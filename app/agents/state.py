"""LangGraph state schema for the event enrichment agent."""

from __future__ import annotations

from typing import Any, TypedDict

from app.common.schemas import EnrichmentOutput


class EnrichmentState(TypedDict, total=False):
    """State for the enrichment graph.

    ``event`` holds the *controlled metadata* of an EventCandidate (no raw
    frames, no artifact bytes). Every field is optional because nodes run at
    different points of the graph.
    """

    event: dict[str, Any]
    llm_prompt: str
    llm_system_prompt: str
    raw_response: str
    output: EnrichmentOutput
    fallback_used: bool
    telemetry: dict[str, Any]
    error: str | None
