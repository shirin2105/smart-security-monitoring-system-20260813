"""Mock EventCandidate dataset for agent enrichment testing with a real LLM.

Each entry is (candidate_id, event_type, zone_id, confidence, track_count,
observations). The set varies confidence, track count, dwell, owner-absence,
and zone so severity distribution can be observed across the five event
types. Output goes to a fresh temp dir; run the eval reporter over it.

Usage:
    python scripts/run_mock_enrichment.py
    python scripts/run_mock_enrichment.py --output-dir artifacts/mock-enrichment
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.common.schemas import EventCandidate  # noqa: E402
from app.services.enrichment import create_enrichment_service  # noqa: E402
from app.services.enrichment_eval import EvaluationReporter  # noqa: E402

# (candidate_id, event_type, zone_id, confidence, track_count, observations)
MOCK_CANDIDATES: list[tuple[str, str, str | None, float, int, dict]] = [
    ("mock-real-intrusion-high", "ZONE_INTRUSION", "restricted_gate", 0.97, 1,
     {"personCount": 1, "dwellSeconds": 9.8, "insideZone": True}),
    ("mock-real-intrusion-low", "ZONE_INTRUSION", "restricted_gate", 0.55, 1,
     {"personCount": 1, "dwellSeconds": 1.1, "insideZone": True}),
    ("mock-real-intrusion-multi", "ZONE_INTRUSION", "restricted_gate", 0.91, 3,
     {"personCount": 3, "dwellSeconds": 4.2, "insideZone": True}),
    ("mock-real-crowd-thresh", "CROWD_THRESHOLD", "plaza", 0.83, 12,
     {"personCount": 12, "dwellSeconds": None, "insideZone": True}),
    ("mock-real-crowd-large", "CROWD_THRESHOLD", "plaza", 0.92, 45,
     {"personCount": 45, "dwellSeconds": None, "insideZone": True}),
    ("mock-real-crowd-small", "CROWD_THRESHOLD", "gate_area", 0.66, 4,
     {"personCount": 4, "dwellSeconds": None, "insideZone": True}),
    ("mock-real-abandon-bag", "ABANDONED_OBJECT", "lobby", 0.74, 1,
     {"personCount": 1, "stationarySeconds": 12.0, "ownerAbsentSeconds": 10.0, "insideZone": False}),
    ("mock-real-abandon-owner", "ABANDONED_OBJECT", "corridor", 0.61, 2,
     {"personCount": 2, "stationarySeconds": 6.0, "ownerAbsentSeconds": 1.0, "insideZone": False}),
    ("mock-real-abandon-short", "ABANDONED_OBJECT", "entrance", 0.58, 1,
     {"personCount": 1, "stationarySeconds": 3.5, "ownerAbsentSeconds": 2.0, "insideZone": False}),
    ("mock-real-fall-unattended", "SUSPECTED_FALL", "stairwell", 0.82, 1,
     {"personCount": 1, "insideZone": False}),
    ("mock-real-fall-low", "SUSPECTED_FALL", "corridor", 0.52, 1,
     {"personCount": 1, "insideZone": False}),
    ("mock-real-coverage-blur", "COVERAGE_DEGRADED", None, 0.48, 0,
     {"personCount": 0, "insideZone": False}),
    ("mock-real-coverage-offline", "COVERAGE_DEGRADED", None, 0.9, 0,
     {"personCount": 0, "insideZone": False}),
]


def build_candidates() -> list[EventCandidate]:
    return [
        EventCandidate(
            candidateId=cid,
            eventType=event_type,
            cameraId="cam_mock",
            zoneId=zone,
            sourceType="SIMULATED",
            detectedAt="2026-08-10T09:00:00Z",
            firstSeenAt="2026-08-10T08:59:55Z",
            lastSeenAt="2026-08-10T09:00:00Z",
            confidence=confidence,
            trackCount=track_count,
            observations=observations,
        )
        for cid, event_type, zone, confidence, track_count, observations in MOCK_CANDIDATES
    ]


async def main(output_dir: str) -> int:
    service = create_enrichment_service(output_dir=output_dir)
    for candidate in build_candidates():
        result = await service.enrich(candidate)
        assessment = result.assessment
        print(
            f"{candidate.eventType.value:18s} conf={candidate.confidence:<4} "
            f"sev={assessment.severity:8s} action={assessment.recommended_action:28s} "
            f"fb={str(result.fallback_used):5s}",
            flush=True,
        )
    print()
    report = EvaluationReporter(output_dir).report()
    print(json.dumps(report, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default=tempfile.mkdtemp(prefix="mock-enrichment-"),
        help="Where assessment records are written (default: fresh temp dir)",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.output_dir)))
