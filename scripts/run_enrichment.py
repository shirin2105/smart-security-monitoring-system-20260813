"""Run LLM enrichment on a persisted EventCandidate JSON.

Thin adapter over ``AssessmentRunner``: it loads candidate files, hands
each to the runner, and prints the outcome. All graph/prompt/telemetry/
persistence coordination lives inside the assessment module (architecture
review candidate 3: LangGraph stays private to the assessment module).

Usage:
    python scripts/run_enrichment.py artifacts/backend_events/candidate_*.json
    python scripts/run_enrichment.py --input-dir artifacts/backend_events

With no credential configured (LLM_API_KEY empty), the runner applies the
deterministic fallback; no provider request is made (FR-AI-06, Journey C).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agents import create_assessment_runner  # noqa: E402
from app.common.schemas import EventCandidate  # noqa: E402


def _load_candidates(paths: list[str]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            print(f"[run_enrichment] SKIP missing file: {path}", file=sys.stderr)
            continue
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, list):
            candidates.extend(payload)
        else:
            candidates.append(payload)
    return candidates


def _parse_candidate(payload: dict[str, Any]) -> EventCandidate | None:
    try:
        return EventCandidate.model_validate(payload)
    except Exception as exc:
        print(f"[run_enrichment] SKIP invalid candidate: {type(exc).__name__}", file=sys.stderr)
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Candidate JSON files (defaults to artifacts/backend_events/*.json)",
    )
    parser.add_argument(
        "--input-dir",
        default="artifacts/backend_events",
        help="Directory containing persisted candidate JSON files",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/backend_events",
        help="Where enrichment records are written (service default)",
    )
    args = parser.parse_args()

    if args.inputs:
        payloads = _load_candidates(args.inputs)
    else:
        globbed = sorted(Path(args.input_dir).glob("candidate_*.json"))
        payloads = _load_candidates([str(p) for p in globbed])

    if not payloads:
        print("[run_enrichment] No candidates found.", file=sys.stderr)
        return 1

    import asyncio

    runner = create_assessment_runner(output_dir=args.output_dir)

    async def _run() -> int:
        processed = 0
        for payload in payloads:
            candidate = _parse_candidate(payload)
            if candidate is None:
                continue
            outcome = await runner.assess(candidate)
            status = "fallback" if outcome.status == "fallback" else "llm"
            print(
                f"[run_enrichment] {candidate.candidateId} -> {status} "
                f"-> {Path(args.output_dir) / f'enrichment_{candidate.candidateId}.json'}"
            )
            processed += 1
        return 0 if processed else 1

    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
