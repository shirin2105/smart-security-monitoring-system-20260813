"""LangGraph enrichment graph: detect → assess → plan → enrich.

Runs on controlled event metadata only. The graph never mutates event
severity/state and never calls tools (FR-AI-04). On any LLM failure the
``fallback`` node produces a deterministic output (FR-AI-06).
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.fallback import build_fallback_output
from app.agents.state import EnrichmentState
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


def _build_prompt(event: dict) -> str:
    lines = [
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
    return "\n".join(lines)


def build_enrichment_graph(llm: LLMAdapter | None = None):
    adapter = llm

    async def assess_node(state: EnrichmentState) -> dict:
        """Prepare the LLM call from controlled metadata."""
        event = state.get("event", {})
        return {
            "llm_prompt": _build_prompt(event),
            "llm_system_prompt": SYSTEM_PROMPT,
        }

    async def llm_node(state: EnrichmentState) -> dict:
        """Call the LLM; on failure store the error and route to fallback."""
        if adapter is None or not adapter.available:
            return {"error": "llm_unavailable", "fallback_used": True}
        prompt = state.get("llm_prompt", "")
        system = state.get("llm_system_prompt", SYSTEM_PROMPT)
        output, telemetry = await adapter.enrich_async(prompt=prompt, system_prompt=system)
        if output is None:
            return {
                "error": telemetry.get("error", "llm_failed"),
                "fallback_used": True,
                "telemetry": telemetry,
            }
        return {"output": output, "fallback_used": False, "telemetry": telemetry}

    async def fallback_node(state: EnrichmentState) -> dict:
        """Deterministic fallback when the LLM failed."""
        event = state.get("event", {})
        updates: dict = {"output": build_fallback_output(event), "fallback_used": True}
        if state.get("error") is None:
            updates["error"] = "llm_failed"
        return updates

    def route_after_llm(state: EnrichmentState) -> str:
        if state.get("output") is not None:
            return END
        return "fallback"

    graph = StateGraph(EnrichmentState)
    graph.add_node("assess", assess_node)
    graph.add_node("llm", llm_node)
    graph.add_node("fallback", fallback_node)

    graph.add_edge(START, "assess")
    graph.add_edge("assess", "llm")
    graph.add_conditional_edges("llm", route_after_llm, {END: END, "fallback": "fallback"})
    graph.add_edge("fallback", END)

    return graph.compile()


enrichment_graph = build_enrichment_graph()
