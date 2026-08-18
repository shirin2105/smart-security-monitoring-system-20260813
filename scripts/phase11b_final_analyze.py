"""Validate and analyze the fail-closed Phase 11B-FINAL benchmark."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.cv.contracts.validation import validate_event

EVAL = Path("evaluation/phase11b_final")
OUT = Path("artifacts/phase11b_final")
RUN_MANIFEST = OUT / "production-roi-run-v3.json"
RESULTS = OUT / "benchmark_results_v4.json"
REPORT = OUT / "phase11b_final_report_v4.md"
CLIPS = {"LeftBag", "LeftBag_AtChair", "LeftBag_PickedUp", "LeftBox"}
CENTRAL_ROI = [[115, 115], [269, 115], [269, 259], [115, 259]]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_new(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(content)


def require_absent(paths: list[Path]) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise FileExistsError(f"refusing to overwrite Phase 11B-FINAL analysis: {existing}")


def validate_policy_inputs(manifest: dict) -> None:
    if manifest.get("status") != "ROI_POLICY_UNRESOLVED" or manifest.get("positive_clips") != []:
        raise ValueError("unresolved refreeze must contain zero trusted positives")
    if set(manifest.get("excluded_pending_human", [])) != CLIPS:
        raise ValueError("refreeze must exclude exactly the four pending clips")
    with (EVAL / "adjudication.csv").open(newline="", encoding="utf-8") as handle:
        decisions = list(csv.DictReader(handle))
    if {row["clip_id"] for row in decisions} != CLIPS:
        raise ValueError("adjudication coverage mismatch")
    if any(row["adjudication_status"] != "AMBIGUOUS_NEEDS_HUMAN" or row["is_in_policy"].lower() != "false"
           or row["roi_change_required"].lower() != "false" for row in decisions):
        raise ValueError("unresolved adjudication contains a trusted positive")
    if (EVAL / "refrozen_ground_truth_events.jsonl").read_text(encoding="utf-8").strip():
        raise ValueError("unresolved refreeze ground truth must be empty")


def validate_run(expected: set[str], policy: dict, run: dict) -> tuple[Path, set[str]]:
    if run.get("schema") != "phase11-inference-run-v1":
        raise ValueError("unsupported inference run manifest")
    if (policy.get("status") != "UNCHANGED_PENDING_HUMAN" or policy.get("event_type") != "ABANDONED_OBJECT"
            or policy.get("coordinate_mode") != "pixel" or policy.get("default_polygon") != CENTRAL_ROI
            or policy.get("camera_overrides") != {} or policy.get("diagnostic_no_roi_is_production_default") is not False
            or policy.get("source") != "docs/phase11/BENCHMARK_FREEZE.md"):
        raise ValueError("ROI policy is not the frozen benchmark default")
    if run.get("phase7c_valid_floor_roi_polygon") != policy["default_polygon"]:
        raise ValueError("inference run ROI does not match frozen policy")
    clips = run.get("clips", [])
    completed = {item.get("clip_id") for item in clips if item.get("completed") is True and item.get("processed_frames", 0) > 0}
    if completed != expected or len(clips) != len(expected):
        raise ValueError(f"run completion mismatch expected={sorted(expected)} completed={sorted(completed)}")
    for item in clips:
        source = Path("phase8_dataset/videos") / f"{item['clip_id']}.mpg"
        if not source.is_file() or sha256(source) != item.get("source_sha256"):
            raise ValueError(f"source artifact hash mismatch: {item['clip_id']}")
    predictions = Path(run["predictions_path"])
    if not predictions.is_file() or sha256(predictions) != run.get("predictions_sha256"):
        raise ValueError("prediction artifact hash mismatch")
    if sha256(Path("configs/event_rules.yaml")) != run.get("event_rules_sha256"):
        raise ValueError("event rules changed after inference")
    if sha256(Path("phase8_dataset/manifest.json")) != run.get("dataset_manifest_sha256"):
        raise ValueError("dataset manifest changed after inference")
    if sha256(Path("scripts/phase11_infer.py")) != run.get("inference_script_sha256"):
        raise ValueError("inference script changed after inference")
    rows = read_jsonl(predictions)
    for row in rows:
        validate_event(row)
    row_counts = Counter(row["camera_id"] for row in rows)
    if any(row_counts[item["clip_id"]] != item.get("lifecycle_records") for item in clips):
        raise ValueError("per-clip lifecycle count mismatch")
    return predictions, completed


def negative_metrics(expected: set[str], completed: set[str], rows: list[dict], duration_s: float) -> dict:
    if completed != expected:
        raise ValueError(f"negative coverage mismatch missing={sorted(expected - completed)}")
    for row in rows:
        validate_event(row)
    unexpected = {row["camera_id"] for row in rows} - expected
    if unexpected:
        raise ValueError(f"unexpected prediction cameras={sorted(unexpected)}")
    starts = [row for row in rows if row["event_type"] == "ABANDONED_OBJECT" and row["event_state"] == "START"]
    return {"expected_clips": len(expected), "completed_clips": len(completed), "abandoned_starts": len(starts),
            "false_alarms_per_hour": len(starts) / (duration_s / 3600.0) if duration_s else None, "pass": not starts}


def terminal_exit_code(status: str, negative_pass: bool) -> int:
    if not negative_pass:
        return 1
    return 0 if status == "READY_FOR_PHASE12" else 2


def main() -> int:
    require_absent([RESULTS, REPORT])
    manifest = json.loads((EVAL / "refrozen_manifest.json").read_text(encoding="utf-8"))
    validate_policy_inputs(manifest)
    policy = json.loads((EVAL / "roi_policy.json").read_text(encoding="utf-8"))
    run = json.loads(RUN_MANIFEST.read_text(encoding="utf-8"))
    expected = set(manifest["generic_negative_clips"])
    dataset = json.loads(Path("phase8_dataset/manifest.json").read_text(encoding="utf-8"))
    source_negatives = {clip["clip_id"] for clip in dataset["clips"] if "abandoned_negative" in clip["scenario_tags"]}
    if expected != source_negatives:
        raise ValueError("refrozen negative set differs from source dataset")
    durations = {clip["clip_id"]: float(clip["expected_duration_s"]) for clip in dataset["clips"]}
    predictions, completed = validate_run(expected, policy, run)
    duration_s = sum(durations[clip_id] for clip_id in expected)
    negatives = negative_metrics(expected, completed, read_jsonl(predictions), duration_s)
    results = {"status": "ROI_POLICY_UNRESOLVED", "benchmark_version": manifest["version"], "benchmark_roi": "CENTRAL_ROI",
               "in_policy_positive_count": 0, "tp": 0, "fp": negatives["abandoned_starts"], "fn": 0,
               "precision": None, "recall": None, "f1": None, "median_delay_s": None, "duplicate_rate": None,
               "first_failing_stage_distribution": {}, "negative_safety": negatives, "run_manifest": str(RUN_MANIFEST),
               "metrics_note": "Positive metrics and stage distribution require human-adjudicated positives."}
    write_new(RESULTS, json.dumps(results, indent=2))
    report = f"""# Phase 11B-FINAL Report

## Decision and policy

All four candidate positives, including `LeftBag_PickedUp`, remain `AMBIGUOUS_NEEDS_HUMAN`. They are excluded from tuning. The frozen Phase 11 benchmark `CENTRAL_ROI` is unchanged; no camera overrides or diagnostic no-ROI default were authorized.

## Refrozen benchmark

- Trusted positives: 0; positive metrics and first-failing-stage distribution: not computable.
- Generic negatives completed: {negatives['completed_clips']}/{negatives['expected_clips']} under the frozen benchmark ROI.
- Abandoned START count: {negatives['abandoned_starts']} ({'PASS' if negatives['pass'] else 'FAIL'}); false alarms/hour: {negatives['false_alarms_per_hour']:.3f} across {duration_s:.2f}s.
- Provenance: `{RUN_MANIFEST}` validates clip completion, ROI, prediction hash, event-rule hash, and inference-script hash.
- Semantic negative categories remain unlabeled and not covered.

## Scope lock

No owner, threshold, detector, tracker, stationary, ROI, or Phase 12 change is authorized. Authoritative human/product adjudication remains required.

## FINAL STATUS

ROI_POLICY_UNRESOLVED
"""
    write_new(REPORT, report)
    print(json.dumps(results, indent=2))
    return terminal_exit_code(results["status"], negatives["pass"])


if __name__ == "__main__":
    raise SystemExit(main())
