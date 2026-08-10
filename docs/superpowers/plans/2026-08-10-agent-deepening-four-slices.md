# Agent Deepening in Four Vertical TDD Slices Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the shallow Agent graph, scattered policy, duplicated record parsing, and silent background handoff with one deep typed assessment module delivered through four vertical TDD slices.

**Architecture:** `EventCandidate` remains the stable external seam. `AssessmentRunner` owns a private, once-compiled LangGraph implementation, provider/fallback routing, authoritative policy, typed outcomes, and record persistence; FastAPI schedules it through an observable best-effort handoff. Existing ingest and record contracts stay compatible while internal Python interfaces are replaced.

**Tech Stack:** Python 3.11, Pydantic 2, LangGraph, LangChain OpenAI adapter, FastAPI, pytest/pytest-asyncio, Coverage.py, Ruff.

## Global Constraints

- Implement all four architecture candidates as four sequential vertical TDD slices.
- Preserve controlled compatibility: `EventCandidate`, ingest endpoint behavior, record filename, top-level record keys, and the 13-field `AgentAssessment` shape remain stable.
- LangGraph stays private and compiles once per `AssessmentRunner` instance.
- Provider output contains only `recommendedSeverity` and `rationale`; `summary` and `actionChecklist` leave the authoritative path.
- Handoff remains best-effort but observable; do not add a queue, outbox, retry worker, or crash-recovery promise.
- Agent assessment remains advisory and never mutates a candidate or executes an external action.
- Replace tests of shallow modules after the same behavior is covered through the deep interface.
- Agent-scope line coverage must remain at or above 90 percent.
- Preserve unrelated worktree changes; stage only files owned by the current task.
- Design source: `docs/superpowers/specs/2026-08-10-agent-deepening-four-slices-design.md`.

---

## File Structure

### Create

- `app/agents/runtime.py` — public deep `AssessmentRunner` module and composition factory.
- `app/agents/_workflow.py` — private LangGraph state, prompt, nodes, and routing.
- `app/agents/provider.py` — internal provider port, strict draft, and typed provider result.
- `app/agents/policy.py` — authoritative severity/action policy and deterministic fallback.
- `app/agents/record.py` — typed record, legacy-compatible serialization, filesystem adapter, and iteration.
- `app/agents/handoff.py` — observable best-effort background execution.
- `tests/unit/test_assessment_runtime.py` — behavioral tests through the deep Agent interface.
- `tests/unit/test_assessment_policy.py` — pure policy and fallback tests.
- `tests/unit/test_assessment_record.py` — record round-trip and compatibility tests.
- `tests/unit/test_assessment_handoff.py` — structured completion/failure log tests.

### Modify

- `app/agents/__init__.py` — export only the public Agent interface.
- `app/agents/assessment.py` — retain `AgentAssessment`; add typed outcome models, then remove policy construction.
- `app/llm/adapter.py` — satisfy the internal provider port and return `ProviderResult`.
- `app/llm/__init__.py` — retain production adapter exports after method migration.
- `app/common/schemas.py` — remove Agent-only `EnrichmentOutput` and unused `EnrichmentTelemetry`.
- `app/api/events.py` — schedule `AssessmentHandoff` through FastAPI dependencies.
- `app/main.py` — expose `create_app()` and compose intake/handoff once.
- `app/services/enrichment_eval.py` — consume typed records instead of parsing JSON.
- `scripts/run_enrichment.py` — use `create_assessment_runner()` and `AssessmentOutcome`.
- `scripts/run_mock_enrichment.py` — use the same deep interface.
- `tests/unit/test_llm_adapter.py` — assert strict two-field provider draft and typed provider result.
- `tests/unit/test_enrichment_evaluation.py` — create/load typed records.
- `tests/integration/test_enrichment_pipeline.py` — test persisted candidate through `AssessmentRunner`.
- `tests/integration/test_enrichment_runtime_api.py` — use injected intake/handoff and assert observable failures.
- `tests/unit/test_http_publisher.py` — retain global `app` compatibility through `create_app()`.
- `requirements.txt` — declare Coverage.py used by the acceptance gate.
- `docs/system-architecture.md` — document the deep Agent flow and best-effort guarantee.
- `docs/project-changelog.md` — record the four completed architecture slices.

### Delete after caller migration

- `app/agents/graph.py`
- `app/agents/state.py`
- `app/agents/fallback.py`
- `app/services/enrichment.py`
- `app/services/assessment_record.py`
- `tests/unit/test_enrichment_agent.py`
- `tests/unit/test_enrichment_service.py`
- `tests/unit/test_agent_assessment.py`

---

## Slice 1 — Deep Assessment Execution

### Task 1: Add the Deep Runner Beside the Legacy Path

**Files:**
- Create: `app/agents/runtime.py`
- Create: `app/agents/_workflow.py`
- Create: `tests/unit/test_assessment_runtime.py`
- Modify: `app/agents/assessment.py:46-96`
- Modify: `app/agents/__init__.py:1-5`
- Reuse temporarily: `app/agents/fallback.py`, `app/services/assessment_record.py`

**Interfaces:**
- Consumes: `EventCandidate`, current `LLMAdapter`, current `EnrichmentOutput`, and current `AssessmentRecordStore`.
- Produces: `AssessmentTelemetry`, `AssessmentOutcome`, `AssessmentRunner.assess(EventCandidate)`, and `create_assessment_runner()`.

- [ ] **Step 1: Record the focused green baseline before changing behavior**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_enrichment_agent.py tests\unit\test_agent_assessment.py tests\unit\test_enrichment_service.py tests\unit\test_enrichment_evaluation.py tests\unit\test_llm_adapter.py tests\integration\test_enrichment_pipeline.py tests\integration\test_enrichment_runtime_api.py -q
```

Expected: `52 passed` with no failures.

- [ ] **Step 2: Write failing runner tests**

Create `tests/unit/test_assessment_runtime.py` with a candidate factory and the first public-interface tests:

```python
import copy
import json

import pytest

from app.agents import AssessmentRunner
from app.common.schemas import EventCandidate
from tests.unit.test_llm_adapter import _make_adapter


def _candidate(event_type: str = "ZONE_INTRUSION") -> EventCandidate:
    return EventCandidate(
        candidateId=f"candidate-{event_type}",
        eventType=event_type,
        cameraId="cam_01",
        zoneId="restricted_gate",
        sourceType="SIMULATED",
        detectedAt="2026-08-10T01:00:00Z",
        firstSeenAt="2026-08-10T00:59:58Z",
        lastSeenAt="2026-08-10T01:00:00Z",
        confidence=0.88,
        trackCount=1,
        observations={"personCount": 1, "dwellSeconds": 2.0, "insideZone": True},
    )


def _provider_response(severity: str = "HIGH") -> str:
    return json.dumps(
        {
            "recommendedSeverity": severity,
            "rationale": "controlled provider rationale",
            "summary": "legacy field removed in Slice 2",
            "actionChecklist": [],
        }
    )


@pytest.mark.asyncio
async def test_runner_returns_typed_completed_outcome(tmp_path):
    runner = AssessmentRunner(
        output_dir=str(tmp_path),
        llm_adapter=_make_adapter(responses=[_provider_response()]),
    )

    outcome = await runner.assess(_candidate())

    assert outcome.status == "completed"
    assert outcome.assessment.severity == "high"
    assert outcome.telemetry.provider_output_valid is True
    assert outcome.telemetry.fallback_used is False
    assert outcome.persist_error is None
    assert (tmp_path / "enrichment_candidate-ZONE_INTRUSION.json").exists()


@pytest.mark.asyncio
async def test_runner_returns_typed_fallback_without_provider(tmp_path):
    runner = AssessmentRunner(
        output_dir=str(tmp_path),
        llm_adapter=_make_adapter(available=False),
    )

    outcome = await runner.assess(_candidate())

    assert outcome.status == "fallback"
    assert outcome.assessment.model_name == "deterministic-fallback"
    assert outcome.telemetry.provider_output_valid is False
    assert outcome.telemetry.fallback_used is True


@pytest.mark.asyncio
async def test_runner_falls_back_for_malformed_provider_output(tmp_path):
    runner = AssessmentRunner(
        output_dir=str(tmp_path),
        llm_adapter=_make_adapter(responses=["not json"]),
    )

    outcome = await runner.assess(_candidate())

    assert outcome.status == "fallback"
    assert outcome.telemetry.provider_output_valid is False
    assert outcome.telemetry.provider_error is not None


@pytest.mark.asyncio
async def test_runner_never_mutates_candidate_and_reuses_instance(tmp_path):
    runner = AssessmentRunner(
        output_dir=str(tmp_path),
        llm_adapter=_make_adapter(responses=[_provider_response(), _provider_response("WARNING")]),
    )
    candidate = _candidate()
    snapshot = copy.deepcopy(candidate.model_dump(mode="json"))

    first = await runner.assess(candidate)
    second = await runner.assess(candidate.model_copy(update={"candidateId": "candidate-second"}))

    assert candidate.model_dump(mode="json") == snapshot
    assert first.assessment.severity == "high"
    assert second.assessment.severity == "medium"
```

- [ ] **Step 3: Run the new tests and verify the missing interface**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_assessment_runtime.py -q
```

Expected: collection fails because `AssessmentRunner` is not exported.

- [ ] **Step 4: Add typed outcome models**

Append these definitions to `app/agents/assessment.py`, reusing its existing `Literal` import:

```python
AssessmentStatus = Literal["completed", "fallback"]


class AssessmentTelemetry(BaseModel):
    provider_output_valid: bool
    fallback_used: bool
    latency_ms: float
    model_name: str
    provider_error: str | None = None


class AssessmentOutcome(BaseModel):
    assessment: AgentAssessment
    status: AssessmentStatus
    telemetry: AssessmentTelemetry
    persist_error: str | None = None
```

Keep the current `AgentAssessment` and `build_assessment()` during Slice 1.

- [ ] **Step 5: Move the current graph implementation behind a private name**

Create `app/agents/_workflow.py` by moving the current graph/state behavior into one private file. Define `WorkflowState` in the same file and rename the builder:

```python
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.fallback import build_fallback_output
from app.common.schemas import EnrichmentOutput
from app.llm.adapter import LLMAdapter


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
```

Add the current metadata-only prompt implementation above the builder:

```python
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
```

- [ ] **Step 6: Implement `AssessmentRunner` and compile the workflow in its constructor**

Create `app/agents/runtime.py` with this ownership shape:

```python
from pathlib import Path

from app.agents._workflow import AssessmentWorkflow
from app.agents.assessment import AssessmentOutcome, AssessmentTelemetry, build_assessment
from app.common.schemas import EventCandidate
from app.llm.adapter import LLMAdapter
from app.services.assessment_record import AssessmentRecordStore, ProviderOutcome


class AssessmentRunner:
    def __init__(
        self,
        output_dir: str = "artifacts/backend_events",
        llm_adapter: LLMAdapter | None = None,
        enabled: bool = True,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.record_store = AssessmentRecordStore(str(self.output_dir))
        adapter = llm_adapter
        if adapter is None and enabled:
            from app.llm.adapter import create_llm_adapter

            adapter = create_llm_adapter()
        self._workflow = AssessmentWorkflow(adapter)

    async def assess(self, candidate: EventCandidate) -> AssessmentOutcome:
        state = await self._workflow.run(candidate.model_dump(mode="json"))
        fallback_used = bool(state.get("fallback_used"))
        raw_telemetry = state.get("telemetry") or {}
        provider_model = str(raw_telemetry.get("model", ""))
        telemetry = AssessmentTelemetry(
            provider_output_valid=bool(raw_telemetry.get("output_valid", False)),
            fallback_used=fallback_used,
            latency_ms=float(raw_telemetry.get("latency_ms", 0.0)),
            model_name=provider_model,
            provider_error=state.get("error"),
        )
        event_type = candidate.eventType.value
        assessment = build_assessment(
            incident_id=candidate.candidateId,
            event_type=event_type,
            enrichment=state["output"],
            model="deterministic-fallback" if fallback_used else provider_model,
            confidence=candidate.confidence,
        )
        persist_error = self.record_store.save(
            candidate_id=candidate.candidateId,
            event_type=event_type,
            assessment=assessment,
            provider=ProviderOutcome(
                output_valid=telemetry.provider_output_valid,
                fallback_used=telemetry.fallback_used,
                latency_ms=telemetry.latency_ms,
                model=telemetry.model_name,
                error=telemetry.provider_error,
            ),
        )
        return AssessmentOutcome(
            assessment=assessment,
            status="fallback" if fallback_used else "completed",
            telemetry=telemetry,
            persist_error=persist_error,
        )


def create_assessment_runner(
    output_dir: str = "artifacts/backend_events",
    llm_adapter: LLMAdapter | None = None,
    llm_enabled: bool | None = None,
) -> AssessmentRunner:
    from app.config import settings

    enabled = settings.llm_enabled if llm_enabled is None else llm_enabled
    return AssessmentRunner(output_dir=output_dir, llm_adapter=llm_adapter, enabled=enabled)
```

- [ ] **Step 7: Export the new interface without removing legacy exports yet**

Set `app/agents/__init__.py` to:

```python
"""Advisory EventCandidate assessment."""

from app.agents.assessment import AgentAssessment, AssessmentOutcome
from app.agents.runtime import AssessmentRunner, create_assessment_runner

__all__ = [
    "AgentAssessment",
    "AssessmentOutcome",
    "AssessmentRunner",
    "create_assessment_runner",
]
```

- [ ] **Step 8: Run the new runner tests and the existing focused tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_assessment_runtime.py tests\unit\test_enrichment_service.py tests\unit\test_llm_adapter.py -q
```

Expected: all selected tests pass; no-provider fallback reports `provider_output_valid=False`.

- [ ] **Step 9: Commit Slice 1 interface introduction**

```powershell
git add app/agents/__init__.py app/agents/assessment.py app/agents/_workflow.py app/agents/runtime.py tests/unit/test_assessment_runtime.py
git commit -m "refactor(agent): introduce deep assessment runner"
```

### Task 2: Migrate Callers and Retire the Public Graph Interface

**Files:**
- Modify: `app/api/events.py:5-25`
- Modify: `scripts/run_enrichment.py:27-100`
- Modify: `scripts/run_mock_enrichment.py:28-56`
- Modify: `tests/unit/test_assessment_runtime.py`
- Modify: `tests/integration/test_enrichment_pipeline.py:7-96`
- Modify: `tests/integration/test_enrichment_runtime_api.py:18-140`
- Delete: `app/agents/graph.py`
- Delete: `app/agents/state.py`
- Delete: `app/services/enrichment.py`
- Delete: `tests/unit/test_enrichment_agent.py`
- Delete: `tests/unit/test_enrichment_service.py`

**Interfaces:**
- Consumes: `AssessmentRunner.assess()` and `create_assessment_runner()` from Task 1.
- Produces: no caller outside `app/agents/_workflow.py` knows `.ainvoke()` or workflow state keys.

- [ ] **Step 1: Add migration assertions to the integration pipeline test**

Replace direct graph construction in `tests/integration/test_enrichment_pipeline.py` with the deep interface:

```python
from app.agents import AssessmentRunner


def _persisted_candidate_payload() -> dict:
    return EventCandidate.model_validate(INTRUSION_EVENT).model_dump(mode="json")


@pytest.mark.asyncio
async def test_enrichment_from_persisted_json_with_llm(tmp_path):
    candidate = EventCandidate.model_validate(_persisted_candidate_payload())
    runner = AssessmentRunner(
        output_dir=str(tmp_path),
        llm_adapter=_make_adapter(responses=[VALID_LLM_RESPONSE]),
    )

    outcome = await runner.assess(candidate)

    assert outcome.status == "completed"
    assert outcome.assessment.severity == "high"
    assert outcome.telemetry.provider_output_valid is True


@pytest.mark.asyncio
async def test_enrichment_fallback_when_llm_outage(tmp_path):
    candidate = EventCandidate.model_validate(_persisted_candidate_payload())
    runner = AssessmentRunner(
        output_dir=str(tmp_path),
        llm_adapter=_make_adapter(available=False),
    )

    outcome = await runner.assess(candidate)

    assert outcome.status == "fallback"
    assert outcome.assessment.severity == "high"
    assert outcome.telemetry.provider_output_valid is False
```

Keep the existing candidate JSON round-trip test and extract its payload construction into `_persisted_candidate_payload()`.

- [ ] **Step 2: Run the integration test and observe legacy imports still present**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_enrichment_pipeline.py -q
rg -n "build_enrichment_graph|EnrichmentState|EnrichmentService|create_enrichment_service" app scripts tests
```

Expected: integration behavior passes; `rg` still reports route, scripts, and legacy tests that must migrate.

- [ ] **Step 3: Migrate route and scripts to the runner names**

In `app/api/events.py`, retain the current global shape until Slice 4 but change its type and call:

```python
from app.agents import create_assessment_runner

assessment_runner = create_assessment_runner(output_dir=BACKEND_EVENT_DIR)


async def _assess_in_background(candidate: EventCandidate) -> None:
    try:
        await assessment_runner.assess(candidate)
    except Exception:
        pass
```

This silent catch is intentionally short-lived and is removed by Task 6. Do not claim observability before that task.

In both scripts, replace `create_enrichment_service()` with `create_assessment_runner()` and `service.enrich(candidate)` with `runner.assess(candidate)`. Read status from `outcome.status` or `outcome.telemetry.fallback_used`.

- [ ] **Step 4: Move remaining runtime behavior tests into `test_assessment_runtime.py`**

Add this exact parameterized public-outcome test to `tests/unit/test_assessment_runtime.py`:

```python
@pytest.mark.parametrize(
    ("event_type", "provider_severity", "expected_severity"),
    [
        ("ZONE_INTRUSION", "HIGH", "high"),
        ("CROWD_THRESHOLD", "WARNING", "medium"),
        ("ABANDONED_OBJECT", "HIGH", "high"),
        ("SUSPECTED_FALL", "WARNING", "medium"),
        ("COVERAGE_DEGRADED", "INFO", "low"),
    ],
)
@pytest.mark.asyncio
async def test_runner_covers_all_event_types(
    tmp_path, event_type, provider_severity, expected_severity
):
    runner = AssessmentRunner(
        output_dir=str(tmp_path),
        llm_adapter=_make_adapter(responses=[_provider_response(provider_severity)]),
    )

    outcome = await runner.assess(_candidate(event_type))

    assert outcome.assessment.severity == expected_severity
```

The persistence, malformed-provider, repeated-runner, and immutable-input behaviors are already covered by Task 1. Do not preserve tests that inspect raw graph state keys.

- [ ] **Step 5: Replace the invalid slow fake with a response-contract test**

Delete `_SlowService` and the old `time`, `EnrichmentOutput`, `EnrichmentResult`, and `EnrichmentService` imports. Replace `test_ingest_responds_before_enrichment_runs` with the behavior it actually verified; Slice 4 adds a real scheduling-without-invocation test.

```python
def test_ingest_response_excludes_assessment(client):
    response = client.post("/internal/api/v1/event-candidates", json=_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ACCEPTED"
    assert body["candidateId"] == INTRUSION_EVENT["candidateId"]
    assert "enrichment" not in body
    assert "assessment" not in body
```

This prevents a passing test from depending on the swallowed `TypeError` caused by the old `EnrichmentResult(output=...)` construction.

Replace the temporary route fixture with runner-compatible globals until Slice 4 removes those globals:

```python
@pytest.fixture
def client(tmp_path):
    from app.agents import AssessmentRunner
    from app.api import events as events_api
    from app.services.intake import PersistedIntake

    original_runner = events_api.assessment_runner
    original_intake = events_api.intake
    events_api.assessment_runner = AssessmentRunner(
        output_dir=str(tmp_path / "enrichments"),
        llm_adapter=_make_adapter(available=False),
    )
    events_api.intake = PersistedIntake(storage_dir=str(tmp_path / "intake"))
    yield TestClient(app)
    events_api.assessment_runner = original_runner
    events_api.intake = original_intake
```

- [ ] **Step 6: Delete the shallow modules and legacy tests**

Delete the five files listed under this task only after their behavior has moved. Update all imports to `app.agents`.

- [ ] **Step 7: Verify no public graph/runtime caller remains**

Run:

```powershell
rg -n "build_enrichment_graph|EnrichmentState|EnrichmentService|create_enrichment_service" app scripts tests
rg -n "\.ainvoke\(" app scripts tests
```

Expected: the first command returns no matches; the second returns exactly one match inside `app/agents/_workflow.py`.

- [ ] **Step 8: Run Slice 1 regression tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_assessment_runtime.py tests\unit\test_llm_adapter.py tests\integration\test_enrichment_pipeline.py tests\integration\test_enrichment_runtime_api.py -q
```

Expected: all selected tests pass.

- [ ] **Step 9: Commit Slice 1 migration**

```powershell
git add app/agents app/api/events.py scripts/run_enrichment.py scripts/run_mock_enrichment.py tests/unit/test_assessment_runtime.py tests/integration/test_enrichment_pipeline.py tests/integration/test_enrichment_runtime_api.py
git add -u app/agents app/services tests/unit
git commit -m "refactor(agent): make LangGraph implementation private"
```

---

## Slice 2 — Authoritative Advisory Policy

### Task 3: Replace Provider Output and Scattered Policy with Typed Modules

**Files:**
- Create: `app/agents/provider.py`
- Create: `app/agents/policy.py`
- Create: `tests/unit/test_assessment_policy.py`
- Modify: `app/agents/assessment.py`
- Modify: `app/agents/_workflow.py`
- Modify: `app/agents/runtime.py`
- Modify: `app/llm/adapter.py`
- Modify: `tests/unit/test_llm_adapter.py`
- Modify: `tests/unit/test_assessment_runtime.py`
- Modify: `app/common/schemas.py:64-80`
- Delete: `app/agents/fallback.py`
- Delete: `tests/unit/test_agent_assessment.py`

**Interfaces:**
- Consumes: `EventCandidate`, `AgentAssessment`, and the runner interface from Slice 1.
- Produces: `ProviderDraft`, `ProviderResult`, `AssessmentProvider`, `fallback_draft()`, and `build_agent_assessment()`.

- [ ] **Step 1: Write failing table-driven policy tests**

Create `tests/unit/test_assessment_policy.py`:

```python
import pytest
from pydantic import ValidationError

from app.agents.policy import build_agent_assessment, fallback_draft
from app.agents.provider import ProviderDraft
from tests.unit.test_assessment_runtime import _candidate


@pytest.mark.parametrize(
    ("provider_severity", "expected_severity", "expected_action"),
    [
        ("INFO", "low", "log_only"),
        ("WARNING", "medium", "notify_guard"),
        ("HIGH", "high", "request_guard_verification"),
        ("CRITICAL", "critical", "request_manager_review"),
    ],
)
def test_policy_maps_severity_and_action(
    provider_severity, expected_severity, expected_action
):
    assessment = build_agent_assessment(
        candidate=_candidate(),
        draft=ProviderDraft(
            recommendedSeverity=provider_severity,
            rationale="fact-based rationale",
        ),
        model_name="test-model",
        prompt_version="assessment-v2",
        created_at="2026-08-10T02:00:04Z",
        assessment_id="assess-fixed",
    )

    assert assessment.severity == expected_severity
    assert assessment.recommended_action == expected_action
    assert assessment.requires_human_approval is False
    assert assessment.confidence == 0.88


def test_abandoned_object_is_capped_at_high():
    assessment = build_agent_assessment(
        candidate=_candidate("ABANDONED_OBJECT"),
        draft=ProviderDraft(recommendedSeverity="CRITICAL", rationale="r"),
        model_name="test-model",
        prompt_version="assessment-v2",
    )

    assert assessment.severity == "high"
    assert assessment.recommended_action == "request_guard_verification"


def test_assessment_contract_keeps_exact_spec_fields():
    assessment = build_agent_assessment(
        candidate=_candidate(),
        draft=ProviderDraft(recommendedSeverity="HIGH", rationale="r"),
        model_name="test-model",
        prompt_version="assessment-v2",
        created_at="2026-08-10T02:00:04Z",
        assessment_id="assess-fixed",
    )

    assert set(assessment.model_dump()) == {
        "schema_version",
        "assessment_id",
        "incident_id",
        "event_type",
        "severity",
        "confidence",
        "reason",
        "recommended_action",
        "requires_human_approval",
        "model_name",
        "model_version",
        "prompt_version",
        "created_at",
    }
    assert assessment.recommended_action not in {"request_alarm", "request_gate_lock"}


@pytest.mark.parametrize(
    ("event_type", "expected"),
    [
        ("ZONE_INTRUSION", "HIGH"),
        ("CROWD_THRESHOLD", "WARNING"),
        ("ABANDONED_OBJECT", "HIGH"),
        ("SUSPECTED_FALL", "WARNING"),
        ("COVERAGE_DEGRADED", "INFO"),
    ],
)
def test_fallback_severity_is_fixed_by_event_type(event_type, expected):
    draft = fallback_draft(_candidate(event_type), reason="llm_unavailable")
    assert draft.recommended_severity == expected
    assert event_type in draft.rationale


def test_provider_draft_rejects_removed_fields():
    with pytest.raises(ValidationError):
        ProviderDraft.model_validate(
            {
                "recommendedSeverity": "HIGH",
                "rationale": "r",
                "summary": "removed",
                "actionChecklist": [],
            }
        )
```

- [ ] **Step 2: Run policy tests and verify imports fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_assessment_policy.py -q
```

Expected: collection fails because `provider.py` and `policy.py` do not exist.

- [ ] **Step 3: Implement the strict provider port**

Create `app/agents/provider.py`:

```python
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


ProviderSeverity = Literal["INFO", "WARNING", "HIGH", "CRITICAL"]


class ProviderDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    recommended_severity: ProviderSeverity = Field(alias="recommendedSeverity")
    rationale: str = Field(min_length=1)


class ProviderResult(BaseModel):
    draft: ProviderDraft | None
    latency_ms: float
    model_name: str
    error: str | None = None


class AssessmentProvider(Protocol):
    async def assess(self, *, prompt: str, system_prompt: str) -> ProviderResult:
        raise NotImplementedError
```

- [ ] **Step 4: Implement authoritative policy and deterministic fallback**

Create `app/agents/policy.py` with one copy of all mappings:

```python
import uuid
from datetime import UTC, datetime

from app.agents.assessment import AgentAssessment
from app.agents.provider import ProviderDraft
from app.common.schemas import EventCandidate


SEVERITY_MAP = {
    "INFO": "low",
    "WARNING": "medium",
    "HIGH": "high",
    "CRITICAL": "critical",
}
ACTION_MAP = {
    "low": "log_only",
    "medium": "notify_guard",
    "high": "request_guard_verification",
    "critical": "request_manager_review",
}
FALLBACK_SEVERITY = {
    "ZONE_INTRUSION": "HIGH",
    "CROWD_THRESHOLD": "WARNING",
    "ABANDONED_OBJECT": "HIGH",
    "SUSPECTED_FALL": "WARNING",
    "COVERAGE_DEGRADED": "INFO",
}


def fallback_draft(candidate: EventCandidate, *, reason: str) -> ProviderDraft:
    event_type = candidate.eventType.value
    return ProviderDraft(
        recommendedSeverity=FALLBACK_SEVERITY[event_type],
        rationale=f"Fallback rule-based cho {event_type}: {reason}.",
    )


def build_agent_assessment(
    *,
    candidate: EventCandidate,
    draft: ProviderDraft,
    model_name: str,
    prompt_version: str,
    created_at: str | None = None,
    assessment_id: str | None = None,
) -> AgentAssessment:
    severity = SEVERITY_MAP[draft.recommended_severity]
    if candidate.eventType.value == "ABANDONED_OBJECT" and severity == "critical":
        severity = "high"
    return AgentAssessment(
        assessment_id=assessment_id or f"assess-{uuid.uuid4()}",
        incident_id=candidate.candidateId,
        event_type=candidate.eventType.value,
        severity=severity,
        confidence=candidate.confidence,
        reason=draft.rationale,
        recommended_action=ACTION_MAP[severity],
        requires_human_approval=False,
        model_name=model_name,
        prompt_version=prompt_version,
        created_at=created_at or datetime.now(UTC).isoformat(),
    )
```

- [ ] **Step 5: Make `LLMAdapter` return `ProviderResult`**

In `app/llm/adapter.py`, replace `EnrichmentOutput` parsing and telemetry dictionaries with:

```python
from app.agents.provider import ProviderDraft, ProviderResult


def _strip_json_fence(raw: str) -> str:
    text = raw.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    text = "\n".join(lines[1:-1]).strip()
    if text.lower().startswith("json"):
        text = text[4:].strip()
    return text


async def assess(self, *, prompt: str, system_prompt: str) -> ProviderResult:
    return await asyncio.to_thread(self._assess, prompt, system_prompt)


def _assess(self, prompt: str, system_prompt: str) -> ProviderResult:
    started = time.perf_counter()
    if not self.available:
        return ProviderResult(
            draft=None,
            latency_ms=0.0,
            model_name=self.model,
            error="adapter_unavailable",
        )
    try:
        response = self._llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
        )
        elapsed = round((time.perf_counter() - started) * 1000.0, 2)
        raw = response.content
        if not isinstance(raw, str) or not raw.strip():
            return ProviderResult(
                draft=None,
                latency_ms=elapsed,
                model_name=self.model,
                error="empty_response",
            )
        return ProviderResult(
            draft=self._parse_draft(raw),
            latency_ms=elapsed,
            model_name=self.model,
            error=None,
        )
    except Exception as exc:
        elapsed = round((time.perf_counter() - started) * 1000.0, 2)
        return ProviderResult(
            draft=None,
            latency_ms=elapsed,
            model_name=self.model,
            error=type(exc).__name__,
        )


def _parse_draft(self, raw: str) -> ProviderDraft:
    text = _strip_json_fence(raw)
    parsed = json.loads(text)
    return ProviderDraft.model_validate(parsed)
```

Keep exception handling around JSON/Pydantic parsing in `_assess()` so invalid drafts return `ProviderResult` with `draft=None` and `error=type(exc).__name__`. Retain `asyncio.to_thread` and the existing no-tools construction.

- [ ] **Step 6: Rewrite the private workflow around typed candidate/provider state**

Replace dictionary provider output in `app/agents/_workflow.py` with:

```python
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
```

Use only `recommendedSeverity` and `rationale` in `SYSTEM_PROMPT`; set prompt version to `assessment-v2`. `_build_prompt()` accepts `EventCandidate` and reads typed attributes. Do not include `candidate.artifact.uri`.

- [ ] **Step 7: Make the runner apply policy and build typed telemetry**

In `AssessmentRunner.assess()`, invoke the private workflow with the typed candidate and build the assessment as follows:

```python
state = await self._workflow.run(candidate)
provider_result = state["provider_result"]
fallback_used = bool(state["fallback_used"])
assessment = build_agent_assessment(
    candidate=candidate,
    draft=state["draft"],
    model_name="deterministic-fallback" if fallback_used else provider_result.model_name,
    prompt_version="assessment-v2",
)
telemetry = AssessmentTelemetry(
    provider_output_valid=provider_result.draft is not None,
    fallback_used=fallback_used,
    latency_ms=provider_result.latency_ms,
    model_name=provider_result.model_name if self._provider_enabled else "",
    provider_error=provider_result.error,
)
```

Store `_provider_enabled = provider is not None` in the constructor so disabled execution records an empty telemetry model name.

Use this constructor fragment when replacing the Slice 1 adapter setup:

```python
provider = llm_adapter
if provider is None and enabled:
    from app.llm.adapter import create_llm_adapter

    provider = create_llm_adapter()
self._provider_enabled = provider is not None
self._workflow = AssessmentWorkflow(provider)
```

- [ ] **Step 8: Update adapter and runner tests for the strict draft**

Change all fake provider JSON in `tests/unit/test_llm_adapter.py` and `tests/unit/test_assessment_runtime.py` to exactly two fields. Assert typed results:

```python
result = await adapter.assess(prompt="p", system_prompt="s")
assert result.draft is not None
assert result.draft.recommended_severity == "HIGH"
assert result.error is None
```

Mark tests containing this assertion with `@pytest.mark.asyncio` and declare them `async def`.

Update the test import to `from app.agents import AssessmentRunner, create_assessment_runner`, then add disabled-provider and prompt tests:

```python
@pytest.mark.asyncio
async def test_disabled_provider_has_empty_telemetry_model(tmp_path):
    runner = create_assessment_runner(
        output_dir=str(tmp_path),
        llm_enabled=False,
    )

    outcome = await runner.assess(_candidate())

    assert outcome.status == "fallback"
    assert outcome.assessment.model_name == "deterministic-fallback"
    assert outcome.telemetry.model_name == ""
    assert outcome.telemetry.provider_output_valid is False


@pytest.mark.asyncio
async def test_runner_prompt_omits_non_authoritative_fields(tmp_path):
    adapter = _make_adapter(responses=[_provider_response()])
    runner = AssessmentRunner(output_dir=str(tmp_path), llm_adapter=adapter)

    await runner.assess(_candidate())

    sent = "\n".join(str(message.content) for message in adapter._llm.calls[0])
    assert "summary" not in sent
    assert "actionChecklist" not in sent
    assert "artifact" not in sent
```

- [ ] **Step 9: Remove obsolete Agent output and policy modules**

Remove `EnrichmentOutput` and `EnrichmentTelemetry` from `app/common/schemas.py`. Delete `app/agents/fallback.py`. Reduce `app/agents/assessment.py` to domain types only and delete its mapping constants and `build_assessment()`.

Delete `tests/unit/test_agent_assessment.py` after its mapping and JSON-shape assertions are covered by `test_assessment_policy.py` and `test_assessment_runtime.py`.

- [ ] **Step 10: Run Slice 2 tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_assessment_policy.py tests\unit\test_assessment_runtime.py tests\unit\test_llm_adapter.py tests\integration\test_enrichment_pipeline.py -q
```

Expected: all selected tests pass.

- [ ] **Step 11: Verify policy and removed fields have one owner**

Run:

```powershell
rg -n "SEVERITY_MAP|ACTION_MAP|FALLBACK_SEVERITY" app tests
rg -n "summary|actionChecklist|EnrichmentOutput|EnrichmentTelemetry" app scripts tests
```

Expected: mappings appear only in `app/agents/policy.py` plus direct policy test expectations; removed output names have no matches.

- [ ] **Step 12: Commit Slice 2**

```powershell
git add app/agents app/llm app/common/schemas.py tests/unit/test_assessment_policy.py tests/unit/test_assessment_runtime.py tests/unit/test_llm_adapter.py tests/integration/test_enrichment_pipeline.py
git add -u app/agents tests/unit
git commit -m "refactor(agent): centralize authoritative advisory policy"
```

---

## Slice 3 — Deep Assessment Record

### Task 4: Introduce Typed Legacy-compatible Record Ownership

**Files:**
- Create: `app/agents/record.py`
- Create: `tests/unit/test_assessment_record.py`
- Modify: `app/agents/runtime.py`
- Modify: `tests/unit/test_assessment_runtime.py`
- Delete: `app/services/assessment_record.py`

**Interfaces:**
- Consumes: `AssessmentOutcome`, `AssessmentTelemetry`, `AgentAssessment`, and `EventCandidate`.
- Produces: `AssessmentRecord`, `AssessmentRecordStore.save()`, `.load()`, and `.iter_records()`.

- [ ] **Step 1: Write failing record round-trip and legacy compatibility tests**

Create `tests/unit/test_assessment_record.py`:

```python
import json

from app.agents.assessment import AssessmentOutcome, AssessmentTelemetry
from app.agents.policy import build_agent_assessment
from app.agents.provider import ProviderDraft
from app.agents.record import AssessmentRecord, AssessmentRecordStore
from tests.unit.test_assessment_runtime import _candidate


def _outcome(candidate=None) -> AssessmentOutcome:
    candidate = candidate or _candidate()
    assessment = build_agent_assessment(
        candidate=candidate,
        draft=ProviderDraft(recommendedSeverity="HIGH", rationale="r"),
        model_name="test-model",
        prompt_version="assessment-v2",
        created_at="2026-08-10T02:00:04Z",
        assessment_id="assess-fixed",
    )
    return AssessmentOutcome(
        assessment=assessment,
        status="completed",
        telemetry=AssessmentTelemetry(
            provider_output_valid=True,
            fallback_used=False,
            latency_ms=12.5,
            model_name="test-model",
            provider_error=None,
        ),
    )


def test_record_store_round_trip_preserves_current_json_shape(tmp_path):
    candidate = _candidate()
    record = AssessmentRecord.from_outcome(candidate=candidate, outcome=_outcome())
    store = AssessmentRecordStore(tmp_path)

    assert store.save(record) is None
    loaded = store.load(candidate.candidateId)

    assert loaded == record
    payload = json.loads(
        (tmp_path / f"enrichment_{candidate.candidateId}.json").read_text(encoding="utf-8")
    )
    assert set(payload) == {"candidateId", "eventType", "assessment", "telemetry"}
    assert set(payload["telemetry"]) == {
        "latencyMs",
        "model",
        "fallbackUsed",
        "outputValid",
        "error",
        "persistError",
    }


def test_record_store_reads_current_legacy_fixture(tmp_path):
    fixture = {
        "candidateId": "legacy-1",
        "eventType": "ZONE_INTRUSION",
        "assessment": {
            **_outcome().assessment.model_dump(mode="json"),
            "incident_id": "legacy-1",
            "prompt_version": "assessment-v1",
        },
        "telemetry": {
            "latencyMs": 20.0,
            "model": "legacy-model",
            "fallbackUsed": False,
            "outputValid": True,
            "error": None,
            "persistError": None,
        },
    }
    (tmp_path / "enrichment_legacy-1.json").write_text(
        json.dumps(fixture), encoding="utf-8"
    )

    loaded = AssessmentRecordStore(tmp_path).load("legacy-1")

    assert loaded is not None
    assert loaded.assessment.prompt_version == "assessment-v1"
    assert loaded.telemetry.provider_output_valid is True


def test_iter_records_skips_malformed_files(tmp_path, caplog):
    (tmp_path / "enrichment_bad.json").write_text("not json", encoding="utf-8")

    records = list(AssessmentRecordStore(tmp_path).iter_records())

    assert records == []
    assert "assessment_record_invalid" in caplog.text
```

- [ ] **Step 2: Run record tests and verify the module is missing**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_assessment_record.py -q
```

Expected: collection fails because `app.agents.record` does not exist.

- [ ] **Step 3: Implement typed record models and aliases**

Create `app/agents/record.py` with typed camelCase serialization:

```python
import json
import logging
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.agents.assessment import AgentAssessment, AssessmentOutcome
from app.common.schemas import EventCandidate

logger = logging.getLogger(__name__)
ENRICHMENT_PREFIX = "enrichment_"
ENRICHMENT_SUFFIX = ".json"


class RecordTelemetry(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    latency_ms: float = Field(alias="latencyMs")
    model_name: str = Field(alias="model")
    fallback_used: bool = Field(alias="fallbackUsed")
    provider_output_valid: bool = Field(alias="outputValid")
    provider_error: str | None = Field(default=None, alias="error")
    persist_error: str | None = Field(default=None, alias="persistError")


class AssessmentRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    candidate_id: str = Field(alias="candidateId")
    event_type: str = Field(alias="eventType")
    assessment: AgentAssessment
    telemetry: RecordTelemetry

    @classmethod
    def from_outcome(
        cls, *, candidate: EventCandidate, outcome: AssessmentOutcome
    ) -> "AssessmentRecord":
        return cls(
            candidateId=candidate.candidateId,
            eventType=candidate.eventType.value,
            assessment=outcome.assessment,
            telemetry=RecordTelemetry(
                latencyMs=outcome.telemetry.latency_ms,
                model=outcome.telemetry.model_name,
                fallbackUsed=outcome.telemetry.fallback_used,
                outputValid=outcome.telemetry.provider_output_valid,
                error=outcome.telemetry.provider_error,
                persistError=None,
            ),
        )
```

- [ ] **Step 4: Implement one filesystem adapter for save/load/iteration**

Add to `app/agents/record.py`:

```python
class AssessmentRecordStore:
    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def save(self, record: AssessmentRecord) -> str | None:
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            target = self.output_dir / (
                f"{ENRICHMENT_PREFIX}{record.candidate_id}{ENRICHMENT_SUFFIX}"
            )
            target.write_text(
                json.dumps(
                    record.model_dump(mode="json", by_alias=True),
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            return None
        except OSError as exc:
            return f"enrichment_persist_failed:{type(exc).__name__}"

    def load(self, candidate_id: str) -> AssessmentRecord | None:
        target = self.output_dir / (
            f"{ENRICHMENT_PREFIX}{candidate_id}{ENRICHMENT_SUFFIX}"
        )
        if not target.exists():
            return None
        return self._read(target)

    def iter_records(self) -> Iterator[AssessmentRecord]:
        if not self.output_dir.exists():
            return
        for path in sorted(
            self.output_dir.glob(f"{ENRICHMENT_PREFIX}*{ENRICHMENT_SUFFIX}")
        ):
            record = self._read(path)
            if record is not None:
                yield record

    def _read(self, path: Path) -> AssessmentRecord | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return AssessmentRecord.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            logger.warning(
                "assessment_record_invalid",
                extra={"record_path": str(path), "exception_class": type(exc).__name__},
            )
            return None
```

- [ ] **Step 5: Migrate the runner to typed record ownership**

Replace the legacy store import and save call in `app/agents/runtime.py`:

```python
from app.agents.record import AssessmentRecord, AssessmentRecordStore


outcome = AssessmentOutcome(
    assessment=assessment,
    status="fallback" if fallback_used else "completed",
    telemetry=telemetry,
)
persist_error = self.record_store.save(
    AssessmentRecord.from_outcome(candidate=candidate, outcome=outcome)
)
return outcome.model_copy(update={"persist_error": persist_error})
```

Delete all `ProviderOutcome` construction.

- [ ] **Step 6: Add the public persistence-failure behavior test**

Append to `tests/unit/test_assessment_runtime.py`:

```python
@pytest.mark.asyncio
async def test_record_failure_is_separate_from_provider_outcome(tmp_path):
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("blocks mkdir", encoding="utf-8")
    runner = AssessmentRunner(
        output_dir=str(blocked),
        llm_adapter=_make_adapter(responses=[_provider_response()]),
    )

    outcome = await runner.assess(_candidate())

    assert outcome.status == "completed"
    assert outcome.telemetry.provider_output_valid is True
    assert outcome.telemetry.fallback_used is False
    assert outcome.persist_error == "enrichment_persist_failed:FileExistsError"
```

- [ ] **Step 7: Delete the legacy record module and run Slice 3 record tests**

Delete `app/services/assessment_record.py`, then run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_assessment_record.py tests\unit\test_assessment_runtime.py -q
```

Expected: all selected tests pass.

- [ ] **Step 8: Commit typed record ownership**

```powershell
git add app/agents/record.py app/agents/runtime.py tests/unit/test_assessment_record.py tests/unit/test_assessment_runtime.py
git add -u app/services
git commit -m "refactor(agent): deepen assessment record ownership"
```

### Task 5: Route Evaluation Through the Typed Record Module

**Files:**
- Modify: `app/services/enrichment_eval.py:1-70`
- Modify: `tests/unit/test_enrichment_evaluation.py:1-100`
- Modify: `scripts/run_mock_enrichment.py:44-57`

**Interfaces:**
- Consumes: `AssessmentRecordStore.iter_records()` from Task 4.
- Produces: unchanged `EvaluationReporter.report()` summary keys without independent JSON parsing.

- [ ] **Step 1: Rewrite the reporter loading test to use the record module**

Replace direct JSON fixture creation in `tests/unit/test_enrichment_evaluation.py` with typed records:

```python
from app.agents.record import AssessmentRecord, AssessmentRecordStore
from tests.unit.test_assessment_record import _outcome
from tests.unit.test_assessment_runtime import _candidate


def test_reporter_loads_records_through_record_store(tmp_path):
    store = AssessmentRecordStore(tmp_path)
    first = _candidate().model_copy(update={"candidateId": "cand-1"})
    second = _candidate().model_copy(update={"candidateId": "cand-2"})
    assert store.save(AssessmentRecord.from_outcome(candidate=first, outcome=_outcome(first))) is None
    assert store.save(AssessmentRecord.from_outcome(candidate=second, outcome=_outcome(second))) is None

    summary = EvaluationReporter(str(tmp_path)).report()

    assert summary["total"] == 2
    assert summary["schema_valid_rate"] == 1.0
    assert summary["severity_counts"] == {"high": 2}
```

Keep pure `summarize_records()` percentile/rate tests unchanged except for lowercase assessment severity.

- [ ] **Step 2: Run the test before changing the reporter**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_enrichment_evaluation.py::test_reporter_loads_records_through_record_store -q
```

Expected: failure because `EvaluationReporter` still parses files independently or the renamed test is not yet supported.

- [ ] **Step 3: Remove record parsing from `EvaluationReporter`**

Replace `Path.glob`, `json.loads`, prefix/suffix constants, and `_parse_file()` with:

```python
from app.agents.record import AssessmentRecordStore


@dataclass
class EvaluationReporter:
    enrichment_dir: str = "artifacts/backend_events"

    def load_records(self) -> list[EvaluationRecord]:
        store = AssessmentRecordStore(self.enrichment_dir)
        return [
            EvaluationRecord(
                candidate_id=record.candidate_id,
                event_type=record.event_type,
                fallback_used=record.telemetry.fallback_used,
                output_valid=record.telemetry.provider_output_valid,
                latency_ms=record.telemetry.latency_ms,
                model=record.telemetry.model_name,
                severity=record.assessment.severity,
            )
            for record in store.iter_records()
        ]

    def report(self) -> dict[str, Any]:
        return summarize_records(self.load_records())
```

- [ ] **Step 4: Verify malformed records are skipped by one implementation**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_assessment_record.py tests\unit\test_enrichment_evaluation.py -q
rg -n "json\.loads|ENRICHMENT_PREFIX|ENRICHMENT_SUFFIX|_parse_file" app/services/enrichment_eval.py
```

Expected: tests pass; `rg` returns no matches.

- [ ] **Step 5: Smoke the mock runner and evaluation projection without network**

Run with LLM disabled for the command:

```powershell
$smokeDir = Join-Path $env:TEMP ("p176-agent-smoke-" + [guid]::NewGuid().ToString("N"))
$env:LLM_ENABLED = 'false'
.\.venv\Scripts\python.exe scripts\run_mock_enrichment.py --output-dir $smokeDir
```

Expected: every candidate prints `fallback`; the final report has `schema_valid_rate: 0.0` and `fallback_rate: 1.0`.

- [ ] **Step 6: Commit evaluation migration**

```powershell
git add app/services/enrichment_eval.py tests/unit/test_enrichment_evaluation.py scripts/run_mock_enrichment.py
git commit -m "refactor(agent): evaluate typed assessment records"
```

---

## Slice 4 — Observable Candidate-to-assessment Handoff

### Task 6: Inject and Observe the Best-effort Handoff

**Files:**
- Create: `app/agents/handoff.py`
- Create: `tests/unit/test_assessment_handoff.py`
- Modify: `app/api/events.py:1-49`
- Modify: `app/main.py:1-22`
- Modify: `tests/integration/test_enrichment_runtime_api.py:1-140`
- Modify: `tests/unit/test_http_publisher.py:1-52`

**Interfaces:**
- Consumes: `AssessmentRunner.assess()` and `PersistedIntake`.
- Produces: `AssessmentHandoff.run()`, `create_app()`, `get_intake()`, and `get_assessment_handoff()`.

- [ ] **Step 1: Write failing handoff log tests**

Create `tests/unit/test_assessment_handoff.py`:

```python
import logging

import pytest

from app.agents.handoff import AssessmentHandoff
from tests.unit.test_assessment_record import _outcome
from tests.unit.test_assessment_runtime import _candidate


class _StubRunner:
    def __init__(self, *, outcome=None, error=None):
        self.outcome = outcome
        self.error = error
        self.calls = []

    async def assess(self, candidate):
        self.calls.append(candidate.candidateId)
        if self.error is not None:
            raise self.error
        return self.outcome


@pytest.mark.asyncio
async def test_handoff_logs_terminal_outcome(caplog):
    runner = _StubRunner(outcome=_outcome())
    handoff = AssessmentHandoff(runner)

    with caplog.at_level(logging.INFO):
        result = await handoff.run(_candidate())

    assert result is not None
    assert "agent_assessment_completed" in caplog.text
    assert runner.calls == ["candidate-ZONE_INTRUSION"]


@pytest.mark.asyncio
async def test_handoff_logs_unexpected_failure(caplog):
    runner = _StubRunner(error=RuntimeError("boom"))
    handoff = AssessmentHandoff(runner)

    with caplog.at_level(logging.ERROR):
        result = await handoff.run(_candidate())

    assert result is None
    assert "agent_assessment_failed" in caplog.text
    record = caplog.records[-1]
    assert record.candidate_id == "candidate-ZONE_INTRUSION"
    assert record.event_type == "ZONE_INTRUSION"
    assert record.assessment_status == "failed"
    assert record.exception_class == "RuntimeError"
```

- [ ] **Step 2: Run handoff tests and verify the module is missing**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_assessment_handoff.py -q
```

Expected: collection fails because `app.agents.handoff` does not exist.

- [ ] **Step 3: Implement observable outermost execution**

Create `app/agents/handoff.py`:

```python
import logging

from app.agents.assessment import AssessmentOutcome
from app.agents.runtime import AssessmentRunner
from app.common.schemas import EventCandidate

logger = logging.getLogger(__name__)


class AssessmentHandoff:
    def __init__(self, runner: AssessmentRunner) -> None:
        self.runner = runner

    async def run(self, candidate: EventCandidate) -> AssessmentOutcome | None:
        fields = {
            "candidate_id": candidate.candidateId,
            "event_type": candidate.eventType.value,
        }
        try:
            outcome = await self.runner.assess(candidate)
        except Exception as exc:
            logger.exception(
                "agent_assessment_failed",
                extra={
                    **fields,
                    "assessment_status": "failed",
                    "exception_class": type(exc).__name__,
                },
            )
            return None

        level = logging.ERROR if outcome.persist_error else logging.INFO
        logger.log(
            level,
            "agent_assessment_completed",
            extra={
                **fields,
                "assessment_status": outcome.status,
                "fallback_used": outcome.telemetry.fallback_used,
                "persist_error": outcome.persist_error,
            },
        )
        return outcome
```

The broad catch exists only here and always calls `logger.exception`.

- [ ] **Step 4: Write failing route scheduling tests without executing background work**

In `tests/integration/test_enrichment_runtime_api.py`, add a direct route test with real FastAPI `BackgroundTasks`:

```python
from fastapi import BackgroundTasks

from app.agents.handoff import AssessmentHandoff
from app.api.events import ingest_event_candidate
from app.common.schemas import EventCandidate
from app.services.intake import PersistedIntake
from tests.unit.test_assessment_record import _outcome


class _RecordingRunner:
    def __init__(self):
        self.calls = []

    async def assess(self, candidate):
        self.calls.append(candidate.candidateId)
        return _outcome(candidate)


def test_route_schedules_without_invoking_runner(tmp_path):
    runner = _RecordingRunner()
    handoff = AssessmentHandoff(runner)
    intake = PersistedIntake(storage_dir=str(tmp_path / "intake"))
    tasks = BackgroundTasks()

    response = ingest_event_candidate(
        candidate=EventCandidate.model_validate(_payload()),
        background_tasks=tasks,
        intake=intake,
        handoff=handoff,
        idempotency_key=None,
    )

    assert response["status"] == "ACCEPTED"
    assert len(tasks.tasks) == 1
    assert runner.calls == []
```

Add a duplicate variant that calls the route twice with fresh `BackgroundTasks` and asserts the second task list is empty.

- [ ] **Step 5: Replace route globals with FastAPI dependencies**

Refactor `app/api/events.py` to:

```python
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status

from app.agents.handoff import AssessmentHandoff
from app.common.schemas import EventCandidate
from app.services.intake import PersistedIntake

router = APIRouter(prefix="/internal/api/v1", tags=["Events Ingestion"])


def get_intake(request: Request) -> PersistedIntake:
    return request.app.state.intake


def get_assessment_handoff(request: Request) -> AssessmentHandoff:
    return request.app.state.assessment_handoff


@router.post("/event-candidates", status_code=status.HTTP_201_CREATED)
def ingest_event_candidate(
    candidate: EventCandidate,
    background_tasks: BackgroundTasks,
    intake: Annotated[PersistedIntake, Depends(get_intake)],
    handoff: Annotated[AssessmentHandoff, Depends(get_assessment_handoff)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    outcome = intake.accept(candidate, header_id=idempotency_key)
    if outcome.status == "ERROR":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=outcome.error or "Failed to persist event candidate",
        )
    if outcome.status == "ACCEPTED":
        canonical = intake.canonical_candidate(candidate, header_id=idempotency_key)
        background_tasks.add_task(handoff.run, canonical)
    return outcome.as_response()
```

- [ ] **Step 6: Add an application factory that composes dependencies once**

Refactor `app/main.py` while preserving `from app.main import app`:

```python
from fastapi import FastAPI

from app.agents import AssessmentRunner, create_assessment_runner
from app.agents.handoff import AssessmentHandoff
from app.api.debug import router as debug_router
from app.api.events import router as events_router
from app.api.health import router as health_router
from app.services.intake import PersistedIntake

BACKEND_EVENT_DIR = "artifacts/backend_events"


def create_app(
    *,
    intake: PersistedIntake | None = None,
    assessment_runner: AssessmentRunner | None = None,
) -> FastAPI:
    application = FastAPI(
        title="CV/VLM Security Event Detection System",
        description="Computer Vision CCTV Security Event Candidate Producer & Backend Ingestion",
        version="1.0.0",
    )
    resolved_intake = intake or PersistedIntake(storage_dir=BACKEND_EVENT_DIR)
    resolved_runner = assessment_runner or create_assessment_runner(
        output_dir=BACKEND_EVENT_DIR
    )
    application.state.intake = resolved_intake
    application.state.assessment_handoff = AssessmentHandoff(resolved_runner)
    application.include_router(health_router)
    application.include_router(debug_router)
    application.include_router(events_router)

    @application.get("/")
    def root():
        return {
            "system": "CV/VLM Security Event Detection System",
            "phase": "Phase 2 - Privacy Redaction Gate & Backend Integration",
            "status": "OPERATIONAL",
        }

    return application


app = create_app()
```

No provider call occurs during factory construction; only the private graph compiles.

- [ ] **Step 7: Rewrite route fixtures to inject dependencies**

In `tests/integration/test_enrichment_runtime_api.py`, replace global save/restore monkeypatches with:

```python
@pytest.fixture
def runner(tmp_path):
    return AssessmentRunner(
        output_dir=str(tmp_path / "enrichments"),
        llm_adapter=_make_adapter(available=False),
    )


@pytest.fixture
def client(tmp_path, runner):
    application = create_app(
        intake=PersistedIntake(storage_dir=str(tmp_path / "intake")),
        assessment_runner=runner,
    )
    return TestClient(application)
```

Use `create_app()` in tests that need custom runners. Keep `tests/unit/test_http_publisher.py` importing the global `app` to prove backward compatibility.

In `tests/unit/test_http_publisher.py`, keep one import assertion for the global application and run endpoint behavior through an injected offline application:

```python
from fastapi import FastAPI

from app.agents import AssessmentRunner
from app.main import app, create_app
from app.services.intake import PersistedIntake
from tests.unit.test_llm_adapter import _make_adapter


def test_global_app_import_remains_compatible():
    assert isinstance(app, FastAPI)


def _event_payload() -> dict:
    now_iso = utc_now_iso()
    candidate_id = f"test-cand-http-{uuid.uuid4()}"
    return {
        "candidateId": candidate_id,
        "sourceEngine": "CV",
        "cameraId": "cam_01",
        "zoneId": "restricted_gate",
        "sourceType": "SIMULATED",
        "eventType": "ZONE_INTRUSION",
        "eventDetected": True,
        "detectedAt": now_iso,
        "firstSeenAt": now_iso,
        "lastSeenAt": now_iso,
        "confidence": 0.95,
        "trackCount": 1,
        "trackIds": [10],
        "observations": {
            "personCount": 1,
            "dwellSeconds": 2.5,
            "insideZone": True,
        },
        "modelVersion": "yolo-v11n",
        "ruleVersion": "intrusion-rule-v1",
        "policyVersion": 1,
        "artifact": {
            "available": True,
            "contentType": "image/jpeg",
            "redactionStatus": "COMPLETE",
            "uri": f"/artifacts/evidence/{candidate_id}.jpg",
        },
    }


def test_fastapi_event_candidate_ingestion_and_idempotency(tmp_path):
    application = create_app(
        intake=PersistedIntake(storage_dir=str(tmp_path / "intake")),
        assessment_runner=AssessmentRunner(
            output_dir=str(tmp_path / "assessment"),
            llm_adapter=_make_adapter(available=False),
        ),
    )
    client = TestClient(application)
    payload = _event_payload()

    first = client.post(
        "/internal/api/v1/event-candidates",
        json=payload,
        headers={"Idempotency-Key": payload["candidateId"]},
    )
    second = client.post(
        "/internal/api/v1/event-candidates",
        json=payload,
        headers={"Idempotency-Key": payload["candidateId"]},
    )

    assert first.status_code == 201
    assert first.json()["status"] == "ACCEPTED"
    assert second.status_code == 201
    assert second.json()["status"] == "DUPLICATE_IGNORED"
```

- [ ] **Step 8: Run handoff and route tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_assessment_handoff.py tests\integration\test_enrichment_runtime_api.py tests\unit\test_http_publisher.py -q
```

Expected: accepted candidates schedule once, duplicates do not schedule, background defects are logged, and all endpoint responses remain compatible.

- [ ] **Step 9: Verify silent catches and mutable route globals are gone**

Run:

```powershell
rg -n "except Exception:\s*$|enrichment_service|assessment_runner\s*=|intake\s*=" app/api/events.py tests/integration/test_enrichment_runtime_api.py
rg -n "logger\.exception\(" app/agents/handoff.py
```

Expected: the first command finds only typed dependency parameters, not a silent catch or module runtime globals; the second finds the outermost failure log.

- [ ] **Step 10: Commit Slice 4**

```powershell
git add app/agents/handoff.py app/api/events.py app/main.py tests/unit/test_assessment_handoff.py tests/integration/test_enrichment_runtime_api.py tests/unit/test_http_publisher.py
git commit -m "refactor(agent): make background handoff observable"
```

---

## Final Acceptance

### Task 7: Remove Residue, Document Guarantees, and Run All Gates

**Files:**
- Modify: `requirements.txt`
- Modify: `docs/system-architecture.md`
- Modify: `docs/project-changelog.md`
- Modify only if residue remains: files reported by the searches below.

**Interfaces:**
- Consumes: all six completed task deliverables.
- Produces: reproducible lint/test/coverage evidence and documentation of the final deep Agent interface.

- [ ] **Step 1: Declare the coverage tool used by the gate**

Add under `# Dev tools` in `requirements.txt`:

```text
coverage>=7.6.0
```

- [ ] **Step 2: Document the final Agent flow and failure guarantee**

Add this section to `docs/system-architecture.md`:

```markdown
## Agent assessment

`AssessmentRunner.assess(EventCandidate)` is the Agent module interface. It owns a private once-compiled LangGraph workflow, the OpenAI-compatible provider adapter, deterministic fallback, advisory policy, and typed assessment-record persistence. Callers and behavioral tests do not access graph state.

The candidate-ingest route persists and canonicalizes an accepted candidate before scheduling `AssessmentHandoff`. The handoff is best-effort: provider and schema failures produce deterministic fallback records, while unexpected defects are logged with candidate/event identity and remain isolated from the `201` ingest response. A process crash after `201` can still lose an assessment job; the system does not claim durable background execution.

Assessment records retain the `enrichment_<candidateId>.json` filename and the existing `candidateId`, `eventType`, `assessment`, and `telemetry` JSON shape. Evaluation loads records through the same typed record implementation.
```

Add this dated bullet to `docs/project-changelog.md`:

```markdown
- **2026-08-10 — Agent architecture deepening:** delivered the private LangGraph assessment runner, authoritative advisory policy, typed legacy-compatible assessment records, and observable best-effort handoff in four vertical TDD slices. `EventCandidate`, ingest behavior, and persisted record shape remain compatible; crash recovery is not claimed.
```

- [ ] **Step 3: Run architecture residue checks**

Run:

```powershell
rg -n "build_enrichment_graph|EnrichmentState|EnrichmentOutput|EnrichmentTelemetry|EnrichmentService|EnrichmentResult|ProviderOutcome|create_enrichment_service" app scripts tests
rg -n "\.ainvoke\(" app scripts tests
rg -n "SEVERITY_MAP|ACTION_MAP|FALLBACK_SEVERITY" app tests
rg -n "except Exception:\s*\r?$" app/agents app/api/events.py
```

Expected:

- Removed legacy names return no matches.
- `.ainvoke()` appears once, inside `app/agents/_workflow.py`.
- Policy mappings appear once in `app/agents/policy.py`; tests contain expected-value tables only.
- The broad catch appears once in `app/agents/handoff.py` and contains `logger.exception`.

- [ ] **Step 4: Run Ruff and formatting checks**

Run:

```powershell
.\.venv\Scripts\ruff.exe check app\agents app\llm app\api\events.py app\main.py app\services\enrichment_eval.py tests\unit\test_assessment_runtime.py tests\unit\test_assessment_policy.py tests\unit\test_assessment_record.py tests\unit\test_assessment_handoff.py tests\unit\test_llm_adapter.py tests\unit\test_enrichment_evaluation.py tests\integration\test_enrichment_pipeline.py tests\integration\test_enrichment_runtime_api.py scripts\run_enrichment.py scripts\run_mock_enrichment.py
.\.venv\Scripts\ruff.exe format --check app\agents app\llm app\api\events.py app\main.py app\services\enrichment_eval.py tests\unit\test_assessment_runtime.py tests\unit\test_assessment_policy.py tests\unit\test_assessment_record.py tests\unit\test_assessment_handoff.py
```

Expected: both commands exit 0.

- [ ] **Step 5: Run focused Agent and ingest tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_assessment_runtime.py tests\unit\test_assessment_policy.py tests\unit\test_assessment_record.py tests\unit\test_assessment_handoff.py tests\unit\test_llm_adapter.py tests\unit\test_enrichment_evaluation.py tests\integration\test_enrichment_pipeline.py tests\integration\test_enrichment_runtime_api.py tests\unit\test_http_publisher.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Run full regression**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ -q
```

Expected: the full suite passes with no failure.

- [ ] **Step 7: Enforce 90 percent Agent-scope line coverage**

Run:

```powershell
$coverageFile = Join-Path $env:TEMP ("p176-agent-coverage-" + [guid]::NewGuid().ToString("N"))
$env:COVERAGE_FILE = $coverageFile
.\.venv\Scripts\python.exe -m coverage erase
.\.venv\Scripts\python.exe -m coverage run --source=app.agents,app.llm.adapter,app.services.enrichment_eval -m pytest tests\unit\test_assessment_runtime.py tests\unit\test_assessment_policy.py tests\unit\test_assessment_record.py tests\unit\test_assessment_handoff.py tests\unit\test_llm_adapter.py tests\unit\test_enrichment_evaluation.py tests\integration\test_enrichment_pipeline.py tests\integration\test_enrichment_runtime_api.py -q
.\.venv\Scripts\python.exe -m coverage report --fail-under=90
```

Expected: coverage command exits 0 with total line coverage at or above 90 percent.

- [ ] **Step 8: Inspect the final diff for external-contract drift**

Run:

```powershell
git diff --check
git diff HEAD~6..HEAD -- app/common/schemas.py app/api/events.py app/agents/assessment.py app/agents/record.py
```

Confirm:

- `EventCandidate` fields are unchanged.
- Endpoint path/status/response behavior is unchanged.
- `AgentAssessment` still has exactly 13 fields.
- Record aliases and filename match the approved spec.

- [ ] **Step 9: Commit acceptance documentation and dependency declaration**

```powershell
git add requirements.txt docs/system-architecture.md docs/project-changelog.md
git commit -m "docs(agent): record deep assessment architecture"
```

- [ ] **Step 10: Report completion evidence**

Record the seven commit hashes, focused/full pytest results, Ruff results, coverage percentage, and the four `rg` residue checks in the implementation handoff. Do not claim durable background execution or CV accuracy improvements.
