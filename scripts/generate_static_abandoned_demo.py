"""Generate an engine-routed abandoned-object demo from untouched PETS footage."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.common.schemas import FrameData  # noqa: E402
from app.common.time_utils import video_timestamp_iso  # noqa: E402
from app.cv.static_region_detector import StaticRegionDetector  # noqa: E402
from app.events.abandoned_object import AbandonedObjectEngine  # noqa: E402
from app.vlm.region_validator import create_region_validator  # noqa: E402

START_ISO = "2026-08-01T00:00:00Z"
DEFAULT_CONFIG = {"warmup_seconds": 3.0, "stationary_seconds": 6.0, "clear_grace_seconds": 2.0,
                  "min_area_ratio": 0.0001, "max_area_ratio": 0.06, "foreground_threshold": 35,
                  "morphology_kernel": 3, "match_iou": 0.15, "learning_rate": 0.04}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_decision_diagnostics(decisions: list[dict]) -> list[dict]:
    safe = []
    for decision in decisions[:10]:
        validation = decision.get("validation") or {}
        verdict = str(validation.get("verdict", "unknown"))[:32]
        reason = str(validation.get("reason", "missing_reason"))[:240]
        reason = re.sub(r"(?i)bearer\s+\S+", "Bearer [REDACTED]", reason)
        reason = re.sub(r"(?i)hf_[a-z0-9_-]{8,}", "[REDACTED]", reason)
        safe.append({"verdict": verdict, "reason": reason})
    return safe


def generate(input_path: Path, output_path: Path, summary_path: Path, mode: str,
             owner_absent_seconds: float = 10.0, model: str = "google/gemma-3-4b-it",
             timeout_seconds: float = 8.0, source_start: str = START_ISO,
             max_vlm_decisions: int = 1) -> dict:
    source = input_path.resolve()
    if not source.is_file():
        raise RuntimeError(f"input clip does not exist: {source}")
    source_hash = _sha256(source)
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise RuntimeError(f"cannot open input clip: {source}")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    expected_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width, height = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if fps <= 0 or expected_frames <= 0 or width <= 0 or height <= 0 or not writer.isOpened():
        capture.release()
        raise RuntimeError("input/output stream metadata is invalid")

    detector = StaticRegionDetector("static-demo", DEFAULT_CONFIG)
    validator = create_region_validator(mode, model=model, timeout_seconds=timeout_seconds)
    rules = {"abandoned_object": {"candidate_source": "static_regions",
                                   "owner_absent_seconds": owner_absent_seconds, "cooldown_seconds": 60,
                                   "temporal": {"enabled": mode == "huggingface", "pre_seconds": 8,
                                                "post_seconds": 8, "sample_fps": 1, "max_frames": 17}}}
    engine = AbandonedObjectEngine("static-demo", [], rules, region_validator=validator)
    events, decisions, frame_count, active_regions = [], [], 0, []
    recorded_decisions, region_cache = set(), {}
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            timestamp = video_timestamp_iso(source_start, frame_count, fps)
            active_regions = detector.update(frame, timestamp)
            region_cache.update({region.region_id: region for region in active_regions})
            engine.submit_static_regions(active_regions)
            frame_data = FrameData(camera_id="static-demo", frame_id=frame_count + 1, captured_at=timestamp,
                                   source_type="VIDEO", source_fps=fps, inference_fps=fps, image=frame)
            for candidate in engine.evaluate([], frame_data):
                timestamp_token = candidate.detectedAt.replace(":", "").replace("-", "").replace(".", "")
                region = next((r for r in active_regions
                               if f"-{r.region_id.replace(':', '-')}-{timestamp_token}" in candidate.candidateId), None)
                region_id = region.region_id if region else next(
                    (key for key in engine.temporal_validation_metadata if f"-{key.replace(':', '-')}-" in candidate.candidateId), None)
                validation = engine.region_validation_results.get(region_id) if region_id else None
                temporal = engine.temporal_validation_metadata.get(region_id, {}) if region_id else {}
                events.append({"candidate": candidate.model_dump(mode="json"),
                               "region_id": region_id,
                               "frame": frame_count, "time_seconds": round(frame_count / fps, 6),
                               "bbox": region.bbox if region else None,
                               "validation": validation.model_dump() if validation else None,
                               **temporal})
            for region_id, metadata in engine.temporal_validation_metadata.items():
                if region_id in recorded_decisions:
                    continue
                validation = engine.region_validation_results.get(region_id)
                if validation is None:
                    continue
                recorded_decisions.add(region_id)
                cached_region = region_cache.get(region_id)
                decisions.append({"region_id": region_id,
                    "bbox": cached_region.bbox if cached_region else None,
                    "candidate_time": metadata["candidate_time"],
                    "decision_time": metadata["decision_time"],
                    "sampled_timestamps": metadata["sampled_timestamps"],
                    "sampled_frame_count": metadata["sampled_frame_count"],
                    "validation": validation.model_dump()})
            for region in active_regions:
                x1, y1, x2, y2 = [int(value) for value in region.bbox]
                result = engine.region_validation_results.get(region.region_id)
                label = f"STATIC {region.persistence_seconds:.1f}s"
                if result:
                    label += f" | {result.verdict.upper()}"
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 215, 255), 2)
                cv2.putText(frame, label, (x1, max(18, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, .45, (0, 215, 255), 1)
            for decision in decisions:
                if decision["decision_time"] != timestamp or not decision["bbox"]:
                    continue
                x1, y1, x2, y2 = [int(value) for value in decision["bbox"]]
                verdict = decision["validation"]["verdict"].upper()
                suffix = "/SUPPRESSED" if verdict == "REJECTED" else ""
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                cv2.putText(frame, f"VLM {verdict}{suffix}", (x1, min(height - 8, y2 + 20)),
                            cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 0, 255), 2)
            cv2.rectangle(frame, (0, 0), (width, 58), (24, 24, 24), -1)
            cv2.putText(frame, f"REAL SOURCE | {frame_count / fps:07.2f}s | regions: {len(active_regions)}",
                        (12, 23), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 1)
            cv2.putText(frame, "ALERT FROM EVENT ENGINE" if events else "MONITORING", (12, 48),
                        cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 80, 255) if events else (0, 220, 255), 2)
            writer.write(frame)
            frame_count += 1
            if mode == "huggingface" and max_vlm_decisions > 0 and len(decisions) >= max_vlm_decisions:
                break
    finally:
        capture.release()
        writer.release()

    incomplete_regions = engine.finalize()
    source_intact = _sha256(source) == source_hash
    semantic_executed = any((decision.get("validation") or {}).get("reason", "").startswith("huggingface_vlm:")
                            for decision in decisions)
    valid_outcome = semantic_executed if mode == "huggingface" else bool(events)
    if frame_count <= 0 or not valid_outcome or not source_intact:
        diagnostics = _safe_decision_diagnostics(decisions)
        failure = {"status": "failed", "validation_mode": mode,
                   "event_count": len(events), "validation_decision_count": len(decisions),
                   "semantic_vlm_executed": semantic_executed,
                   "incomplete_temporal_region_count": len(incomplete_regions),
                   "frame_count": frame_count, "source_frame_count": expected_frames,
                   "source_untouched": source_intact, "decision_diagnostics": diagnostics}
        summary_path.write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        detail = (f"; decisions={len(decisions)}, events={len(events)}, "
                  f"diagnostics={json.dumps(diagnostics, separators=(',', ':'))}"
                  if mode == "huggingface" and decisions and not semantic_executed else "")
        raise RuntimeError("demo verification failed: frames/events/source integrity" + detail)
    first = events[0] if events else None
    first_decision = decisions[0] if decisions else None
    summary = {"source": str(source.relative_to(ROOT)).replace("\\", "/"), "source_sha256": source_hash,
               "source_untouched": source_intact, "output": str(output_path.resolve().relative_to(ROOT)).replace("\\", "/"),
               "config": {"static_region": DEFAULT_CONFIG, "owner_absent_seconds": owner_absent_seconds,
                          "validation_mode": mode, "model": model, "timeout_seconds": timeout_seconds,
                          "source_start": source_start, "max_vlm_decisions": max_vlm_decisions},
               "fps": fps, "frame_count": frame_count, "width": width, "height": height,
               "source_frame_count": expected_frames, "processing_truncated": frame_count < expected_frames,
               "alert_frame": first["frame"] if first else None,
               "alert_time_seconds": first["time_seconds"] if first else None,
               "candidate_time": first_decision["candidate_time"] if first_decision else None,
               "decision_time": first_decision["decision_time"] if first_decision else None,
               "sampled_timestamps": first_decision["sampled_timestamps"] if first_decision else [],
               "sampled_frame_count": first_decision["sampled_frame_count"] if first_decision else 0,
               "event_count": len(events), "events": events,
               "validation_decision_count": len(decisions), "validation_decisions": decisions,
               "incomplete_temporal_region_count": len(incomplete_regions),
               "warnings": ([f"{len(incomplete_regions)} late candidate(s) lacked complete post-roll"]
                            if incomplete_regions else []),
               "semantic_vlm_executed": semantic_executed,
               "validation_disclosure": ("Semantic Hugging Face VLM executed." if semantic_executed else
                                         "No semantic VLM executed; heuristic/disabled/unavailable validation only.")}
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "tests/clips/pets2006_3.mp4")
    parser.add_argument("--output", type=Path, default=ROOT / "examples/static-abandoned-pets2006-demo.mp4")
    parser.add_argument("--summary", type=Path, default=ROOT / "artifacts/static-abandoned-pets2006-summary.json")
    parser.add_argument("--validation", "--vlm", dest="mode", choices=("disabled", "heuristic", "huggingface"), default="heuristic")
    parser.add_argument("--owner-absent-seconds", type=float, default=10.0)
    parser.add_argument("--model", default="google/gemma-3-4b-it")
    parser.add_argument("--timeout-seconds", type=float, default=8.0)
    parser.add_argument("--source-start", default=START_ISO)
    parser.add_argument("--max-vlm-decisions", type=int, default=1)
    args = parser.parse_args()
    try:
        result = generate(args.input, args.output, args.summary, args.mode, args.owner_absent_seconds,
                          args.model, args.timeout_seconds, args.source_start, args.max_vlm_decisions)
    except RuntimeError as exc:
        print(f"demo generation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"output": result["output"], "alert_frame": result["alert_frame"],
                      "alert_time_seconds": result["alert_time_seconds"], "events": result["event_count"],
                      "semantic_vlm_executed": result["semantic_vlm_executed"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
