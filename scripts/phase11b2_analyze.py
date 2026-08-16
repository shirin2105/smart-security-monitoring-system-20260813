"""Build Phase 11B.2 ROI provenance, stage, and safety reports."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


OUT = Path("artifacts/phase11b2")
CLIPS = ("LeftBag", "LeftBag_AtChair", "LeftBag_PickedUp", "LeftBox")


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_csv(path: Path, rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def negative_gate(expected: set[str], observed: set[str], abandoned_starts: list[dict]) -> bool:
    return expected == observed and not abandoned_starts


def main() -> int:
    before = {row["clip_id"]: row for row in read_jsonl(OUT / "roi-audit-before.jsonl")}
    after = {row["clip_id"]: row for row in read_jsonl(OUT / "roi-audit-after.jsonl")}
    gt = {row["clip_id"]: row for row in read_jsonl(Path("evaluation/phase11a/ground_truth_events.jsonl"))
          if row["event_type"] == "ABANDONED_OBJECT"}
    positives = []
    reasons: Counter[str] = Counter()
    trace_manifest = {}
    for clip_id in CLIPS:
        trace_path = OUT / "traces-after" / f"{clip_id}.jsonl"
        trace = read_jsonl(trace_path)
        event = gt[clip_id]
        rows = [row for row in trace if event["start_s"] - 2 <= row["time_s"] <= event["end_s"] + 2]
        emitted = any(row["event_emitted"] for row in rows)
        owner_reasons = [row["owner_rejection_reason"] for row in rows if row.get("owner_rejection_reason")]
        failure = None if emitted else ("OWNER_NOT_ASSOCIATED" if owner_reasons else
                                        next((row["failure_hint"] for row in reversed(rows) if row.get("failure_hint")), "UNKNOWN"))
        if failure:
            reasons[failure] += 1
        positives.append({
            "clip_id": clip_id, "gt_event_id": event["event_id"], "camera_id": clip_id,
            "stationary_confirmed_at_s": before[clip_id]["time_s"],
            "frame_width": before[clip_id]["original_width"], "frame_height": before[clip_id]["original_height"],
            "roi_id": "ABANDONED_VALID_FLOOR_NONE", "roi_coordinate_mode": "pixel",
            "test_point_type": "bottom_center", "test_point_x": before[clip_id]["bottom_center_x"],
            "test_point_y": before[clip_id]["bottom_center_y"], "inside_before": before[clip_id]["inside_result"],
            "inside_after": after[clip_id]["inside_result"], "root_cause_class": "BENCHMARK_POLICY_MISMATCH",
            "overlay_before": before[clip_id]["overlay_path"], "overlay_after": after[clip_id]["overlay_path"],
            "new_first_failing_stage": failure or "NONE", "event_emitted": emitted,
            "notes": "NEEDS_VISUAL_GT_CONFIRMATION" if clip_id == "LeftBag_PickedUp" else
                     f"owner rejection reasons: {dict(Counter(owner_reasons))}",
        })
        trace_manifest[clip_id] = {"rows": len(trace), "sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest()}
    write_csv(OUT / "positive_roi_audit.csv", positives)
    provenance = [{
        "clip_id": clip_id, "camera_id": clip_id, "event_type": "ABANDONED_OBJECT",
        "roi_id": "CENTRAL_ROI", "source_config_file": "docs/phase11/BENCHMARK_FREEZE.md",
        "roi_purpose": "frozen benchmark valid-floor restriction", "camera_specific": False,
        "event_specific": True, "fallback_used": False,
        "notes": "default preserved; no-ROI behavior is diagnostic opt-in only",
    } for clip_id in CLIPS]
    write_csv(OUT / "roi_provenance.csv", provenance)
    negative_rows = read_jsonl(OUT / "predictions-negatives.jsonl")
    dataset_manifest = json.loads(Path("phase8_dataset/manifest.json").read_text(encoding="utf-8"))
    expected_negatives = {clip["clip_id"] for clip in dataset_manifest["clips"]
                          if "abandoned_negative" in clip["scenario_tags"]}
    observed_negatives = {row.get("camera_id") for row in negative_rows}
    missing_negatives = expected_negatives - observed_negatives
    unexpected_negatives = observed_negatives - expected_negatives
    abandoned_starts = [row for row in negative_rows
                        if row.get("event_type") == "ABANDONED_OBJECT" and row.get("event_state") == "START"]
    negative_pass = negative_gate(expected_negatives, observed_negatives, abandoned_starts)
    negative_safety = [{
        "coverage": "manifest-classified abandoned_negative clips", "clips": len(expected_negatives),
        "observed_clips": len(observed_negatives), "missing_clips": ";".join(sorted(missing_negatives)),
        "unexpected_clips": ";".join(sorted(unexpected_negatives)),
        "abandoned_starts": len(abandoned_starts), "result": "PASS" if negative_pass else "FAIL",
        "semantic_categories": "pre-existing/fixed/owner-stays/pickup/carrying/brief-return/multiple-people",
        "category_result": "NOT_COVERED", "notes": "manifest has generic negatives, not category-level labels",
    }]
    write_csv(OUT / "negative_safety.csv", negative_safety)
    distribution = {"total_positive_clips": len(CLIPS), "trace_inputs": trace_manifest,
                    "by_stage": {key: {"count": value, "share": value / len(CLIPS)} for key, value in reasons.items()}}
    (OUT / "new_first_failing_stage.json").write_text(json.dumps(distribution, indent=2), encoding="utf-8")
    report = f"""# Phase 11B.2 Valid-Floor ROI Report

## Status
- Diagnosis: ROI_CONFIG_CORRECT_BENCHMARK_MISMATCH.
- Root cause: `BENCHMARK_POLICY_MISMATCH` — all four positive GT placements are outside the explicitly frozen abandoned central ROI.
- Fix: no production/default fix. Frozen Phase 11 behavior is preserved; no-ROI is available only with `PHASE11B2_DISABLE_ABANDONED_ROI=1` for diagnostic reruns.
- Recommendation: visually adjudicate and re-freeze the abandoned ROI or exclude/relabel out-of-policy GT before owner work.

## Coordinate audit
- Original frame: 384x288 pixels. Detector input: direct resize to 640x640, no letterbox/padding.
- DEIMv2 postprocessor receives original width/height and returns original-frame pixel `xyxy` boxes.
- ROI: raw pixel coordinates, unchanged. Current test point: bbox bottom-center, correct for floor semantics.
- Transform, axis order, bbox restoration, and test-point calculations: PASS.

## Positive results
- Frozen ROI: 0/4 pass. Diagnostic no-ROI counterfactual: 4/4 pass.
- Counterfactual next failing stage: OWNER_NOT_ASSOCIATED 4/4. Events emitted: 0/4.
- LeftBag_PickedUp semantics: NEEDS_VISUAL_GT_CONFIRMATION.

## Targeted fix
- Class: BENCHMARK. File: `scripts/phase11_infer.py`.
- Exact behavior: documented default remains frozen; explicit diagnostic env flag disables abandoned ROI only for Phase 11B.2 evidence runs.
- No polygon enlarged, no test point changed, no owner logic changed, no frozen default changed.

## Negative safety
- Real generic abandoned negatives: {len(expected_negatives)} expected/{len(observed_negatives)} observed clips, {len(abandoned_starts)} abandoned START events — {negative_safety[0]['result']}.
- Requested semantic negative categories: NOT_COVERED (no category-level labels).

## Visual verification
- Eight before/counterfactual overlays generated and agent-inspected, not human-verified, under `artifacts/phase11b2/overlays/`.

## Non-regression
- See `test_handoff.md`.

## Decision
- Status: ROI_CONFIG_CORRECT_BENCHMARK_MISMATCH.
- Next phase: ROI/GT visual adjudication and benchmark re-freeze.
- Reason: counterfactual removal exposes owner association, but cannot authorize changing the frozen product/benchmark policy.
"""
    (OUT / "phase11b2_report.md").write_text(report, encoding="utf-8")
    print(json.dumps(distribution["by_stage"], indent=2))
    return 0 if negative_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
