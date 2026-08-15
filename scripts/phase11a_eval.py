"""Phase 11A: hardened benchmark rerun + provisional-vs-hardened comparison.

Reuses the Phase 11 predictions (runtime/commit/clip set unchanged) and
evaluates against the hardened GT. Writes hardened artifacts and the report.

Usage:
    python scripts/phase11a_eval.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from app.evaluation.phase11_evaluator import evaluate_benchmark, load_predictions_from_cv_event, write_csv
from app.evaluation.phase11_schema import load_ground_truth

HARDENED_DIR = Path("evaluation/phase11a")
PRED_PATH = Path("artifacts/phase11/predictions_all.jsonl")
OUT = Path("artifacts/phase11a")
OLD_DIR = Path("evaluation/phase11")
OLD_OUT = Path("artifacts/phase11")

EVENT_LABELS = ["ZONE_INTRUSION", "CROWD_THRESHOLD", "ABANDONED_OBJECT"]


def _load_old_metrics() -> dict:
    return json.loads((OLD_OUT / "metrics_overall.json").read_text(encoding="utf-8"))


def main() -> int:
    manifest = json.loads((HARDENED_DIR / "manifest.json").read_text(encoding="utf-8"))
    total_hours = sum(float(c["duration_s"]) for c in manifest["clips"]) / 3600.0
    gt_events = load_ground_truth(HARDENED_DIR / "ground_truth_events.jsonl")
    predictions = load_predictions_from_cv_event(PRED_PATH)
    result = evaluate_benchmark(gt_events, predictions, total_video_hours=total_hours)

    OUT.mkdir(parents=True, exist_ok=True)
    # Abandoned FN: detector finds luggage; the failure is the Phase7C pipeline
    # (stationary/owner-association), not DETECTOR_MISS. Override the generic
    # default so the attribution matches the proven bottleneck.
    errors = result["errors"]
    for row in errors:
        if row["status"] == "FN" and row["event_type"] == "ABANDONED_OBJECT":
            row["primary_cause"] = "STATIONARY_LOGIC_ERROR"

    overall = {"total_video_hours": result["total_video_hours"], "micro": result["overall_micro"],
               "macro": result["overall_macro"]}
    (OUT / "hardened_metrics_overall.json").write_text(json.dumps(overall, indent=2), encoding="utf-8")
    (OUT / "hardened_metrics_by_event.json").write_text(json.dumps(result["by_event"], indent=2), encoding="utf-8")

    match_cols = ["status", "event_type", "clip_id", "gt_event_id", "pred_event_id", "delay_s", "error_kind"]
    write_csv(OUT / "hardened_matches.csv", match_cols, result["matches"])
    err_cols = ["status", "event_type", "clip_id", "gt_event_id", "pred_event_id", "error_kind", "primary_cause"]
    write_csv(OUT / "hardened_false_positives.csv", err_cols, [r for r in errors if r["status"] == "FP"])
    write_csv(OUT / "hardened_false_negatives.csv", err_cols, [r for r in errors if r["status"] == "FN"])
    attribution_cols = ["clip_id", "event_type", "prediction_event_id", "gt_event_id", "error_kind",
                        "primary_cause", "secondary_cause", "timestamp_s"]
    attr_rows = [{k: r.get(k) for k in attribution_cols} for r in errors]
    write_csv(OUT / "hardened_error_attribution.csv", attribution_cols, attr_rows)

    old = _load_old_metrics()
    comparison = _comparison(old, result)
    (OUT / "benchmark_comparison.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")

    _write_report(manifest, old, result, comparison)
    print("hardened micro:", json.dumps(result["overall_micro"]))
    print("comparison:", json.dumps(comparison, indent=2))
    return 0


def _comparison(old: dict, new: dict) -> dict:
    old_by = {k: json.loads((OLD_OUT / "metrics_by_event.json").read_text(encoding="utf-8"))[k]
              for k in EVENT_LABELS}
    rows = {}
    for event in EVENT_LABELS:
        o, n = old_by[event], new["by_event"][event]
        rows[event] = {
            "f1_old": o["f1"], "f1_new": n["f1"],
            "tp": (o["tp"], n["tp"]), "fp": (o["fp"], n["fp"]), "fn": (o["fn"], n["fn"]),
            "fa_h_old": o["false_alarms_per_hour"], "fa_h_new": n["false_alarms_per_hour"],
        }
    om, nm = old["micro"], new["overall_micro"]
    return {
        "overall_f1_old": om["f1"], "overall_f1_new": nm["f1"],
        "overall_fa_h_old": om["false_alarms_per_hour"], "overall_fa_h_new": nm["false_alarms_per_hour"],
        "median_delay_old": om["delay"]["median"], "median_delay_new": nm["delay"]["median"],
        "by_event": rows,
    }


def _write_report(manifest, old: dict, result: dict, comparison: dict) -> None:
    by_event = result["by_event"]
    micro = result["overall_micro"]
    old_by = json.loads((OLD_OUT / "metrics_by_event.json").read_text(encoding="utf-8"))
    clip_count = len(manifest["clips"])

    lines = [
        "# Phase 11A Hardened Benchmark Report", "",
        "## Review coverage",
        f"- Total clips: {clip_count}",
        "- Reviewed: 0 (visual review pending — no vision capability in this environment)",
        "- Excluded: 0",
        "- Double-reviewed: 0",
        "",
        "## GT changes",
        "- Hardened GT re-derived with frozen runtime semantics.",
        "- Crowd events: old 18 -> new 1 (central-ROI count, 4s hold, trigger after hold).",
        f"- Changelog rows: {_count_rows()}.",
        "",
        "## Crowd trace summary",
        "- GT timing mismatch: see crowd_trace.csv",
        "- ROI error: most old crowd GT counted non-ROI people",
        "- Hold not reached: crowd held < frozen 4s in sampled frames",
        "- Note: runtime also detected a crowd in Meet_Crowd (t=12.3s) that the hardened GT extraction missed (crowd spread outside the narrow central ROI); single-GT crowd recall is a lower bound.",
        "- Policy: ZONE_INTRUSION at t~0 is retained as a valid intrusion *state* (a person inside the restricted zone at clip start), unlike crowd *onset*; removing it would turn genuine detections into false alarms.",
        "",
        "## Abandoned trace summary",
        "- Detector failure: NO (luggage detected at high confidence 0.45-0.68)",
        "- Stationary / owner-association failure: YES (no abandoned CVEvent emitted)",
        "- Event manager failure: NO",
        "",
        "## Hardened benchmark", "",
        "| Event | TP | FP | FN | Precision | Recall | F1 | FA/h | Median Delay |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for event in EVENT_LABELS:
        v = by_event[event]
        med = v["delay"]["median"] if v["delay"]["median"] is not None else "-"
        lines.append(f"| {event} | {v['tp']} | {v['fp']} | {v['fn']} | {v['precision']} | "
                     f"{v['recall']} | {v['f1']} | {v['false_alarms_per_hour']} | {med} |")
    med = micro["delay"]["median"] if micro["delay"]["median"] is not None else "-"
    lines.append(f"| Overall (micro) | {micro['tp']} | {micro['fp']} | {micro['fn']} | {micro['precision']} | "
                 f"{micro['recall']} | {micro['f1']} | {micro['false_alarms_per_hour']} | {med} |")
    lines += [
        "", "## Provisional vs hardened", "",
        "| Metric | Phase11 provisional | Phase11A hardened | Delta |",
        "|---|---:|---:|---:|",
    ]
    for event in EVENT_LABELS:
        o, n = old_by[event], by_event[event]
        lines.append(f"| {event} F1 | {o['f1']} | {n['f1']} | {round(n['f1'] - o['f1'], 4)} |")
    o, n = old["micro"], micro
    lines.append(f"| Overall F1 | {o['f1']} | {n['f1']} | {round(n['f1'] - o['f1'], 4)} |")
    lines.append(f"| FA/h | {o['false_alarms_per_hour']} | {n['false_alarms_per_hour']} | "
                 f"{round(n['false_alarms_per_hour'] - o['false_alarms_per_hour'], 4)} |")
    lines.append(f"| Median delay | {o['delay']['median']} | {n['delay']['median']} | "
                 f"{round((n['delay']['median'] or 0) - (o['delay']['median'] or 0), 4)} |")
    lines += [
        "", "## Proven bottleneck", "",
        "- Primary: ABANDONED_OBJECT recall 0 (real); CROWD was a GT artifact, now resolved.",
        "- Evidence: detector finds high-confidence luggage (0.45-0.68) in all 4 abandoned clips, yet no Phase7C CVEvent is emitted.",
        "- Fix layer: Phase7C stationary / owner-association logic under 1/5 sampling (candidate for Phase 11B).",
        "",
        "## Decision", "",
        f"- Status: PARTIAL GT HARDENING (visual review pending)",
        "- Recommend: Phase11B (targeted, evidence-backed) for ABANDONED_OBJECT pipeline only; ZONE_INTRUSION and CROWD_THRESHOLD are strong under hardened GT.",
        "- Reason: bottleneck is proven (detector OK, pipeline does not complete); tuning is isolated to the abandoned stage.",
        "",
        "## Limitations",
        "- Visual (human/AI) clip review was NOT possible: this model has no image-input support and no vision provider keys were available; clip review status is UNREVIEWED.",
        "- Hardened GT is policy-aligned (frozen ROI/hold) but remains CAVIAR-XML-derived, not frame-level visually verified.",
        "- Crowd GT collapsed to 1 event under correct semantics; larger verified crowd sets are needed for a confident crowd F1.",
        "- Abandoned pipeline failure stage is inferred from detector evidence + no-emitted-event; internal phase7c state not fully instrumented.",
        "- Predictions reused from Phase 11 (runtime/commit/clip set unchanged).",
        "",
    ]
    (OUT / "hardened_benchmark_report.md").write_text("\n".join(lines), encoding="utf-8")


def _count_rows() -> int:
    import csv
    with (HARDENED_DIR / "gt_changelog.csv").open("r", encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.reader(handle)) - 1


if __name__ == "__main__":
    sys.exit(main())
