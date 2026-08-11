# Implementation Report — Agent Deepening in Four Vertical TDD Slices

**Date:** 2026-08-11
**Branch:** `agents` (feature branch `agent-deepening-slices`, fast-forward merged)
**Plan:** `docs/superpowers/plans/2026-08-10-agent-deepening-four-slices.md`
**Design source:** `docs/superpowers/specs/2026-08-10-agent-deepening-four-slices-design.md`

## Summary

Replaced the shallow Agent graph, scattered policy, duplicated record parsing, and silent background handoff with one deep typed assessment module, delivered as four sequential vertical TDD slices plus acceptance. `EventCandidate`, ingest endpoint behavior, record filename, top-level record keys, and the 13-field `AgentAssessment` shape remain stable. LangGraph is now private and compiles once per `AssessmentRunner` instance; the handoff is best-effort but observable; no durable background execution or crash-recovery is claimed.

## Commits (9, in order)

| Hash | Message |
|------|---------|
| `2f9bd95` | refactor(agent): introduce deep assessment runner |
| `c2c3460` | refactor(agent): make LangGraph implementation private |
| `3ec76dd` | refactor(agent): centralize authoritative advisory policy |
| `f1cb6dc` | refactor(agent): deepen assessment record ownership |
| `6f53c7a` | refactor(agent): evaluate typed assessment records |
| `3c3c1b7` | test(agent): cover legacy uppercase-severity skip in reporter |
| `cb55558` | refactor(agent): make background handoff observable |
| `74af06f` | docs(agent): record deep assessment architecture |
| `7ea1f54` | style(agent): enforce ruff check and format gates |
| `0c01a25` | fix(agent): pin handoff traceback and fallback default |

Base: `a12f9ee` (branch forked from `agents`). Merge: fast-forward, no conflicts.

## Slice Deliverables

### Slice 1 — Deep Assessment Execution (`2f9bd95`, `c2c3460`)

- `app/agents/runtime.py` — `AssessmentRunner` (owns a private once-compiled LangGraph workflow, provider routing, policy, record persistence) and `create_assessment_runner()`.
- `app/agents/_workflow.py` — private `WorkflowState`, `SYSTEM_PROMPT`, `_compile_graph`, `AssessmentWorkflow.run()`; the only `.ainvoke()` in the repo lives here.
- `app/agents/assessment.py` — `AgentAssessment` retained; added `AssessmentStatus`, `AssessmentTelemetry`, `AssessmentOutcome`.
- `app/agents/__init__.py` — exports only the public interface: `AgentAssessment`, `AssessmentOutcome`, `AssessmentRunner`, `create_assessment_runner`.
- All callers migrated: `app/api/events.py` route, `scripts/run_enrichment.py`, `scripts/run_mock_enrichment.py`, integration and unit tests.
- Deleted: `app/agents/graph.py`, `app/agents/state.py`, `app/services/enrichment.py`, `tests/unit/test_enrichment_agent.py`, `tests/unit/test_enrichment_service.py`.
- Residue check: `build_enrichment_graph|EnrichmentState|EnrichmentService|create_enrichment_service` → zero matches; `.ainvoke(` → exactly one match in `_workflow.py`.

### Slice 2 — Authoritative Advisory Policy (`3ec76dd`)

- `app/agents/provider.py` — strict two-field `ProviderDraft` (`extra="forbid"`), `ProviderResult`, `AssessmentProvider` Protocol. Provider output contains only `recommendedSeverity` + `rationale`; `summary`/`actionChecklist` removed from the authoritative path (zero residue).
- `app/agents/policy.py` — single-owner `SEVERITY_MAP`, `ACTION_MAP`, `FALLBACK_SEVERITY`; `fallback_draft()` deterministic by event type; `build_agent_assessment()` with the `ABANDONED_OBJECT` HIGH cap.
- `app/llm/adapter.py` — `assess()` returns `ProviderResult`; malformed/empty/invalid drafts return `draft=None` with error class; `asyncio.to_thread` retained.
- Deleted: `app/agents/fallback.py`, `tests/unit/test_agent_assessment.py`; removed `EnrichmentOutput`/`EnrichmentTelemetry` from `app/common/schemas.py`.
- Prompt version `assessment-v2`; `_build_prompt()` reads typed candidate attributes, omits `artifact.uri`, `summary`, `actionChecklist`.

### Slice 3 — Deep Assessment Record (`f1cb6dc`, `6f53c7a`, `3c3c1b7`)

- `app/agents/record.py` — `RecordTelemetry` + `AssessmentRecord` (camelCase aliases, `populate_by_name`) and `AssessmentRecordStore.save()/load()/iter_records()`. Filename `enrichment_<candidateId>.json`, top-level keys `candidateId`/`eventType`/`assessment`/`telemetry`, telemetry keys `latencyMs`/`model`/`fallbackUsed`/`outputValid`/`error`/`persistError` — all pinned by tests.
- Persistence failure is decoupled from provider outcome: `persist_error` flows on the outcome while status stays `completed`.
- `app/services/enrichment_eval.py` — `EvaluationReporter.load_records()` consumes `AssessmentRecordStore.iter_records()`; no `json.loads`/`ENRICHMENT_PREFIX`/`_parse_file` remain; summary keys unchanged; severity now lowercase per the typed domain.
- Deleted: `app/services/assessment_record.py`.
- Fix round: added `test_reporter_skips_legacy_uppercase_severity` so the reporter test discriminates the typed path from the old pass-through (legacy uppercase files are skipped by the typed validator).

### Slice 4 — Observable Candidate-to-assessment Handoff (`cb55558`)

- `app/agents/handoff.py` — `AssessmentHandoff.run()`; the only broad catch in agent scope, always `logger.exception` with candidate/event identity; success logs `agent_assessment_completed` (INFO, ERROR when `persist_error`), failure logs `agent_assessment_failed`.
- `app/api/events.py` — module globals removed; `get_intake()`/`get_assessment_handoff()` FastAPI dependencies; accepted candidates schedule `handoff.run` once via `BackgroundTasks`; duplicates schedule zero; 201/ACCEPTED/DUPLICATE_IGNORED/500 behavior unchanged.
- `app/main.py` — `create_app(*, intake=None, assessment_runner=None)` composes state once; `from app.main import app` preserved; no provider call at factory time.
- Route tests use real `BackgroundTasks` with a recording stub — scheduling without invocation proven; `test_http_publisher.py` keeps the global `app` import assertion.

## Acceptance Gates

| Gate | Result |
|------|--------|
| Focused Agent/ingest tests | 55 passed |
| Full regression (`pytest tests\ -q`) | 129 passed (was 52 at baseline), 0 failures |
| Ruff check | exit 0 (17 files) |
| Ruff format --check | exit 0 |
| Coverage (agent scope, `--fail-under=90`) | **98%** total; per-module 93–100% |
| Residue: legacy names (`build_enrichment_graph`/`EnrichmentOutput`/`ProviderOutcome`/etc.) | zero matches |
| Residue: `.ainvoke(` | exactly one, `app/agents/_workflow.py` |
| Residue: policy mappings | only `app/agents/policy.py` |
| Residue: broad catch | single, `app/agents/handoff.py` + `logger.exception` |
| `git diff --check` | exit 0 |
| Contract: `EventCandidate` fields | unchanged |
| Contract: endpoint path/status/response | unchanged |
| Contract: `AgentAssessment` | exactly 13 fields |
| Contract: record aliases + filename | match approved spec |

## Fix Rounds

- **Task 5 fix round 1/5** (`6f53c7a` → `3c3c1b7`): severity-case change made explicit via lowercase assertions; discriminating reporter test added. Re-review: both ADDRESSED.
- **Final whole-branch review fix wave** (`7ea1f54` → `0c01a25`): (a) `FALLBACK_SEVERITY.get(event_type, "INFO")` — ADDRESSED, restoring the deleted `fallback.py` default for unknown event types; (b) persist-error ERROR log `exc_info` marker — re-review found NOT ADDRESSED (the OSError is caught inside `record_store.save()`, so no live exception exists at the handoff frame; the marker emits a synthetic `NoneType: None` traceback). **Parked with ruling:** a genuine fix requires an `AssessmentOutcome` exception field or a second logging site in `record.py` — both public-contract changes beyond the plan; the plan never mandated a traceback. The marker remains in place; the noise it produces is a known cosmetic defect (see Known Issues).

## Known Issues (parked, non-blocking)

1. **`NoneType: None` on persist-error ERROR records** — `handoff.py` sets `exc_info=outcome.persist_error is not None`, but no exception object is live at that site; the record shows a false `NoneType: None` traceback plus the `persist_error` string. Real fix: carry the exception on `AssessmentOutcome`, or log the ERROR at the catch site in `record.py`. Decision needed: accept the marker, drop it, or carry the exception.
2. **`SEVERITY_MAP[draft.recommended_severity]` drift** — same shape as the fixed `FALLBACK_SEVERITY`; a future 6th severity would hard-KeyError in the background task. Apply the same `.get()` default if a new severity appears.
3. **Default dataset mismatch** (pre-existing, out of scope) — `datasets/mock_enrichment_candidates.json` fails `EventCandidate` validation (missing `cameraId`/`detectedAt`/`firstSeenAt`/`lastSeenAt`); `scripts/run_mock_enrichment.py` needs `--dataset datasets/mock_cv_output_candidates.json`. Unrelated to this refactor.
4. **Deferred minors** — `_workflow.py` docstring references deleted `graph.py`; `EvaluationRecord` docstring describes removed `_parse_file`; `BACKEND_EVENT_DIR` duplicated (main.py + runtime.py default); handoff INFO-path `exc_info` unused when `persist_error` is None; unsanitized `candidate_id` in filename (pre-existing pattern).

## Claims

- ✅ `EventCandidate`, ingest behavior, record filename, top-level record keys, 13-field `AgentAssessment` — all unchanged, diff-inspected.
- ✅ Agent assessment advisory; never mutates a candidate (pinned by test).
- ✅ LangGraph private, compiled once per runner instance.
- ❌ NOT claimed: durable background execution (a crash after `201` can lose an assessment job), CV accuracy improvements, retry/outbox/queue semantics.
