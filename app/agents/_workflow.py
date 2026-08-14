"""Private LangGraph workflow behind the deep AssessmentRunner.

The state is fully typed (``WorkflowState``): the candidate is passed as
``EventCandidate`` and the provider returns ``ProviderResult``; on any
LLM failure the ``fallback`` node produces a deterministic ``ProviderDraft``
(FR-AI-06). The graph runs on controlled event metadata only, never
mutates event severity/state, and never calls tools (FR-AI-04).

The module name is private: only ``AssessmentRunner`` (``runtime.py``)
may import it; later slices retire the legacy public graph.
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.policy import fallback_draft
from app.agents.provider import AssessmentProvider, ProviderDraft, ProviderResult
from app.common.schemas import EventCandidate

SYSTEM_PROMPT = """Bạn là trợ lý đánh giá sự kiện an ninh camera.

Chỉ dùng metadata được cung cấp. Không suy đoán danh tính, ý định phạm tội,
hoặc kết luận tội lỗi. Không thực hiện hành động bên ngoài.

Trả về chính xác một JSON object gồm:
- "recommendedSeverity": "INFO" | "WARNING" | "HIGH" | "CRITICAL"
- "rationale": lý do ngắn gọn, chỉ dựa trên metadata

ABANDONED_OBJECT tối đa "HIGH". Không thêm trường khác."""


def _build_prompt(candidate: EventCandidate) -> str:
    return "\n".join(
        [
            "Sự kiện an ninh cần đánh giá:",
            f"- eventType: {candidate.eventType.value}",
            f"- cameraId: {candidate.cameraId}",
            f"- zoneId: {candidate.zoneId}",
            f"- confidence: {candidate.confidence}",
            f"- trackCount: {candidate.trackCount}",
            f"- observations: {candidate.observations.model_dump(mode='json')}",
            f"- sourceType: {candidate.sourceType}",
            f"- detectedAt: {candidate.detectedAt}",
        ]
    )


class WorkflowState(TypedDict, total=False):
    candidate: EventCandidate
    prompt: str
    system_prompt: str
    provider_result: ProviderResult
    draft: ProviderDraft
    fallback_used: bool


def _compile_graph(provider: AssessmentProvider | None):
    async def prepare(state: WorkflowState) -> dict:
        return {
            "prompt": _build_prompt(state["candidate"]),
            "system_prompt": SYSTEM_PROMPT,
        }

    async def call_provider(state: WorkflowState) -> dict:
        if provider is None:
            result = ProviderResult(
                draft=None,
                latency_ms=0.0,
                model_name="",
                error="llm_disabled",
            )
        else:
            result = await provider.assess(
                prompt=state["prompt"],
                system_prompt=state["system_prompt"],
            )
        updates = {"provider_result": result, "fallback_used": result.draft is None}
        if result.draft is not None:
            updates["draft"] = result.draft
        return updates

    async def apply_fallback(state: WorkflowState) -> dict:
        result = state["provider_result"]
        return {
            "draft": fallback_draft(
                state["candidate"],
                reason=result.error or "provider_output_invalid",
            ),
            "fallback_used": True,
        }

    def route(state: WorkflowState) -> str:
        return END if state.get("draft") is not None else "fallback"

    graph = StateGraph(WorkflowState)
    graph.add_node("prepare", prepare)
    graph.add_node("provider", call_provider)
    graph.add_node("fallback", apply_fallback)
    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "provider")
    graph.add_conditional_edges("provider", route, {END: END, "fallback": "fallback"})
    graph.add_edge("fallback", END)
    return graph.compile()


class AssessmentWorkflow:
    def __init__(self, provider: AssessmentProvider | None) -> None:
        self._graph = _compile_graph(provider)

    async def run(self, candidate: EventCandidate) -> WorkflowState:
        return await self._graph.ainvoke({"candidate": candidate})
