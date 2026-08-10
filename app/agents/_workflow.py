"""Private LangGraph workflow behind the deep AssessmentRunner.

Mirror of the legacy graph (``app.agents.graph``) with two differences:
the state shape is local (``WorkflowState``) and the builder is private.
The graph runs on controlled event metadata only, never mutates event
severity/state, and never calls tools (FR-AI-04). On any LLM failure the
``fallback`` node produces a deterministic output (FR-AI-06).

The module name is private: only ``AssessmentRunner`` (``runtime.py``)
may import it; later slices retire the legacy public graph.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.fallback import build_fallback_output
from app.common.schemas import EnrichmentOutput
from app.llm.adapter import LLMAdapter

SYSTEM_PROMPT = """Bạn là trợ lý đánh giá sự kiện an ninh camera.

Chỉ được dùng dữ liệu metadata được cung cấp; không suy đoán danh tính,
ý định phạm tội, hoặc kết luận tội lỗi. Bạn chỉ đề xuất — hệ thống và con
người quyết định. Không được thực hiện hành động bên ngoài.

Trả về chính xác một JSON object với các trường:
- "recommendedSeverity": "INFO" | "WARNING" | "HIGH" | "CRITICAL"
- "rationale": lý do ngắn gọn dựa trên metadata
- "summary": mô tả sự kiện chỉ gồm sự kiện (fact-only)
- "actionChecklist": mảng tối đa 5 mục hành động đề xuất cho người trực

Ràng buộc: ABANDONED_OBJECT tối đa "HIGH". Không thêm trường khác."""


def _build_prompt(event: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Sự kiện an ninh cần đánh giá:",
            f"- eventType: {event.get('eventType')}",
            f"- cameraId: {event.get('cameraId')}",
            f"- zoneId: {event.get('zoneId')}",
            f"- confidence: {event.get('confidence')}",
            f"- trackCount: {event.get('trackCount')}",
            f"- observations: {event.get('observations')}",
            f"- sourceType: {event.get('sourceType')}",
            f"- detectedAt: {event.get('detectedAt')}",
        ]
    )


class WorkflowState(TypedDict, total=False):
    event: dict[str, Any]
    llm_prompt: str
    llm_system_prompt: str
    output: EnrichmentOutput
    fallback_used: bool
    telemetry: dict[str, Any]
    error: str | None


def _compile_graph(llm: LLMAdapter | None):
    adapter = llm

    async def prepare(state: WorkflowState) -> dict:
        event = state["event"]
        return {"llm_prompt": _build_prompt(event), "llm_system_prompt": SYSTEM_PROMPT}

    async def call_provider(state: WorkflowState) -> dict:
        if adapter is None or not adapter.available:
            return {"error": "llm_unavailable", "fallback_used": True}
        output, telemetry = await adapter.enrich_async(
            prompt=state["llm_prompt"],
            system_prompt=state["llm_system_prompt"],
        )
        if output is None:
            provider_error = (telemetry or {}).get("error", "llm_failed")
            return {
                "error": provider_error,
                "fallback_used": True,
                "telemetry": telemetry or {},
            }
        return {"output": output, "fallback_used": False, "telemetry": telemetry or {}}

    async def apply_fallback(state: WorkflowState) -> dict:
        return {
            "output": build_fallback_output(state["event"]),
            "fallback_used": True,
            "error": state.get("error") or "llm_failed",
        }

    def route(state: WorkflowState) -> str:
        return END if state.get("output") is not None else "fallback"

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
    def __init__(self, llm: LLMAdapter | None) -> None:
        self._graph = _compile_graph(llm)

    async def run(self, event: dict[str, Any]) -> WorkflowState:
        return await self._graph.ainvoke({"event": event})
