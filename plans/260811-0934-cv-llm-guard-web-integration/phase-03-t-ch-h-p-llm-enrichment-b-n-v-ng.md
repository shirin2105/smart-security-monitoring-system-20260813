---
phase: 3
title: "Tích hợp LLM enrichment bền vững"
status: pending
priority: P1
effort: 2.5d
dependencies: [2]
---

# Phase 3: Tích hợp LLM enrichment bền vững

## Context Links

- Port selectively from `origin/agents:app/agents/{assessment,fallback,graph,state}.py`, `app/llm/adapter.py`, `app/services/{enrichment,assessment_record}.py`.
- Reference tests: `origin/agents:tests/unit/test_{agent_assessment,enrichment_agent,enrichment_service,llm_adapter}.py`, `tests/integration/test_enrichment_{pipeline,runtime_api}.py`.
- Relevant commits: `147c2dc`, `862edba`, `dbc37dd`, `a458cc3`, `711ff68`, `4c8d095`.

## Overview

Priority P1, pending, 2.5d. Port only advisory assessment logic into a durable DB worker with deterministic fallback and versioned update outbox.

## Key Insights

- LLM output is untrusted advisory data. Effective severity/state remain operator/backend controlled.
- Existing filesystem intake/background task patterns violate durability and are replaced, not ported.

## Requirements

- Functional: claim enrichment jobs; construct metadata-only prompt; validate structured assessment; persist attempt/result/fallback; enqueue `INCIDENT_UPDATED` atomically.
- Non-functional: update or fallback within `≤5s`; bounded timeout/retry; restart-safe; no raw artifact sent to LLM.

## Architecture / Data Flow

DB job claim → load authorized incident metadata (not image/video bytes/URI content) → LLM adapter → schema/policy validation → assessment record + incident version/update outbox transaction. On timeout/error/invalid output, deterministic fallback follows the same persistence path. Neither path mutates effective severity/state.

## Related Code Files

- Source: branch paths above; exclude `app/services/intake.py` production filesystem/background-task behavior and legacy VLM code/tests.
- Proposed target: `app/agents/**`, `app/llm/adapter.py`, enrichment worker/service and assessment repository under the backend package selected in P1 `[UNVERIFIED]`.
- Proposed tests: focused unit/integration worker, policy, fallback, timeout and crash-recovery tests.
- Ownership: LLM/assessment/enrichment worker files only; do not edit P2 persistence ownership except agreed repository interfaces.

## Implementation Steps

1. Write failing tests first for prompt allowlist, structured output, factual/advisory separation, timeout, invalid JSON, provider error, retry exhaustion, deterministic fallback, crash recovery and update versioning.
2. Port assessment/state/fallback/adapter logic commit-by-commit; remove dependencies on excluded intake/VLM paths and keep provenance in manifest.
3. Implement DB job claimant with lease/reclaim and `FOR UPDATE SKIP LOCKED`; define bounded attempts and total deadline compatible with 5s SLO.
4. Build prompt only from allowlisted metadata; validate/sanitize LLM response and record model/config/latency/error without secrets.
5. Atomically persist immutable assessment attempt/result and enqueue versioned `INCIDENT_UPDATED`; effective fields must be unchanged by invariant/DB/service checks.
6. Implement deterministic fallback for every terminal failure and ensure initial provisional alert is independent/already visible.
7. Run controlled fake provider tests for deterministic timeout/failure only; integration uses configured real adapter or contract test server, never production shortcuts.

## Todo List

- [ ] Tests-first failure matrix complete
- [ ] Selective source port audited
- [ ] Metadata allowlist enforced
- [ ] Durable worker/fallback implemented
- [ ] Advisory immutability verified
- [ ] 5s deadline measured

## Expected Outputs

- Ported assessment graph/adapter with durable enrichment worker, validated assessment schema, deterministic fallback and immutable assessment records.
- `INCIDENT_UPDATED` outbox event carrying new incident version but not unauthorized artifact data.
- Metrics: queue age, provider latency/error/timeout, fallback count, completion latency; traces correlate candidate/incident/job.
- Test evidence covering provider and process failure modes.

## Success Criteria

- Targeted unit/integration pytest suites pass; controlled provider timeout returns persisted fallback and update notification within `≤5s`.
- Test asserts effective severity/operator state byte-for-byte unchanged after both LLM success and failure.
- Initial provisional alert exists even if worker never starts.
- Worker restart reclaims unfinished job without duplicate assessment/update version.

## Risk Assessment

- High×High provider latency/outage: hard deadline + deterministic fallback + independent provisional notification.
- Medium×High prompt data leak: explicit metadata DTO/allowlist and outbound payload test.
- Medium×Medium malformed/harmful output: strict schema, length/enumeration validation, escape rendering, audit raw response under retention policy.

## Security Considerations

Never transmit artifacts, credentials or authorized URI contents to LLM. Minimize metadata, redact logs, constrain provider egress, encrypt assessment data, and treat advice as untrusted UI text.

## Next Steps / Dependencies

Requires P2 durable jobs/outbox. P4 consumes versioned updates. Rollback stops worker and update publisher while retaining jobs/assessments for replay; revert ported modules without deleting durable rows.
