"""Deterministic Phase 11 event-level benchmark evaluator.

Pipeline: load GT + canonical cv-event-v1 predictions -> collapse lifecycles ->
one-to-one match by (clip, camera, event_type) + temporal window -> compute
TP/FP/FN, Precision/Recall/F1 (micro + macro), false alarms/hour, detection
delay (mean/median/P90/max), duplicate rate and error attribution rows.
"""

from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.evaluation.phase11_schema import (
    DEFAULT_TOLERANCES_S,
    PredictedEvent,
    GroundTruthEvent,
    collapse_lifecycles,
    prediction_from_cv_event,
)

# Re-declare tolerated event delay window conventions.
EARLY = "EARLY_ALERT"
LATE = "LATE_ALERT"


def _safe_div(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def _validate_unique_gt(events: Iterable[GroundTruthEvent]) -> None:
    seen: set[tuple[str, str, str]] = set()
    for event in events:
        key = (event.clip_id, event.camera_id, event.event_id)
        if key in seen:
            raise ValueError(f"duplicate GT event identity={key}")
        seen.add(key)


def load_predictions_from_cv_event(path: str | Path) -> list[PredictedEvent]:
    """Load a raw cv-event-v1 JSONL and collapse lifecycles into instances."""
    raw: list[PredictedEvent] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            raw.append(prediction_from_cv_event(payload))
    collapsed = collapse_lifecycles(raw)
    # A collapsed instance must still carry its identity fields.
    for prediction in collapsed:
        prediction.validate()
    return collapsed


def _tolerance(tolerances: dict[str, float], event_type: str) -> float:
    return float(tolerances.get(event_type, 3.0))


def _default_primary_cause(status: str, event_type: str) -> str:
    """Deterministic default attribution for a FP/FN/DUP error row.

    Refined automatically by the report's error inspection; the taxonomy keeps
    the primary causes stable.
    """
    if status == "DUP":
        return "DUPLICATE_EVENT"
    if status == "FN":
        if event_type == "CROWD_THRESHOLD":
            return "CROWD_COUNT_ERROR"
        if event_type == "ABANDONED_OBJECT":
            return "DETECTOR_MISS"
        return "DETECTOR_MISS"
    # FP
    if event_type == "ZONE_INTRUSION":
        return "ROI_ERROR"
    if event_type == "CROWD_THRESHOLD":
        return "CROWD_COUNT_ERROR"
    return "DETECTOR_FALSE_POSITIVE"


def _compatible(gt: GroundTruthEvent, pred: PredictedEvent, tolerance: float) -> bool:
    """Temporal match window: [trigger_time_s - tolerance, end_s + tolerance].

    ``tolerance`` gates early (before trigger) acceptance; the late bound extends
    through the event's end plus the tolerance so an alert raised while the event
    is still ongoing (or within grace of its end) is accepted as a true positive
    and flagged LATE_ALERT when past the tolerance after trigger.
    """
    if (gt.clip_id, gt.camera_id, gt.event_type) != (pred.clip_id, pred.camera_id, pred.event_type):
        return False
    if gt.zone_id and pred.evidence.get("zone_id") not in (None, gt.zone_id):
        return False
    return gt.trigger_time_s - tolerance <= pred.event_time_s <= gt.end_s + tolerance


def _match_one_to_one(
    gt_events: list[GroundTruthEvent],
    pred_events: list[PredictedEvent],
    tolerances: dict[str, float],
) -> tuple[list[tuple[int, int, float]], set[int], set[int]]:
    candidates: list[tuple[float, int, int]] = []
    for gt_index, gt in enumerate(gt_events):
        tolerance = _tolerance(tolerances, gt.event_type)
        for pred_index, pred in enumerate(pred_events):
            if _compatible(gt, pred, tolerance):
                candidates.append((abs(pred.event_time_s - gt.trigger_time_s), gt_index, pred_index))
    used_gt: set[int] = set()
    used_pred: set[int] = set()
    matches: list[tuple[int, int, float]] = []
    for _, gt_index, pred_index in sorted(candidates, key=lambda item: (item[0], item[1], item[2])):
        if gt_index not in used_gt and pred_index not in used_pred:
            used_gt.add(gt_index)
            used_pred.add(pred_index)
            gt = gt_events[gt_index]
            pred = pred_events[pred_index]
            matches.append((gt_index, pred_index, pred.event_time_s - gt.trigger_time_s))
    missing_gt = set(range(len(gt_events))) - used_gt
    missing_pred = set(range(len(pred_events))) - used_pred
    return matches, missing_gt, missing_pred


def _duplicate_predictions(
    pred_events: list[PredictedEvent],
    missing_pred: set[int],
    gt_events: list[GroundTruthEvent],
    matches: list[tuple[int, int, float]],
    tolerances: dict[str, float],
) -> set[int]:
    """Unmatched predictions falling inside a matched GT's window are duplicates."""
    matched_gt: dict[int, GroundTruthEvent] = {}
    for gt_index, _, _ in matches:
        matched_gt[gt_index] = gt_events[gt_index]
    duplicates: set[int] = set()
    for pred_index in missing_pred:
        pred = pred_events[pred_index]
        for gt in matched_gt.values():
            if (gt.clip_id, gt.camera_id, gt.event_type) != (pred.clip_id, pred.camera_id, pred.event_type):
                continue
            tolerance = _tolerance(tolerances, pred.event_type)
            if gt.trigger_time_s - tolerance <= pred.event_time_s <= gt.end_s + tolerance:
                duplicates.add(pred_index)
                break
    return duplicates


def _percentile(sorted_values: list[float], percentile: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = percentile / 100.0 * (len(sorted_values) - 1)
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    weight = rank - low
    return sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight


def _delay_stats(delays: list[float]) -> dict[str, float | None]:
    if not delays:
        return {"mean": None, "median": None, "p90": None, "max": None, "min": None, "count": 0}
    sorted_delays = sorted(delays)
    return {
        "mean": round(statistics.mean(delays), 3),
        "median": round(statistics.median(delays), 3),
        "p90": round(_percentile(sorted_delays, 90.0), 3),
        "max": round(max(delays), 3),
        "min": round(min(delays), 3),
        "count": len(delays),
    }


def _macro_mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def evaluate_benchmark(
    gt_events: Iterable[GroundTruthEvent],
    pred_events: Iterable[PredictedEvent],
    total_video_hours: float,
    tolerances_s: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Evaluate event-level predictions against ground truth."""
    if total_video_hours <= 0:
        raise ValueError("total_video_hours must be positive")
    gt_all = list(gt_events)
    pred_all = list(pred_events)
    _validate_unique_gt(gt_all)
    tolerances = dict(tolerances_s or DEFAULT_TOLERANCES_S)

    by_event: dict[str, dict[str, Any]] = {}
    all_delays: list[float] = []
    match_rows: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []
    total_tp = total_fp = total_fn = total_dup = 0

    for event_type in sorted(tolerances.keys()):
        gt = [event for event in gt_all if event.event_type == event_type]
        pred = [event for event in pred_all if event.event_type == event_type]
        matches, missing_gt, missing_pred = _match_one_to_one(gt, pred, tolerances)
        duplicates = _duplicate_predictions(pred, missing_pred, gt, matches, tolerances)
        delays = []

        for gt_index, pred_index, delay in matches:
            delays.append(delay)
            all_delays.append(delay)
            gt_event = gt[gt_index]
            pred_event = pred[pred_index]
            row = {
                "status": "TP",
                "event_type": event_type,
                "clip_id": gt_event.clip_id,
                "gt_event_id": gt_event.event_id,
                "pred_event_id": pred_event.event_id,
                "delay_s": round(delay, 3),
                "error_kind": "TP",
            }
            if delay < 0:
                row["error_kind"] = EARLY
            elif delay > _tolerance(tolerances, event_type):
                row["error_kind"] = LATE
            match_rows.append(row)
            if row["error_kind"] in (EARLY, LATE):
                error_rows.append(row)

        for pred_index in missing_pred:
            pred_event = pred[pred_index]
            if pred_index in duplicates:
                total_dup += 1
                error_rows.append({
                    "status": "DUP", "event_type": event_type, "clip_id": pred_event.clip_id,
                    "gt_event_id": None, "pred_event_id": pred_event.event_id,
                    "delay_s": None, "error_kind": "DUPLICATE",
                    "primary_cause": _default_primary_cause("DUP", event_type),
                })
            else:
                total_fp += 1
                error_rows.append({
                    "status": "FP", "event_type": event_type, "clip_id": pred_event.clip_id,
                    "gt_event_id": None, "pred_event_id": pred_event.event_id,
                    "delay_s": None, "error_kind": "FP",
                    "primary_cause": _default_primary_cause("FP", event_type),
                })

        for gt_index in missing_gt:
            gt_event = gt[gt_index]
            total_fn += 1
            error_rows.append({
                "status": "FN", "event_type": event_type, "clip_id": gt_event.clip_id,
                "gt_event_id": gt_event.event_id, "pred_event_id": None,
                "delay_s": None, "error_kind": "FN",
                "primary_cause": _default_primary_cause("FN", event_type),
            })

        tp = len(matches)
        fn = len(missing_gt)
        # recompute per-event fp (exclude duplicates which are not FA)
        per_fp = len([r for r in error_rows if r["status"] == "FP" and r["event_type"] == event_type])
        per_fn = len([r for r in error_rows if r["status"] == "FN" and r["event_type"] == event_type])
        per_tp = len([r for r in match_rows if r["event_type"] == event_type])
        precision = _safe_div(per_tp, per_tp + per_fp)
        recall = _safe_div(per_tp, per_tp + per_fn)
        by_event[event_type] = {
            "tp": per_tp,
            "fp": per_fp,
            "fn": per_fn,
            "duplicates": len([r for r in error_rows if r["status"] == "DUP" and r["event_type"] == event_type]),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(_safe_div(2 * precision * recall, precision + recall), 4),
            "false_alarms_per_hour": round(_safe_div(per_fp, total_video_hours), 4),
            "delay": _delay_stats([r["delay_s"] for r in match_rows if r["event_type"] == event_type]),
        }

    total_tp = len([r for r in match_rows])
    total_fp = len([r for r in error_rows if r["status"] == "FP"])
    total_fn = len([r for r in error_rows if r["status"] == "FN"])
    total_dup = len([r for r in error_rows if r["status"] == "DUP"])
    total_preds = len(pred_all)

    micro_precision = _safe_div(total_tp, total_tp + total_fp)
    micro_recall = _safe_div(total_tp, total_tp + total_fn)
    # Macro averages over event types that actually have ground truth
    # (tp + fn > 0); a type with no GT contributes no spurious 0.0.
    macro_events = [v for v in by_event.values() if v["tp"] + v["fn"] > 0]
    macro_p = _macro_mean([v["precision"] for v in macro_events])
    macro_r = _macro_mean([v["recall"] for v in macro_events])
    macro_f1 = _macro_mean([v["f1"] for v in macro_events])

    return {
        "total_video_hours": round(total_video_hours, 4),
        "by_event": by_event,
        "overall_micro": {
            "tp": total_tp, "fp": total_fp, "fn": total_fn,
            "precision": round(micro_precision, 4),
            "recall": round(micro_recall, 4),
            "f1": round(_safe_div(2 * micro_precision * micro_recall, micro_precision + micro_recall), 4),
            "false_alarms_per_hour": round(_safe_div(total_fp, total_video_hours), 4),
            "duplicates": total_dup,
            "duplicate_rate": round(_safe_div(total_dup, total_preds), 4),
            "predictions": total_preds,
            "delay": _delay_stats(all_delays),
        },
        "overall_macro": {
            "precision": macro_p, "recall": macro_r, "f1": macro_f1,
        },
        "matches": match_rows,
        "errors": error_rows,
        "tolerances_s": tolerances,
        "deterministic": True,
    }


def write_csv(path: str | Path, columns: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})
