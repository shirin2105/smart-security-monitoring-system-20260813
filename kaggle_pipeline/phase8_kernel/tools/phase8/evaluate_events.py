from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.evaluation.phase8_config import load_json, validate_manifest
from app.evaluation.phase8_evaluator import evaluate_events, load_attributions
from app.evaluation.phase8_schema import ground_truth_from_mapping, prediction_from_mapping


def load_jsonl(path: Path, loader) -> list:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(loader(json.loads(line)))
            except Exception as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error
    return rows


def _write_attributions(path: Path, rows: list[dict]) -> None:
    fields = ["clip_id", "event_type", "status", "gt_event_id", "pred_event_id",
              "error_category", "root_cause_notes", "component_to_change", "retest_required"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        writer.writerows({key: row.get(key, "") for key in fields} for row in rows)


def _write_report(path: Path, result: dict) -> None:
    lines = ["# Phase 8 CV E2E validation", "", "## Metrics", "",
             "| Event | Scope | TP | FP | FN | Precision | Recall | F1 | False/hour | Mean delay (s) |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for event_type, row in result["by_event_type"].items():
        delay = "—" if row["mean_detection_delay_s"] is None else f"{row['mean_detection_delay_s']:.3f}"
        false_rate = (row["false_candidates_per_hour"] if row["evaluation_scope"] == "CANDIDATE_ONLY"
                      else row["false_alarms_per_hour"])
        lines.append(f"| {event_type} | {row['evaluation_scope']} | {row['tp']} | {row['fp']} | {row['fn']} | "
                     f"{row['precision']:.4f} | {row['recall']:.4f} | {row['f1']:.4f} | "
                     f"{false_rate:.3f} | {delay} |")
    overall = result["overall"]
    lines += ["", "## Overall", "",
              f"- Precision: {overall['precision']:.4f}", f"- Recall: {overall['recall']:.4f}",
              f"- F1: {overall['f1']:.4f}",
              f"- False alarms/hour: {overall['false_alarms_per_hour']:.3f}",
              f"- False event predictions/hour: {overall['false_event_predictions_per_hour']:.3f}",
              "- Abandoned-object metrics are candidate-only; no confirmed alarm is claimed.",
              f"- FP/FN without reviewed attribution: {result['unattributed_error_count']}",
              "", "## Error attribution", ""]
    if result["error_attribution_counts"]:
        for category, count in result["error_attribution_counts"].items():
            lines.append(f"- {category}: {count}")
    else:
        lines.append("- No FP/FN errors.")
    lines += ["", "## Decision boundary", "",
              "No retraining, S4, or EdgeCrafter decision is made until UNKNOWN causes are reviewed.",
              "", "## Unresolved questions", "",
              "- Review every UNKNOWN row against video and tracking evidence."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict:
    clips = validate_manifest(load_json(args.manifest), not args.allow_small_manifest)
    status = None
    if not args.allow_small_manifest:
        if args.batch_status is None:
            raise ValueError("--batch-status is required for production Phase 8 evaluation")
        status = json.loads(args.batch_status.read_text(encoding="utf-8"))
        expected_ids = {str(clip["clip_id"]) for clip in clips}
        successful_ids = {str(row["clip_id"]) for row in status if row.get("ok")}
        if len(status) != len(clips) or successful_ids != expected_ids:
            raise ValueError("batch status does not prove successful coverage of every manifest clip")
    gt = load_jsonl(args.gt, ground_truth_from_mapping)
    predictions = load_jsonl(args.pred, prediction_from_mapping)
    valid_pairs = {(str(clip["clip_id"]), str(clip["camera_id"])) for clip in clips}
    for event in [*gt, *predictions]:
        if (event.clip_id, event.camera_id) not in valid_pairs:
            raise ValueError(f"event identity is outside manifest: {event.clip_id}/{event.camera_id}")
    duration_s = (sum(float(row["processed_duration_s"]) for row in status)
                  if status is not None else
                  sum(float(clip["expected_duration_s"]) for clip in clips))
    video_hours = duration_s / 3600.0
    result = evaluate_events(gt, predictions, video_hours,
                             attributions=load_attributions(args.attributions))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "phase8_metrics.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_attributions(args.out_dir / "error_attribution.csv", result["errors"])
    _write_report(args.out_dir / "phase8_report.md", result)
    print(json.dumps(result["overall"], indent=2))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate unified Phase 8 event JSONL")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--gt", type=Path, required=True)
    parser.add_argument("--pred", type=Path, required=True)
    parser.add_argument("--attributions", type=Path)
    parser.add_argument("--batch-status", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--allow-small-manifest", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
