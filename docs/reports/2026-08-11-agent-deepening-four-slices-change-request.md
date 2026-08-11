# Change Request — Agent Deepening in Four Vertical TDD Slices

**Date:** 2026-08-11
**Branch:** `agents`
**Status:** Implemented, merged locally (fast-forward), all gates green

## Change Overview

| Aspect | Value |
|--------|-------|
| Type | Refactor (internal architecture), no external contract change |
| Scope | Agent assessment module: `app/agents/*`, `app/llm/adapter.py`, `app/api/events.py`, `app/main.py`, `app/services/enrichment_eval.py`, `app/common/schemas.py`, `scripts/`, tests |
| Lines | +1291 / −1352 across 36 files |
| External contracts | **Unchanged** — `EventCandidate`, `POST /internal/api/v1/event-candidates` (201/ACCEPTED, DUPLICATE_IGNORED, 500), record filename `enrichment_<candidateId>.json`, top-level record keys, telemetry keys, 13-field `AgentAssessment` |
| Commits | 10 (`2f9bd95` → `0c01a25`), fast-forward merged |

## What Changed and Why

### 1. Public graph interface retired (Slice 1)

**Before:** callers (route, scripts, tests) constructed `build_enrichment_graph()` and invoked `.ainvoke()` with raw state dicts; the LangGraph implementation was a public seam.

**After:** `AssessmentRunner.assess(EventCandidate) -> AssessmentOutcome` is the only Agent interface. The workflow lives in private `app/agents/_workflow.py`; the only `.ainvoke()` in the repo is there. The runner compiles the graph once per instance and owns provider routing, policy, and record persistence.

**Why:** the graph/state shape was leaking into callers; every caller duplicated routing and telemetry logic. A single typed seam makes behavior testable through one interface and free to evolve internally.

### 2. Strict two-field provider contract (Slice 2)

**Before:** the provider emitted `EnrichmentOutput` with `recommendedSeverity`, `rationale`, `summary`, `actionChecklist`; severity/action mappings were duplicated across `assessment.py`, `fallback.py`, and tests.

**After:** provider output contains only `recommendedSeverity` + `rationale` (enforced by `ProviderDraft` with `extra="forbid"`); `LLMAdapter.assess()` returns `ProviderResult` (draft or typed error). All mappings live once in `app/agents/policy.py`; `fallback_draft()` is deterministic per event type; `ABANDONED_OBJECT` is capped at `HIGH`. Prompt version is `assessment-v2`.

**Why:** the model was being asked to produce fields the system does not consume; scattered policy drifted. One owner prevents mapping divergence.

**Impact on consumers:** persisted records no longer carry `summary`/`actionChecklist`. No consumer read them (verification: zero residue in app/scripts/tests). The prompt no longer requests them.

### 3. Typed legacy-compatible records (Slice 3)

**Before:** `app/services/assessment_record.py` parsed/serialized JSON dicts by hand; `enrichment_eval.py` independently re-parsed files with its own glob/prefix/`_parse_file` logic.

**After:** `app/agents/record.py` owns the on-disk shape: `AssessmentRecord`/`RecordTelemetry` with camelCase aliases, `AssessmentRecordStore.save()/load()/iter_records()`; malformed files are skipped once (logged `assessment_record_invalid`). `EvaluationReporter` consumes the store; its summary keys are unchanged.

**Impact on consumers:** on-disk JSON is byte-compatible (same filename, same keys, same alias names). **One semantic change:** `severity` values in records are now lowercase (`high` not `HIGH`) because the typed `AgentAssessment` domain is lowercase. Report `severity_counts` follow (`{"high": N}`). Consumers of the eval report should expect lowercase keys. Legacy uppercase-severity files are skipped by the typed loader.

### 4. Observable best-effort handoff (Slice 4)

**Before:** the route swallowed `Exception: pass` in a module-level background function; no observability.

**After:** `AssessmentHandoff.run()` is the single outermost execution point; the only broad catch in agent scope always logs via `logger.exception` with candidate/event identity (`agent_assessment_failed`), and success logs `agent_assessment_completed` (INFO; ERROR when persistence failed). Dependencies are injected through `create_app()`/FastAPI `Depends`; accepted candidates schedule once, duplicates schedule zero.

**Why:** silent failures are invisible; a structured log is the minimum guarantee.

## Verification

- 129/129 tests pass (baseline 52 at plan start).
- Agent-scope line coverage 98% (gate ≥90%).
- Ruff check + format clean.
- Four residue checks: no legacy names, one `.ainvoke()` (private), policy mappings single-owned, one broad catch with `logger.exception`.

## Accepted Limitations (unchanged by design)

- **Best-effort, not durable:** a process crash after `201` can still lose an assessment job. No queue, outbox, retry worker, or crash recovery is provided or claimed.
- **Advisory only:** assessments never mutate a candidate and never execute external actions.
- **Persist-error diagnostics:** when record persistence fails, the ERROR log carries the `persist_error` string; a real traceback is not currently captured (the exception is caught inside the store). A cosmetic `NoneType: None` line appears. See follow-up options below.

## Follow-up Options (not included in this change)

| Option | Effort | Value |
|--------|--------|-------|
| Carry exception on `AssessmentOutcome` and pass as `exc_info` | Small | Real stack on persist failures; removes the `NoneType: None` noise |
| Log the ERROR at the catch site in `record.py` (`sys.exc_info()` live) | Small | Same benefit, second logging site |
| Drop the `exc_info` marker (keep clean record body) | Trivial | Removes misleading noise, loses nothing the plan required |
| `SEVERITY_MAP.get(...)` default for unknown provider severities | Trivial | Closes the same drift gap fixed for `FALLBACK_SEVERITY` |
| Repair `datasets/mock_enrichment_candidates.json` (pre-existing) | Small | Default script smoke works without `--dataset` override |

## Approvals Requested

- Merge acceptance of the four-slice deep Agent architecture (local merge already performed).
- Decision on the persist-error diagnostics option (one of the three above).
