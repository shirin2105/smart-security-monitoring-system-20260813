"""Summarize real Phase 11B.1 owner-association diagnostic traces."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


OUT = Path("artifacts/phase11b1")
TRACE_DIR = OUT / "traces-precheck"
GT_PATH = Path("evaluation/phase11a/ground_truth_events.jsonl")
CLIPS = ("LeftBag", "LeftBag_AtChair", "LeftBag_PickedUp", "LeftBox")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def best_luggage(rows: list[dict], event: dict) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        if event["start_s"] - 2 <= row["time_s"] <= event["end_s"] + 2:
            grouped.setdefault(row["physical_luggage_id"], []).append(row)
    return max(grouped.values(), key=lambda group: (sum(r.get("stationary_confirmed_at_s") is not None for r in group), len(group)), default=[])


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    events = {row["clip_id"]: row for row in read_jsonl(GT_PATH) if row["event_type"] == "ABANDONED_OBJECT"}
    summaries = []
    rejection_counts: Counter[str] = Counter()
    trace_inputs = {}
    for clip_id in CLIPS:
        path = TRACE_DIR / f"{clip_id}.jsonl"
        rows = read_jsonl(path)
        chosen = best_luggage(rows, events[clip_id])
        precheck_reasons = [r["owner_association_precheck_rejection_reason"] for r in chosen if r.get("owner_association_precheck_rejection_reason")]
        owner_reasons = [r["owner_rejection_reason"] for r in chosen if r.get("owner_rejection_reason")]
        reason = Counter(owner_reasons).most_common(1)[0][0] if owner_reasons else (
            Counter(precheck_reasons).most_common(1)[0][0] if precheck_reasons else "MISSING_DIAGNOSTIC_EVIDENCE"
        )
        rejection_counts[reason] += 1
        scores = [(score, person_id, distance) for row in chosen for score, person_id, distance in zip(
            row.get("owner_candidate_scores", []), row.get("owner_candidate_person_ids", []), row.get("owner_candidate_min_distances", [])
        ) if score is not None]
        best = max(scores, default=(None, None, None))
        summaries.append({
            "clip_id": clip_id,
            "gt_event_id": events[clip_id]["event_id"],
            "stationary_confirmed_at_s": next((r["stationary_confirmed_at_s"] for r in chosen if r.get("stationary_confirmed_at_s") is not None), ""),
            "candidate_before_stationary": bool(scores) if owner_reasons else "",
            "best_candidate_before_track_id": best[1] or "",
            "best_candidate_before_distance": best[2] if best[2] is not None else "",
            "best_candidate_before_score": best[0] if best[0] is not None else "",
            "candidate_at_stationary": "",
            "best_candidate_at_stationary_track_id": "",
            "best_candidate_at_stationary_distance": "",
            "best_candidate_at_stationary_score": "",
            "candidate_disappeared_before_confirm": "",
            "candidate_fragmented": "",
            "rejection_reason": reason,
            "selected_owner_track_id": next((r["selected_owner_person_id"] for r in chosen if r.get("selected_owner_person_id") is not None), ""),
            "event_emitted": any(r["event_emitted"] for r in chosen),
            "notes": f"owner precheck ROI rejects={len(precheck_reasons)}; owner association attempts with candidates={len(scores)}",
        })
        trace_inputs[clip_id] = {"rows": len(rows), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    write_csv(OUT / "positive_owner_analysis.csv", summaries, list(summaries[0]))
    negatives = [{
        "clip_id": "NOT_COVERED", "negative_category": category,
        "owner_candidate_created": "", "owner_associated": "", "selected_owner_track_id": "",
        "owner_away_confirmed": "", "event_emitted": "", "expected_event": False,
        "result": "NOT_COVERED", "notes": "No real classified clip supplied in the bundle/dataset mapping.",
    } for category in ("owner_stays", "pickup", "brief_return", "pre_existing", "fixed_object", "carrying", "multiple_people")]
    write_csv(OUT / "negative_owner_safety.csv", negatives, list(negatives[0]))
    distribution = {
        "total_positive_clips": len(CLIPS), "trace_inputs": trace_inputs,
        "by_reason": {reason: {"count": count, "share": count / len(CLIPS)} for reason, count in rejection_counts.items()},
    }
    (OUT / "rejection_distribution.json").write_text(json.dumps(distribution, indent=2), encoding="utf-8")
    reason_rows = "\n".join(
        f"| {reason} | {data['count']} | {data['share']:.0%} |"
        for reason, data in distribution["by_reason"].items()
    )
    dominant = max(distribution["by_reason"], key=lambda key: distribution["by_reason"][key]["count"])
    diagnosis_complete = len(distribution["by_reason"]) == 1 and dominant != "MISSING_DIAGNOSTIC_EVIDENCE"
    root_cause = dominant if diagnosis_complete else "mixed or missing diagnostic evidence"
    emitted_count = sum(bool(row["event_emitted"]) for row in summaries)
    no_owner_scores = all(not row["best_candidate_before_score"] for row in summaries)
    roi_blocked = diagnosis_complete and dominant == "LUGGAGE_OUTSIDE_VALID_FLOOR_ROI"
    mechanism = (
        "Owner association is not reached, so an owner-memory change cannot affect these failures."
        if roi_blocked else "The computed rejection distribution does not justify a single owner-memory fix."
    )
    recommendation = (
        "validate the configured valid-floor ROI against positive GT" if roi_blocked
        else "collect or inspect the missing/mixed stage evidence"
    )
    report = f"""# Phase 11B.1 Owner Association Report

## Status
- Diagnosis: {"complete" if diagnosis_complete else "incomplete"} for all four locked positives.
- Root cause: {root_cause}.
- Fix: not applied. The bundle permits one owner fix only when owner-association evidence supports it.
- Recommendation: continue Phase 11B and {recommendation}; do not start Phase 12.

## Rejection reason distribution
| Reason | Count | Share |
|---|---:|---:|
{reason_rows}

## Proven mechanism
- Owner candidate scores absent in all selected histories: {no_owner_scores}.
- Distribution generated from exact precheck/owner rejection reasons; see `rejection_distribution.json`.
- {mechanism}

## Before vs after
| Metric | Before | After | Delta |
|---|---:|---:|---:|
| TP | 0 | {emitted_count} | {emitted_count} |
| FP | not measured | not measured | not measured |
| FN | 4 | {len(CLIPS) - emitted_count} | {-emitted_count} |
| Recall | 0 | {emitted_count / len(CLIPS):.3f} | {emitted_count / len(CLIPS):.3f} |
| F1 | not measured | not measured | not measured |

## Negative safety
- All requested real negative categories: NOT COVERED; no classified mapping was supplied.
- No owner logic, threshold, tracker, detector, sampling, or ROI behavior changed.

## Non-regression
- See test handoff for focused/full CV results.

## Decision
- Continue Phase 11B, not Phase 12. Next action: {recommendation} before authorizing a different targeted fix.

## Unresolved questions
- Is the central ROI intentionally the valid floor for these four CAVIAR positives?
"""
    (OUT / "phase11b1_report.md").write_text(report, encoding="utf-8")
    print(json.dumps(distribution["by_reason"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
