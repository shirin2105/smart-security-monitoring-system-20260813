"""Runtime enrichment service: persisted EventCandidate → AgentAssessment.

Owns the enrichment graph invocation for the ingest pipeline (FR-AI-07).
Advisory only: the output never mutates the candidate's severity or state.
Any provider failure or persist error resolves to a fallback result instead
of raising, so the ingest boundary is never blocked by the agent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.agents.fallback import build_fallback_output
from app.agents.graph import build_enrichment_graph
from app.common.schemas import EnrichmentOutput
from app.llm.adapter import LLMAdapter

ENRICHMENT_SUFFIX = "enrichment_{candidate_id}.json"


@dataclass
class EnrichmentResult:
    output: EnrichmentOutput
    fallback_used: bool
    error: str | None
    telemetry: dict[str, Any] | None


class EnrichmentService:
    """Enriches event candidates and persists the advisory result."""

    def __init__(
        self,
        output_dir: str = "artifacts/backend_events",
        llm_adapter: LLMAdapter | None = None,
        enabled: bool = True,
    ):
        self.output_dir = Path(output_dir)
        self.llm_adapter = llm_adapter
        self.enabled = enabled

    def _adapter(self) -> LLMAdapter | None:
        if self.llm_adapter is not None:
            return self.llm_adapter
        if self.enabled:
            from app.llm.adapter import create_llm_adapter

            return create_llm_adapter()
        return None

    async def enrich(self, candidate: Any) -> EnrichmentResult:
        """Run the enrichment graph on one candidate and persist the result.

        Never raises: provider failure, missing credentials, and persist
        errors all resolve to a deterministic fallback output (FR-AI-06).
        """
        event = candidate.model_dump(mode="json")
        adapter = self._adapter()
        graph = build_enrichment_graph(llm=adapter)
        result = await graph.ainvoke({"event": event})

        output: EnrichmentOutput = result["output"]
        fallback_used = bool(result.get("fallback_used"))
        error = result.get("error")
        telemetry = result.get("telemetry")

        persist_error = self._persist(candidate, output, telemetry, fallback_used, error)
        if persist_error is not None:
            fallback_used = True
            error = persist_error

        return EnrichmentResult(
            output=output,
            fallback_used=fallback_used,
            error=error,
            telemetry=telemetry,
        )

    def _persist(
        self,
        candidate: Any,
        output: EnrichmentOutput,
        telemetry: dict[str, Any] | None,
        fallback_used: bool,
        error: str | None,
    ) -> str | None:
        candidate_id = str(getattr(candidate, "candidateId", "unknown"))
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            record = {
                "candidateId": candidate_id,
                "eventType": getattr(candidate, "eventType", None),
                "enrichment": output.model_dump(mode="json"),
                "telemetry": {
                    "latencyMs": (telemetry or {}).get("latency_ms", 0.0),
                    "model": (telemetry or {}).get("model", ""),
                    "fallbackUsed": fallback_used,
                    "outputValid": True,
                    "error": error,
                },
            }
            target = self.output_dir / ENRICHMENT_SUFFIX.format(candidate_id=candidate_id)
            with open(target, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2, ensure_ascii=False)
            return None
        except OSError as exc:
            return f"enrichment_persist_failed:{type(exc).__name__}"


def fallback_for_test(event: dict) -> EnrichmentOutput:
    """Deterministic fallback, exported for tests and evaluation tooling."""
    return build_fallback_output(event)
