"""Mock EventCandidate dataset for agent enrichment testing with a real LLM.

Candidates live in datasets/mock_enrichment_candidates.json: 13 entries
across the five event types, varying confidence, track count, dwell,
owner-absence, and zone so severity distribution can be observed.

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

DEFAULT_DATASET = ROOT / "datasets" / "mock_enrichment_candidates.json"


def load_candidates(path: Path = DEFAULT_DATASET) -> list[EventCandidate]:
    with open(path, encoding="utf-8") as f:
        payloads = json.load(f)
    return [
        EventCandidate(
            candidateId=entry["candidateId"],
            eventType=entry["eventType"],
            cameraId="cam_mock",
            zoneId=entry.get("zoneId"),
            sourceType="SIMULATED",
            detectedAt="2026-08-10T09:00:00Z",
            firstSeenAt="2026-08-10T08:59:55Z",
            lastSeenAt="2026-08-10T09:00:00Z",
            confidence=entry["confidence"],
            trackCount=entry["trackCount"],
            observations=entry["observations"],
        )
        for entry in payloads
    ]


async def main(output_dir: str) -> int:
    service = create_enrichment_service(output_dir=output_dir)
    for candidate in load_candidates():
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
