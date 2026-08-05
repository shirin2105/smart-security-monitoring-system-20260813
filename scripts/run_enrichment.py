"""Run LLM enrichment on a persisted EventCandidate JSON.

Usage:
    python scripts/run_enrichment.py artifacts/backend_events/candidate_*.json
    python scripts/run_enrichment.py --input artifacts/backend_events/candidate_cam_01.json

With no credential configured (LLM_API_KEY empty), the graph applies the
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

from app.agents.graph import build_enrichment_graph  # noqa: E402
from app.common.schemas import EnrichmentOutput, EnrichmentTelemetry
from app.config import settings
from app.llm.adapter import create_llm_adapter


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


async def _run(candidates: list[dict[str, Any]], out: Path) -> None:
    adapter = create_llm_adapter()
    graph = build_enrichment_graph(llm=adapter)
    out.mkdir(parents=True, exist_ok=True)

    for event in candidates:
        result = await graph.ainvoke({"event": event})
        output: EnrichmentOutput = result["output"]
        telemetry = EnrichmentTelemetry(
            eventType=str(event.get("eventType", "")),
            candidateId=str(event.get("candidateId", "")),
            latencyMs=result.get("telemetry", {}).get("latency_ms", 0.0),
            model=result.get("telemetry", {}).get("model", settings.llm_model),
            fallbackUsed=bool(result.get("fallback_used")),
            outputValid=True,
            error=result.get("error"),
        )
        record = {
            "candidateId": event.get("candidateId"),
            "eventType": event.get("eventType"),
            "enrichment": output.model_dump(mode="json"),
            "telemetry": telemetry.model_dump(mode="json"),
        }
        target = out / f"enrichment_{event.get('candidateId', 'unknown')}.json"
        with open(target, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        status = "fallback" if telemetry.fallbackUsed else "llm"
        print(f"[run_enrichment] {event.get('candidateId')} -> {status} -> {target}")


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
        default="artifacts/enrichment",
        help="Where enrichment records are written",
    )
    args = parser.parse_args()

    if args.inputs:
        candidates = _load_candidates(args.inputs)
    else:
        globbed = sorted(Path(args.input_dir).glob("candidate_*.json"))
        candidates = _load_candidates([str(p) for p in globbed])

    if not candidates:
        print("[run_enrichment] No candidates found.", file=sys.stderr)
        return 1

    import asyncio

    asyncio.run(_run(candidates, Path(args.output_dir)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
