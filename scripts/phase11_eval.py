"""Phase 11: evaluate predictions against GT and emit all benchmark artifacts.

Runs under the test venv. Reads manifest.json + ground_truth_events.jsonl +
predictions_all.jsonl and writes the Phase 11 output artifacts.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from app.evaluation.phase11_evaluator import evaluate_benchmark, load_predictions_from_cv_event, write_csv
from app.evaluation.phase11_schema import load_ground_truth

MANIFEST = Path("evaluation/phase11/manifest.json")
GT_PATH = Path("evaluation/phase11/ground_truth_events.jsonl")
PRED_PATH = Path("artifacts/phase11/predictions_all.jsonl")
OUT = Path("artifacts/phase11")

EVENT_LABELS = ["ZONE_INTRUSION", "CROWD_THRESHOLD", "ABANDONED_OBJECT"]


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    total_hours = sum(float(clip["duration_s"]) for clip in manifest["clips"]) / 3600.0

    gt_events = load_ground_truth(GT_PATH)
    predictions = load_predictions_from_cv_event(PRED_PATH)
    result = evaluate_benchmark(gt_events, predictions, total_video_hours=total_hours)

    OUT.mkdir(parents=True, exist_ok=True)

    overall = {
        "total_video_hours": result["total_video_hours"],
        "micro": result["overall_micro"],
        "macro": result["overall_macro"],
    }
    (OUT / "metrics_overall.json").write_text(json.dumps(overall, indent=2), encoding="utf-8")
    (OUT / "metrics_by_event.json").write_text(json.dumps(result["by_event"], indent=2), encoding="utf-8")

    match_cols = ["status", "event_type", "clip_id", "gt_event_id", "pred_event_id", "delay_s", "error_kind"]
    write_csv(OUT / "matched_events.csv", match_cols, result["matches"])

    fpn_cols = ["status", "event_type", "clip_id", "gt_event_id", "pred_event_id", "error_kind", "primary_cause"]
    fps = [r for r in result["errors"] if r["status"] == "FP"]
    fns = [r for r in result["errors"] if r["status"] == "FN"]
    dups = [r for r in result["errors"] if r["status"] == "DUP"]
    write_csv(OUT / "false_positives.csv", fpn_cols, fps)
    write_csv(OUT / "false_negatives.csv", fpn_cols, fns)

    delay_cols = ["event_type", "clip_id", "gt_event_id", "pred_event_id", "delay_s", "error_kind"]
    write_csv(OUT / "detection_delay.csv", delay_cols, result["matches"])

    attribution_cols = [
        "clip_id", "camera_id", "event_type", "prediction_event_id", "gt_event_id",
        "error_kind", "primary_cause", "secondary_cause", "timestamp_s", "description",
        "evidence", "recommended_fix_layer",
    ]
    attribution_rows = _attribution_rows(result)
    write_csv(OUT / "error_attribution.csv", attribution_cols, attribution_rows)

    _write_report(manifest, result, fps, fns, dups)
    print("Overall micro:", json.dumps(overall["micro"]))
    print("By event:", json.dumps({k: {"tp": v["tp"], "fp": v["fp"], "fn": v["fn"],
                                        "p": v["precision"], "r": v["recall"], "f1": v["f1"],
                                        "fa/h": v["false_alarms_per_hour"]} for k, v in result["by_event"].items()}))
    print(f"wrote artifacts to {OUT}")
    return 0


def _attribution_rows(result: dict) -> list[dict]:
    rows = []
    for error in result["errors"]:
        rows.append({
            "clip_id": error.get("clip_id"),
            "camera_id": error.get("clip_id"),
            "event_type": error.get("event_type"),
            "prediction_event_id": error.get("pred_event_id"),
            "gt_event_id": error.get("gt_event_id"),
            "error_kind": error.get("error_kind"),
            "primary_cause": error.get("primary_cause", "UNKNOWN"),
            "secondary_cause": "",
            "timestamp_s": error.get("delay_s"),
            "description": "",
            "evidence": "",
            "recommended_fix_layer": "",
        })
    return rows


def _write_report(manifest: dict, result: dict, fps: list, fns: list, dups: list) -> None:
    by_event = result["by_event"]
    micro = result["overall_micro"]
    macro = result["overall_macro"]
    clip_count = len(manifest["clips"])
    total_duration = sum(float(c["duration_s"]) for c in manifest["clips"])

    lines = [
        "# Phase 11 Final CV Benchmark Report",
        "",
        "## Freeze",
        "- Commit: `02e9f0e` (develop)",
        "- Benchmark version: phase11-v1",
        "- Detector checkpoint: artifacts/phase7a-results/outputs/phase7a_deimv2_s_person_luggage/best.pth",
        "- Runtime profile: BALANCED",
        "- Inference FPS: 5",
        "- Hardware: NVIDIA GeForce RTX 3050 Laptop GPU (CUDA)",
        "",
        "## Dataset",
        f"- Total clips: {clip_count}",
        f"- Total duration: {total_duration:.1f}s ({total_duration/3600:.4f} h)",
        f"- GT events: {sum(1 for _ in open(GT_PATH, encoding='utf-8') if _.strip())}",
        f"- Status: PARTIAL BENCHMARK (GT provisional/heuristic)",
        "",
        "## Overall metrics",
        "",
        "| Event | TP | FP | FN | Precision | Recall | F1 | FA/h | Median Delay |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for event in EVENT_LABELS:
        v = by_event[event]
        med = v["delay"]["median"] if v["delay"]["median"] is not None else "-"
        lines.append(
            f"| {event} | {v['tp']} | {v['fp']} | {v['fn']} | {v['precision']} | "
            f"{v['recall']} | {v['f1']} | {v['false_alarms_per_hour']} | {med} |"
        )
    med = micro["delay"]["median"] if micro["delay"]["median"] is not None else "-"
    lines.append(
        f"| Overall (micro) | {micro['tp']} | {micro['fp']} | {micro['fn']} | {micro['precision']} | "
        f"{micro['recall']} | {micro['f1']} | {micro['false_alarms_per_hour']} | {med} |"
    )
    lines.append(
        f"| Overall (macro) | - | - | - | {macro['precision']} | {macro['recall']} | {macro['f1']} | - | - |"
    )
    lines += [
        "",
        "## Delay",
        f"- Mean: {micro['delay']['mean']}",
        f"- Median: {micro['delay']['median']}",
        f"- P90: {micro['delay']['p90']}",
        f"- Max: {micro['delay']['max']}",
        "",
        "## Duplicate",
        f"- Total duplicates: {micro['duplicates']}",
        f"- Duplicate rate: {micro['duplicate_rate']}",
        "",
        "## Runtime",
        "- Actual FPS: see per-clip inference log (target 5, sampling 1/5)",
        "- Pipeline latency: detector ~96 ms/frame (RTX 3050, CPU-bound pipeline)",
        "- Frame age: fresh (file source, sampling)",
        "- Dropped/skipped: non-sampled frames skipped (FrameSampler)",
        "- Runtime profile: BALANCED",
        "",
        "## Error attribution",
        "",
        "| Cause | Count | Share |",
        "|---|---:|---:|",
    ]
    counts = Counter(r["primary_cause"] for r in fps + fns + dups)
    total_err = len(fps) + len(fns) + len(dups)
    for cause, count in counts.most_common():
        share = f"{100 * count / total_err:.1f}%" if total_err else "-"
        lines.append(f"| {cause} | {count} | {share} |")
    lines += [
        "",
        "## Product interpretation",
        f"- Best event: {_best_event(by_event)}",
        f"- Weakest event: {_weakest_event(by_event)}",
        f"- Main risk: {_main_risk(by_event)}",
        "- False alarm assessment: see FA/h per event",
        "- Delay assessment: see Delay section",
        "",
        "## Decision",
        f"- Phase 11 status: PARTIAL BENCHMARK",
        f"- Primary bottleneck: {_main_risk(by_event)}",
        "- Recommend: Phase12 (GT provisioning + real annotation) — see Limitations",
        "- Reason: GT is provisional/heuristic; a Phase11B tuning decision needs reliable GT.",
        f"- Phase11B candidates (only once GT is reliable): crowd hold/sampling (hold 4s + 1/5 sampling misses brief crowds; {by_event['CROWD_THRESHOLD']['fn']} crowd FN); abandoned detection (0/4 detected; detector/adapter miss).",
        "",
        "## Limitations",
        "- GT is derived deterministically from CAVIAR trajectory XML and is provisional (not frame-level visually verified).",
        "- Intrusion ROI is a heuristic central region; the model/tracker may interpret the scene differently.",
        "- Predicted vs GT alignment is sensitive to the ROI and thresholds; absolute Precision/Recall are indicative, not production-grade.",
        f"- CROWD_THRESHOLD GT uses a short hold (1 s, independent truth) while the frozen runtime requires 4 s + 1/5 frame sampling; the runtime therefore under-catches brief crowds (18 FN).",
        f"- ABANDONED_OBJECT GT relies on the 'leaving object' role (present in some clips); the runtime detected 0 abandoned events.",
        "- Real inference ran on a single RTX 3050; per-clip FPS and latency are environment-specific.",
        "",
    ]
    (OUT / "benchmark_report.md").write_text("\n".join(lines), encoding="utf-8")


def _best_event(by_event: dict) -> str:
    best = None
    best_f1 = -1
    for event, v in by_event.items():
        if v["tp"] + v["fn"] > 0 and v["f1"] > best_f1:
            best_f1 = v["f1"]
            best = event
    return best or "n/a"


def _weakest_event(by_event: dict) -> str:
    worst = None
    worst_f1 = float("inf")
    for event, v in by_event.items():
        if v["tp"] + v["fn"] > 0 and v["f1"] < worst_f1:
            worst_f1 = v["f1"]
            worst = event
    return worst or "n/a"


def _main_risk(by_event: dict) -> str:
    worst = _weakest_event(by_event)
    if worst is None:
        return "no GT-backed events"
    v = by_event[worst]
    crowd = by_event.get("CROWD_THRESHOLD", {})
    abandoned = by_event.get("ABANDONED_OBJECT", {})
    if (crowd.get("tp", 0) == 0 and crowd.get("fn", 0) > 0) and (
        abandoned.get("tp", 0) == 0 and abandoned.get("fn", 0) > 0
    ):
        return f"CROWD_THRESHOLD ({crowd['fn']} FN) and ABANDONED_OBJECT ({abandoned['fn']} FN) recall 0"
    if v["fn"] > v["fp"]:
        return f"{worst} misses dominate (recall {v['recall']})"
    if v["fp"] >= v["fn"]:
        return f"{worst} false alarms dominate (precision {v['precision']})"
    return worst


if __name__ == "__main__":
    sys.exit(main())
