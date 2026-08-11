# Agent Deepening in Four Vertical TDD Slices

**Status:** Approved design  
**Date:** 2026-08-10  
**Scope:** Agent assessment execution, advisory policy, assessment records, and candidate-to-assessment handoff  
**Delivery method:** Four sequential vertical TDD slices

## 1. Context

The CV path emits a validated `EventCandidate` through `EventPublisher`. Local JSON and HTTP publishers are two concrete adapters at this seam. The backend persists accepted candidates before scheduling advisory Agent assessment.

The current Agent path is behaviorally functional and has 52 passing focused tests, but its architecture remains shallow in four places:

1. `build_enrichment_graph()` exposes compiled LangGraph state to callers and tests. `EnrichmentService.enrich()` must know state keys, unpack dictionaries, build `AgentAssessment`, and persist a separate record.
2. Advisory policy is spread across system prompt text, fallback branches, severity maps, action maps, and copied test tables.
3. Provider outcome meaning passes through optional state keys, telemetry dictionaries, `EnrichmentResult`, `ProviderOutcome`, JSON, and a separately parsed `EvaluationRecord`.
4. The ingest route owns canonicalization and scheduling order, relies on mutable module globals in tests, and silently discards unexpected background exceptions.

The refactor deepens the Agent module without changing the CV detection implementation or the external candidate-ingest contract.

## 2. Decisions

The approved decisions are:

- Implement all four architecture candidates.
- Deliver them as four sequential vertical TDD slices.
- Preserve controlled compatibility: external contracts remain stable; internal Python interfaces may change.
- Keep LangGraph as private implementation and compile it once per runtime instance.
- Remove `summary` and `actionChecklist` from the authoritative Agent path.
- Keep the background handoff best-effort but observable.
- Do not introduce an outbox, durable queue, retry worker, or new deployment infrastructure.
- Replace tests of shallow modules after equivalent behavior is covered through the deep interface.

## 3. Goals

1. Give production callers and tests one small Agent interface.
2. Keep policy invariants authoritative in one implementation.
3. Give provider telemetry and persistence errors unambiguous typed meaning.
4. Make every in-process background failure observable without delaying or failing candidate ingest.
5. Preserve the current `EventCandidate`, HTTP endpoint, record filename, and record JSON shape.
6. Keep the Agent advisory: it never mutates a candidate or executes an external action.

## 4. Non-goals

- Durable assessment recovery after backend crash or restart.
- A queue, outbox, dead-letter mechanism, or distributed worker.
- New Incident persistence or a database migration.
- Changes to CV detection, tracking, event engines, evidence capture, or VLM validation.
- UI, approval execution, or HITL workflow implementation.
- New protected actions such as alarm or gate-lock execution.
- A second Agent workflow or multi-agent orchestration.

## 5. Compatibility Contract

### 5.1 Stable external seam

The following behavior remains stable:

- `EventCandidate` fields and serialization.
- `POST /internal/api/v1/event-candidates` path, request body, idempotency header, status codes, and response shape.
- Persist-before-assess ordering.
- Duplicate candidates do not schedule a second assessment.
- `enrichment_<candidateId>.json` filename convention.
- Record top-level keys: `candidateId`, `eventType`, `assessment`, and `telemetry`.
- The 13 fields in `AgentAssessment` from SPEC §3.6.

### 5.2 Internal interfaces allowed to break

The following interfaces are internal and may be removed or replaced:

- `build_enrichment_graph()` as a public export.
- `EnrichmentState` and direct `.ainvoke()` access.
- `EnrichmentOutput` and `EnrichmentTelemetry` from `app.common.schemas`.
- `EnrichmentResult` and telemetry dictionaries.
- Direct imports from `app.services.enrichment` and `app.services.assessment_record` after their callers migrate.

No compatibility facade is required for these Python interfaces.

## 6. Target Architecture

```text
CVWorker
  -> EventPublisher seam
       -> local JSON adapter for offline/demo
       -> HTTP adapter for backend ingest
            -> persisted canonical EventCandidate
                 -> observable background handoff
                      -> AssessmentRunner
                           -> private LangGraph implementation
                           -> LLM adapter or deterministic fallback
                           -> authoritative advisory policy
                           -> AgentAssessment + typed outcome
                           -> typed assessment record
```

`AssessmentRunner` is the deep Agent module. Prompt construction, graph state, provider routing, fallback, policy normalization, assessment creation, telemetry construction, and record persistence sit behind its interface.

LangGraph remains useful implementation machinery. It is not a seam and is not exposed to production callers or behavioral tests.

## 7. Public Agent Interface

`app.agents` exports only:

```python
from app.agents.assessment import AgentAssessment, AssessmentOutcome
from app.agents.runtime import AssessmentRunner, create_assessment_runner
```

The runtime interface is:

```python
class AssessmentRunner:
    async def assess(self, candidate: EventCandidate) -> AssessmentOutcome:
        ...
```

The caller must know only these facts:

- Input is a validated, persisted, canonical `EventCandidate`.
- The input is never mutated.
- The call returns a typed deterministic outcome for provider success and all expected provider failures.
- A filesystem write failure is returned separately from provider failure.
- Unexpected implementation defects may escape to the outer handoff, where they are logged and isolated from ingest.

### 7.1 Outcome types

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

Invariants:

- `status == "completed"` implies `provider_output_valid is True` and `fallback_used is False`.
- `status == "fallback"` implies `fallback_used is True`.
- `provider_output_valid` is `False` when no provider is configured, the provider is unavailable, the provider fails, or its output is malformed.
- `persist_error` never changes `status` or `fallback_used`.
- Provider and persistence failures remain separate facts.

## 8. Module Ownership

```text
app/agents/
├── __init__.py      public exports only
├── assessment.py    AgentAssessment, AssessmentTelemetry, AssessmentOutcome
├── runtime.py       deep AssessmentRunner module and composition factory
├── _workflow.py     private LangGraph state, prompt, nodes, and routing
├── provider.py      internal provider port and typed provider result
├── policy.py        authoritative policy and deterministic fallback
├── record.py        typed record, filesystem adapter, and legacy reader
└── handoff.py       observable best-effort background execution
```

Existing ownership changes:

- `app/agents/graph.py` and `app/agents/state.py` are replaced by `_workflow.py` after callers migrate.
- `app/services/enrichment.py` is replaced by `app/agents/runtime.py` after the route and CLI migrate.
- `app/services/assessment_record.py` moves into `app/agents/record.py`.
- `app/services/enrichment_eval.py` keeps aggregate reporting but obtains records through `app.agents.record`.
- `app/llm/adapter.py` remains the production provider adapter.
- `app/common/schemas.py` retains shared CV/backend schemas and loses Agent-only provider/output types.

Files that change together live in `app/agents`; the package owns the whole assessment behavior while keeping internal seams private.

## 9. Provider Seam

The LLM is a true external dependency. The Agent implementation owns an internal provider port:

```python
ProviderSeverity = Literal["INFO", "WARNING", "HIGH", "CRITICAL"]


class ProviderDraft(BaseModel):
    recommended_severity: ProviderSeverity
    rationale: str


class ProviderResult(BaseModel):
    draft: ProviderDraft | None
    latency_ms: float
    model_name: str
    error: str | None = None


class AssessmentProvider(Protocol):
    async def assess(self, *, prompt: str, system_prompt: str) -> ProviderResult:
        ...
```

The production `LLMAdapter` satisfies the port. Behavioral tests use a mock adapter. No LangChain type crosses this seam.

Provider JSON contains exactly:

```json
{
  "recommendedSeverity": "INFO | WARNING | HIGH | CRITICAL",
  "rationale": "fact-based reason"
}
```

`ProviderDraft` uses aliases for the provider's camelCase field. Extra fields are rejected. The prompt no longer requests `summary` or `actionChecklist`.

## 10. Authoritative Advisory Policy

`app.agents.policy` owns all deterministic advisory decisions.

| Provider severity | Assessment severity | Recommended action |
|---|---|---|
| `INFO` | `low` | `log_only` |
| `WARNING` | `medium` | `notify_guard` |
| `HIGH` | `high` | `request_guard_verification` |
| `CRITICAL` | `critical` | `request_manager_review` |

Policy invariants:

- `ABANDONED_OBJECT` is capped at `high` regardless of provider output.
- Agent output never selects `request_alarm` or `request_gate_lock`.
- `requires_human_approval` remains `False` for actions emitted by this module.
- Candidate confidence is copied from `EventCandidate`; the LLM does not invent it.
- Fallback severity and reason are generated by the same policy implementation that normalizes provider drafts.
- Prompt statements are advisory instructions; the policy implementation is authoritative.

The provider path and fallback path cross the same policy seam before producing `AgentAssessment`.

Deterministic fallback severity is fixed by event type:

| Event type | Fallback provider severity | Final assessment severity |
|---|---|---|
| `ZONE_INTRUSION` | `HIGH` | `high` |
| `CROWD_THRESHOLD` | `WARNING` | `medium` |
| `ABANDONED_OBJECT` | `HIGH` | `high` |
| `SUSPECTED_FALL` | `WARNING` | `medium` |
| `COVERAGE_DEGRADED` | `INFO` | `low` |

`EventCandidate` validation rejects event types outside this table. Every fallback reason identifies the deterministic policy path and the candidate event type; it never infers identity, intent, or criminality.

## 11. Provenance

- Provider success records the configured provider model name.
- Deterministic fallback uses `model_name="deterministic-fallback"` in `AgentAssessment`.
- Provider telemetry retains the attempted provider model name when a provider attempt fails.
- `AssessmentTelemetry.model_name` is the configured provider model when a provider was attempted and an empty string when provider execution was disabled before an attempt.
- Because the provider output contract changes, the prompt version advances from `assessment-v1` to `assessment-v2`.
- The existing `model_version` field remains present and uses the configured/default value already supported by the project.
- Every assessment receives a new assessment ID and UTC timestamp.

## 12. Assessment Record

The typed record module owns serialization, write, load, iteration, and evaluation projection.

The writer preserves the current JSON shape:

```json
{
  "candidateId": "candidate-id",
  "eventType": "ZONE_INTRUSION",
  "assessment": {
    "schema_version": "1.0",
    "assessment_id": "assess-uuid",
    "incident_id": "candidate-id",
    "event_type": "ZONE_INTRUSION",
    "severity": "high",
    "confidence": 0.88,
    "reason": "fact-based reason",
    "recommended_action": "request_guard_verification",
    "requires_human_approval": false,
    "model_name": "configured-model",
    "model_version": "configured-version",
    "prompt_version": "assessment-v2",
    "created_at": "2026-08-10T02:00:04Z"
  },
  "telemetry": {
    "latencyMs": 100.0,
    "model": "configured-model",
    "fallbackUsed": false,
    "outputValid": true,
    "error": null,
    "persistError": null
  }
}
```

Record rules:

- Existing record files remain readable.
- New records retain camelCase telemetry keys.
- The current filename convention remains unchanged.
- A successfully written record retains `persistError: null` for shape compatibility.
- A write failure appears in `AssessmentOutcome.persist_error`; it cannot be persisted to the file that failed to write.
- Malformed or unreadable legacy files are skipped by iteration and reported through structured logging.
- `EvaluationReporter` no longer reimplements record parsing.

The filesystem is local-substitutable. Tests use a real temporary directory rather than a public storage port.

## 13. LangGraph Implementation

`_workflow.py` contains all LangGraph-specific state and nodes. Its compiled graph is created once when `AssessmentRunner` is constructed.

The private workflow performs:

1. Build a metadata-only prompt from the typed `EventCandidate`.
2. Call the injected provider adapter when available.
3. Route missing, failed, timed-out, or invalid provider output to deterministic fallback.
4. Return a typed provider/fallback decision to `AssessmentRunner`.

The workflow never receives raw frames, artifact bytes, or evidence URI. It never writes records and never selects final actions independently of the policy module.

No production caller or behavioral test invokes `.ainvoke()` directly.

## 14. Observable Best-effort Handoff

FastAPI composition creates one `AssessmentRunner` and one handoff module. The route obtains intake and handoff through FastAPI dependencies rather than mutable module globals.

Runtime order:

1. Validate candidate.
2. Persist candidate through `PersistedIntake`.
3. Return the existing error response when persistence fails.
4. Canonicalize only an accepted candidate.
5. Schedule the canonical candidate once.
6. Return the existing `201` response without waiting for the provider.
7. Run assessment in the background.
8. Log the terminal result.

Expected provider failures are represented by `AssessmentOutcome(status="fallback")`, not exceptions.

An outermost catch remains in the background handoff solely to isolate unexpected implementation defects. It must call `logger.exception` with:

- `candidate_id`
- `event_type`
- `assessment_status="failed"`
- exception class

No exception is silently discarded. A backend crash after `201` may still lose the assessment job; this is an accepted property of best-effort mode.

## 15. Error Semantics

| Failure | Required behavior |
|---|---|
| LLM disabled or missing credentials | Deterministic fallback; `provider_output_valid=False` |
| Provider unavailable | Deterministic fallback with provider error |
| Provider timeout/network error | Deterministic fallback with latency and provider error |
| Empty or malformed provider JSON | Deterministic fallback; `provider_output_valid=False` |
| Provider policy violation | Normalize/cap through authoritative policy |
| Assessment record write failure | Return assessment with `persist_error`; log write failure |
| Unexpected workflow defect | Handoff logs exception; ingest remains isolated |
| Duplicate candidate | Do not schedule a second assessment |
| Backend crash after `201` | Job may be lost; no recovery promise |

## 16. Four Vertical TDD Slices

### Slice 1: Deep assessment execution

Tests are written first through `AssessmentRunner` for:

- valid provider output;
- missing provider;
- unavailable provider;
- malformed output;
- deterministic fallback;
- immutable input;
- repeated calls through one runner instance.

Then the implementation:

- introduces typed outcome models;
- moves LangGraph to `_workflow.py`;
- compiles the workflow once;
- migrates the route-independent runtime and CLI callers;
- replaces direct graph tests;
- removes public graph/state exports after behavioral coverage exists.

### Slice 2: Authoritative advisory policy

Table-driven tests are written first for:

- all severity/action mappings;
- abandoned-object severity cap;
- deterministic fallback per event type;
- protected actions never emitted;
- candidate confidence preserved;
- provider draft rejects extra fields;
- prompt omits removed fields.

Then policy tables, normalization, fallback, and assessment construction move into one implementation. Duplicated assertions against old mappings are removed after interface tests cover the behavior.

### Slice 3: Deep assessment record

Tests are written first for:

- typed save/load round-trip;
- current record fixture compatibility;
- missing and malformed record behavior;
- iteration over mixed valid/invalid files;
- evaluation projection through the record module;
- no-provider fallback reports `provider_output_valid=False`;
- persistence failure does not change provider/fallback facts.

Then serialization and parsing move into `app.agents.record`, evaluator parsing is deleted, and unused/dictionary telemetry types are removed.

### Slice 4: Observable handoff

Tests are written first for:

- accepted candidate schedules exactly once;
- duplicate candidate schedules nothing;
- canonical header identity reaches assessment;
- slow provider does not enter the ingest response body;
- fallback completion is logged;
- unexpected background failure is logged with required fields;
- dependency substitution requires no module-global monkeypatch;
- local publisher behavior remains available for offline/demo.

Then FastAPI dependencies and the handoff module replace mutable route globals and silent exception handling.

## 17. Test Strategy

The interface is the test surface.

### Behavioral tests

- `AssessmentRunner` tests cover end-to-end Agent behavior with mock provider adapters and temporary filesystem storage.
- Policy tests are pure and table-driven.
- Record tests use real temporary directories.
- Route tests substitute dependencies through FastAPI mechanisms.
- Provider adapter tests retain provider parsing, timeout, and telemetry coverage.

### Tests to replace

- Direct `build_enrichment_graph()` tests.
- Assertions against optional LangGraph state dictionary keys.
- Tests that duplicate severity/action mapping rather than call policy behavior.
- Evaluation tests that construct untyped JSON independently of the record module, except the frozen legacy compatibility fixture.
- Tests that monkeypatch `events_api.enrichment_service` or `events_api.intake` globals.

### Regression gates

Every slice must:

1. Begin with a failing behavioral test.
2. Add the smallest implementation that makes the test pass.
3. Run its focused tests.
4. Run all Agent and ingest tests.
5. Run the full pytest suite.
6. Run Ruff on changed Python files.
7. Finish with an independently revertible commit.

Agent-scope line coverage must remain at or above 90 percent.

## 18. Migration Sequence

1. Add the new public Agent interface alongside current internal callers.
2. Migrate runtime and CLI callers to `AssessmentRunner`.
3. Replace graph/state tests with interface tests.
4. Remove public graph/state exports.
5. Centralize policy and remove old mappings/fallback output.
6. Move record ownership and route evaluation through it.
7. Replace route globals with injected dependencies and observable handoff.
8. Remove obsolete `app.services` Agent modules only after `rg` confirms no callers.

External consumers require no migration. Internal callers migrate within the same slice that introduces their replacement.

## 19. Acceptance Criteria

- `EventCandidate` serialization and ingest endpoint contract are unchanged.
- Current assessment record fixtures load successfully.
- `app.agents` exposes one assessment execution interface.
- `.ainvoke()` appears only inside `_workflow.py`.
- LangGraph compiles once per `AssessmentRunner` instance.
- No policy mapping is duplicated across prompt, fallback, assessment, and tests.
- Provider output no longer contains `summary` or `actionChecklist`.
- Telemetry dictionaries do not cross the Agent interface.
- No `except Exception: pass` remains in the assessment handoff.
- Background defects produce structured exception logs.
- Duplicate candidate intake schedules no second assessment.
- Provider failure always yields a deterministic fallback assessment when the process remains alive.
- Persistence failure never changes provider validity or fallback facts.
- Agent-scope line coverage is at least 90 percent.
- Full pytest and Ruff checks pass after every slice.

## 20. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Internal imports break during migration | Migrate all callers in the same slice; verify with `rg` before deletion |
| Record semantics drift while preserving shape | Frozen legacy fixture plus typed round-trip and evaluation tests |
| Policy centralization accidentally weakens defense | Table-driven caps/actions tests run against provider and fallback paths |
| LangGraph remains indirectly exposed through tests | Delete direct graph tests after runner behavior is covered |
| Broad background catch hides defects again | Require `logger.exception` fields and assert them with log capture |
| Refactor expands into durable processing | Keep crash recovery explicitly outside scope |
| File moves conflict with concurrent work | Stage and commit only slice-owned files; never revert unrelated changes |

## 21. Completion Definition

The program is complete when all four slices have independent green commits, all acceptance criteria pass, obsolete shallow modules and tests are removed, and external candidate/record contracts remain compatible.
