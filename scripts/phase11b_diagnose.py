"""Summarize optional Phase7C traces without changing runtime decisions.

Run inference first:
  $env:PHASE11B_TRACE=1
  $env:PHASE11_OUTPUT_PATH='artifacts/phase11b/predictions_all.jsonl'
  third_party\\deimv2\\.python311\\python.exe scripts/phase11_infer.py
Then run this script with the repository test Python.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


OUT = Path("artifacts/phase11b")
TRACE_DIR = OUT / "traces"
GT_PATH = Path("evaluation/phase11a/ground_truth_events.jsonl")
FAILURE_ORDER = [
    "TRACKER_MISS", "TRACK_FRAGMENTATION", "QUALITY_REJECT", "STITCH_FAILURE",
    "STATIONARY_NOT_CONFIRMED", "OWNER_NOT_ASSOCIATED", "OWNER_ASSOCIATION_WRONG",
    "OWNER_AWAY_NOT_REACHED", "CANDIDATE_NOT_EMITTED", "ADAPTER_FAILURE",
    "EVENT_MANAGER_FAILURE", "SAMPLING_GAP", "GT_AMBIGUITY", "UNKNOWN",
]
STATE_RANK = {
    "QUALITY_REJECTED": 1, "TRACKED": 2, "STATIONARY_PENDING": 3,
    "OWNER_UNASSIGNED": 4, "OWNER_AWAY_PENDING": 5, "CANDIDATE": 6,
}


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _positive_clips() -> dict[str, dict]:
    return {
        event["clip_id"]: event
        for event in _read_jsonl(GT_PATH)
        if event["event_type"] == "ABANDONED_OBJECT"
    }


def _best_luggage(rows: list[dict], event: dict) -> list[dict]:
    by_luggage: dict[str, list[dict]] = {}
    for row in rows:
        if not float(event["start_s"]) - 2.0 <= float(row["time_s"]) <= float(event["end_s"]) + 2.0:
            continue
        by_luggage.setdefault(row["physical_luggage_id"], []).append(row)
    return max(
        by_luggage.values(),
        key=lambda values: (max(STATE_RANK.get(v["candidate_state"], 0) for v in values), len(values)),
        default=[],
    )


def _summary(clip_id: str, event: dict, rows: list[dict]) -> dict:
    best = _best_luggage(rows, event)
    states = {row["candidate_state"] for row in best}
    hints = [row["failure_hint"] for row in best if row.get("failure_hint")]
    emitted = any(row["event_emitted"] for row in best)
    failure = None if emitted else (hints[-1] if hints else "TRACKER_MISS")
    return {
        "clip_id": clip_id,
        "gt_event_id": event["event_id"],
        "gt_trigger_s": event["trigger_time_s"],
        "luggage_detected": bool(best),
        "track_created": bool(best),
        "quality_passed": any(row.get("quality_pass") for row in best),
        "stitch_ok": bool(states - {"QUALITY_REJECTED", "TRACKED"}),
        "stationary_confirmed": bool(states & {"OWNER_UNASSIGNED", "OWNER_AWAY_PENDING", "CANDIDATE"}),
        "owner_associated": any(row.get("owner_track_id") is not None for row in best),
        "owner_away_confirmed": "CANDIDATE" in states,
        "candidate_created": "CANDIDATE" in states,
        "event_emitted": emitted,
        "first_failing_stage": failure,
        "evidence": f"trace_rows={len(best)} states={','.join(sorted(states))}",
        "notes": "GT-window trace heuristic; physical identity remains visually unverified.",
    }


def _write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    positives = _positive_clips()
    summaries = []
    for clip_id, event in positives.items():
        trace = TRACE_DIR / f"{clip_id}.jsonl"
        summaries.append(_summary(clip_id, event, _read_jsonl(trace) if trace.exists() else []))
    columns = list(summaries[0]) if summaries else []
    _write_csv(OUT / "positive_stage_summary.csv", summaries, columns)
    failures = Counter(row["first_failing_stage"] for row in summaries if row["first_failing_stage"])
    distribution = {
        "total_positive_clips": len(summaries),
        "trace_inputs": {
            clip_id: {
                "sha256": hashlib.sha256((TRACE_DIR / f"{clip_id}.jsonl").read_bytes()).hexdigest(),
                "rows": len(_read_jsonl(TRACE_DIR / f"{clip_id}.jsonl")),
            }
            for clip_id in positives
        },
        "by_stage": {stage: {"count": failures[stage], "share": failures[stage] / len(summaries)}
                     for stage in FAILURE_ORDER if failures[stage]},
    }
    (OUT / "failure_distribution.json").write_text(json.dumps(distribution, indent=2), encoding="utf-8")
    _write_csv(OUT / "negative_stage_summary.csv", [], [
        "clip_id", "negative_category", "luggage_detected", "track_created", "stationary_confirmed",
        "owner_associated", "owner_away_confirmed", "event_emitted", "expected_alert", "result", "notes",
    ])
    dominant = failures.most_common(1)
    status = "DIAGNOSIS COMPLETE — FIX NOT JUSTIFIED" if not dominant or dominant[0][1] < 3 else "FIX INVESTIGATION REQUIRED"
    report = [
        "# Phase 11B Abandoned Targeted Diagnosis", "", "## Status",
        f"- Diagnosis: {status}", "- Fix: Not applied by this diagnostic pass.",
        "- Recommendation: Run negative regression before any targeted fix.", "",
        "## Root-cause evidence", f"- Failure distribution: `{OUT / 'failure_distribution.json'}`",
        "- Positive summaries: `positive_stage_summary.csv`", "",
        "## Limitations",
        "- Negative categories are intentionally blank until real clips are classified; no coverage is fabricated.",
        "- Ground truth remains partially hardened and visually unverified.",
    ]
    (OUT / "phase11b_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
