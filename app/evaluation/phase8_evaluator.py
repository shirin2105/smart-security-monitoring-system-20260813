from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Iterable

from app.evaluation.phase8_schema import (
    ERROR_CATEGORIES,
    VALID_EVENT_TYPES,
    GroundTruthEvent,
    PredictedEvent,
)


DEFAULT_TOLERANCES_S = {
    "ZONE_INTRUSION": 2.0,
    "CROWD_THRESHOLD": 3.0,
    "ABANDONED_OBJECT": 5.0,
}


def _safe_div(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def _validate_unique(events: Iterable[GroundTruthEvent | PredictedEvent], label: str) -> None:
    seen = set()
    for event in events:
        key = (event.clip_id, event.camera_id, event.event_id)
        if key in seen:
            raise ValueError(f"duplicate {label} event identity={key}")
        seen.add(key)


def _compatible(gt: GroundTruthEvent, pred: PredictedEvent, tolerance_s: float) -> bool:
    if (gt.clip_id, gt.camera_id, gt.event_type) != (
        pred.clip_id,
        pred.camera_id,
        pred.event_type,
    ):
        return False
    if gt.zone_id and pred.evidence.get("zone_id") not in (None, gt.zone_id):
        return False
    return gt.trigger_time_s <= pred.event_time_s <= gt.end_s + tolerance_s


def _match(
    gt_events: list[GroundTruthEvent],
    pred_events: list[PredictedEvent],
    tolerances: dict[str, float],
) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    candidates = []
    for gt_index, gt in enumerate(gt_events):
        tolerance = float(tolerances.get(gt.event_type, 3.0))
        for pred_index, pred in enumerate(pred_events):
            if _compatible(gt, pred, tolerance):
                candidates.append((abs(pred.event_time_s - gt.trigger_time_s), gt_index, pred_index))
    used_gt: set[int] = set()
    used_pred: set[int] = set()
    matches: list[tuple[int, int]] = []
    for _, gt_index, pred_index in sorted(candidates):
        if gt_index not in used_gt and pred_index not in used_pred:
            used_gt.add(gt_index); used_pred.add(pred_index)
            matches.append((gt_index, pred_index))
    return (
        matches,
        [index for index in range(len(gt_events)) if index not in used_gt],
        [index for index in range(len(pred_events)) if index not in used_pred],
    )


def load_attributions(path: str | Path | None) -> dict[tuple[str, str, str, str], dict[str, str]]:
    if path is None or not Path(path).exists():
        return {}
    rows: dict[tuple[str, str, str, str], dict[str, str]] = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            category = row.get("error_category", "UNKNOWN") or "UNKNOWN"
            if category not in ERROR_CATEGORIES:
                raise ValueError(f"unsupported error_category={category}")
            key_id = row.get("gt_event_id") or row.get("pred_event_id")
            if not key_id:
                raise ValueError("attribution row requires gt_event_id or pred_event_id")
            key = (str(row.get("clip_id")), str(row.get("event_type")),
                   str(row.get("status")), str(key_id))
            if key in rows:
                raise ValueError(f"duplicate attribution key={key}")
            rows[key] = row
    return rows


def _error_row(status: str, event_type: str, clip_id: str, gt_id: str | None,
               pred_id: str | None, attributions: dict) -> dict:
    key = (clip_id, event_type, status, str(gt_id or pred_id))
    supplied = attributions.get(key, {})
    return {
        "status": status,
        "event_type": event_type,
        "clip_id": clip_id,
        "gt_event_id": gt_id,
        "pred_event_id": pred_id,
        "error_category": supplied.get("error_category") or "UNKNOWN",
        "root_cause_notes": supplied.get("root_cause_notes") or "",
        "component_to_change": supplied.get("component_to_change") or "",
        "retest_required": supplied.get("retest_required") or "yes",
    }


def evaluate_events(gt_events: Iterable[GroundTruthEvent], pred_events: Iterable[PredictedEvent],
                    total_video_hours: float, tolerances_s: dict[str, float] | None = None,
                    attributions: dict | None = None) -> dict:
    if total_video_hours <= 0:
        raise ValueError("total_video_hours must be positive")
    gt_all, pred_all = list(gt_events), list(pred_events)
    _validate_unique(gt_all, "ground-truth")
    _validate_unique(pred_all, "prediction")
    tolerances = dict(tolerances_s or DEFAULT_TOLERANCES_S)
    attributions = attributions or {}
    by_type = {}; match_rows = []; error_rows = []; all_delays = []
    total_tp = total_fp = total_fn = alert_fp = 0
    for event_type in sorted(VALID_EVENT_TYPES):
        gt = [event for event in gt_all if event.event_type == event_type]
        pred = [event for event in pred_all if event.event_type == event_type]
        matches, missing_gt, missing_pred = _match(gt, pred, tolerances)
        delays = []
        for gt_index, pred_index in matches:
            delay = pred[pred_index].event_time_s - gt[gt_index].trigger_time_s
            delays.append(delay); all_delays.append(delay)
            match_rows.append({"status": "TP", "event_type": event_type,
                "clip_id": gt[gt_index].clip_id, "gt_event_id": gt[gt_index].event_id,
                "pred_event_id": pred[pred_index].event_id, "delay_s": delay})
        for index in missing_gt:
            error_rows.append(_error_row("FN", event_type, gt[index].clip_id,
                                         gt[index].event_id, None, attributions))
        for index in missing_pred:
            error_rows.append(_error_row("FP", event_type, pred[index].clip_id,
                                         None, pred[index].event_id, attributions))
        tp, fp, fn = len(matches), len(missing_pred), len(missing_gt)
        precision, recall = _safe_div(tp, tp + fp), _safe_div(tp, tp + fn)
        candidate_only = event_type == "ABANDONED_OBJECT"
        by_type[event_type] = {
            "tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall,
            "f1": _safe_div(2 * precision * recall, precision + recall),
            "evaluation_scope": "CANDIDATE_ONLY" if candidate_only else "ALERT",
            "false_alarms_per_hour": None if candidate_only else _safe_div(fp, total_video_hours),
            "false_candidates_per_hour": (_safe_div(fp, total_video_hours)
                                            if candidate_only else None),
            "mean_detection_delay_s": mean(delays) if delays else None,
            "median_detection_delay_s": median(delays) if delays else None,
        }
        total_tp += tp; total_fp += fp; total_fn += fn
        if not candidate_only:
            alert_fp += fp
    precision = _safe_div(total_tp, total_tp + total_fp)
    recall = _safe_div(total_tp, total_tp + total_fn)
    counts = Counter(row["error_category"] for row in error_rows)
    return {
        "overall": {"tp": total_tp, "fp": total_fp, "fn": total_fn,
            "precision": precision, "recall": recall,
            "f1": _safe_div(2 * precision * recall, precision + recall),
            "false_alarms_per_hour": _safe_div(alert_fp, total_video_hours),
            "false_event_predictions_per_hour": _safe_div(total_fp, total_video_hours),
            "confirmed_alarm_metrics_complete": False,
            "mean_detection_delay_s": mean(all_delays) if all_delays else None,
            "median_detection_delay_s": median(all_delays) if all_delays else None,
            "total_video_hours": total_video_hours},
        "by_event_type": by_type,
        "matches": match_rows,
        "errors": error_rows,
        "error_attribution_counts": dict(sorted(counts.items())),
        "unattributed_error_count": counts.get("UNKNOWN", 0),
        "attribution_complete": counts.get("UNKNOWN", 0) == 0,
        "tolerances_s": tolerances,
    }
