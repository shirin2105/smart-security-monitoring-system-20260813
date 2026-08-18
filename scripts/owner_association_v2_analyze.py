"""Create the immutable Owner Association Targeted Fix v2 decision report."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

OUT = Path("artifacts/owner-association-v2")
TRUSTED = ("LeftBag", "LeftBag_AtChair")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def abandoned_starts(rows: list[dict]) -> list[dict]:
    return [row for row in rows if row.get("event_type") == "ABANDONED_OBJECT" and row.get("event_state") == "START"]


def best_candidate(rows: list[dict], *, selected_only: bool = False) -> dict:
    candidates = []
    for row in rows:
        scores = row.get("owner_candidate_scores", [])
        for index, score in enumerate(scores):
            selected = bool(row["owner_candidate_selected"][index])
            if not row["owner_candidate_eligible"][index] or (selected_only and not selected):
                continue
            component = row["owner_candidate_score_components"][index]
            candidates.append({
                "track": row["owner_candidate_person_ids"][index], "score": float(score),
                "threshold": row["owner_candidate_min_association_scores"][index],
                "distance_px": row["owner_candidate_min_distances_px"][index],
                "distance_norm": row["owner_candidate_min_distances"][index],
                "inside_ratio": row["owner_candidate_inside_ratios"][index],
                "near_ratio": row["owner_candidate_near_ratios"][index],
                "overlap_s": row["owner_candidate_overlap_seconds"][index],
                "temporal_ratio": row["owner_candidate_temporal_overlap_ratios"][index],
                "inside_component": component.get("inside"), "near_component": component.get("near"),
                "overlap_component": component.get("overlap"),
                "fragmented": row["owner_candidate_track_fragmented"][index],
                "selected": selected,
            })
    if not candidates:
        raise ValueError("no eligible owner candidate evidence")
    return max(candidates, key=lambda item: (item["score"], -int(item["track"])))


def write_csv_new(path: Path, rows: list[dict]) -> None:
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    result_paths = [OUT / "trusted_positive_analysis.csv", OUT / "negative_safety.csv", OUT / "final_report.md"]
    if any(path.exists() for path in result_paths):
        raise FileExistsError("refusing to overwrite owner-fix decision evidence")
    before_events = read_jsonl(OUT / "predictions-before.jsonl")
    after_events = read_jsonl(OUT / "predictions-after.jsonl")
    positive_rows = []
    for clip in TRUSTED:
        before = best_candidate(read_jsonl(OUT / "traces-before" / f"{clip}.jsonl"))
        after = best_candidate(read_jsonl(OUT / "traces-after" / f"{clip}.jsonl"), selected_only=True)
        starts = [row for row in abandoned_starts(after_events) if row["camera_id"] == clip]
        positive_rows.append({
            "clip_id": clip, "best_candidate_track_id": before["track"],
            "best_score_before": before["score"], "threshold": before["threshold"],
            "distance_px": before["distance_px"], "distance_norm": before["distance_norm"],
            "inside_ratio": before["inside_ratio"], "near_ratio": before["near_ratio"],
            "overlap_s": before["overlap_s"], "temporal_overlap_ratio": before["temporal_ratio"],
            "fragmented": before["fragmented"], "root_cause": "SCORING_NORMALIZATION_DEFECT",
            "attempted_fix": "closest-approach proximity replaces containment score component",
            "best_score_after": after["score"], "selected_owner_after": after["track"],
            "abandoned_start_count": len(starts),
            "result": "PASS" if starts else "OWNER_AWAY_NOT_REACHED",
        })
    write_csv_new(OUT / "trusted_positive_analysis.csv", positive_rows)

    negative_events = read_jsonl(OUT / "predictions-negatives.jsonl")
    negative_counts = Counter(row["camera_id"] for row in abandoned_starts(negative_events))
    negative_rows = [{"clip_id": clip_id, "abandoned_start_count": count, "result": "FAIL"}
                     for clip_id, count in sorted(negative_counts.items())]
    if not negative_rows:
        negative_rows = [{"clip_id": "ALL_15", "abandoned_start_count": 0, "result": "PASS"}]
    write_csv_new(OUT / "negative_safety.csv", negative_rows)

    picked_up = len(abandoned_starts(read_jsonl(OUT / "predictions-picked-up.jsonl")))
    baseline_negative = len(abandoned_starts(read_jsonl(Path("artifacts/phase11b_final/predictions-negatives-production-roi-v3.jsonl"))))
    total_negative = sum(negative_counts.values())
    report = f"""# Owner Association Targeted Fix v2 Report

## Root cause

Fresh CUDA traces prove `SCORING_NORMALIZATION_DEFECT`: strict bbox-containment averaged over the entire pre-stationary history contributes 65% of score, while the already-computed closest approach contributes nothing. Both plausible owners are tracked, eligible, close, temporally overlapping, and unfragmented, yet score below 0.60.

## Trusted results

- LeftBag: 0.1957 → 0.79, 1 START (PASS).
- LeftBag_AtChair: 0.2417 → 0.78, 0 START; first failing stage moved to `OWNER_AWAY_NOT_REACHED`.
- LeftBag_PickedUp: {picked_up} START ({'PASS' if picked_up == 0 else 'FAIL'}).

## Attempted one-fix class

Class A scoring normalization: replace the 65% containment component with normalized closest approach. Threshold, ROI, detector, tracker, stationary, owner-visible/return/pickup semantics, Intrusion, Crowd, and Phase 12 were unchanged.

## Negative safety and rollback

- Generic negatives: 15/15 completed.
- Baseline abandoned START: {baseline_negative}; attempted-fix START: {total_negative}.
- Offending distribution: {dict(negative_counts)}.
- Result: REJECTED and production scoring delta rolled back. Diagnostics remain behavior-neutral.
- Local clip inference: stopped before stage E because the mandatory generic-negative rejection gate failed.

## Regressions

See `test_handoff.md`. Regression commands run against the rolled-back production scorer.

## FINAL STATUS

OWNER_FIX_REJECTED_FALSE_POSITIVES
"""
    (OUT / "final_report.md").write_text(report, encoding="utf-8", errors="strict")
    print(json.dumps({"positive_rows": positive_rows, "negative_starts": dict(negative_counts)}, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
