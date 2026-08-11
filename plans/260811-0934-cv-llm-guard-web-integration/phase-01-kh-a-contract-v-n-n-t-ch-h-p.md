---
phase: 1
title: "Khóa contract và nền tích hợp"
status: completed
priority: P1
effort: 2d
dependencies: []
---

# Phase 1: Khóa contract và nền tích hợp

## Context Links

- Base verified: `model-CV-v1@f04c452`; contract history includes `3edd09d`.
- CV sources: `f04c452:app/cv/contracts/**`, `app/cv/phase8_event_adapter.py`, `app/cv/evidence.py`, `tests/contracts/**`.
- LLM sources: `origin/agents:app/agents/{assessment,fallback,graph,state}.py`, `app/llm/adapter.py`, `app/services/{enrichment,assessment_record,intake}.py`; commits `147c2dc`, `862edba`, `dbc37dd`, `a458cc3`, `711ff68`, `4c8d095`.
- Guard sources: `origin/hiep-01156:front-end/src/{api,auth,realtime}/**`, guard incident/alert pages; backend concepts at `back-end/app/api/{alerts,auth}.py`, `back-end/app/services/websocket.py`.

## Overview

Priority P1, completed, 2d. Lock contracts, security boundaries, selective-port manifest, and branch procedure before code movement.

## Key Insights

- Existing branch implementations are references, not merge units. Insecure auth fallback, wildcard CORS, unauthenticated endpoints/WS are explicitly rejected.
- Contract adapter is the only boundary translating CV lifecycle/facts into backend candidate/incident data.

## Requirements

- Functional: define canonical candidate/incident/assessment/action/notification contracts and mapping for exactly three event types.
- Non-functional: backward compatible CVEvent v1; versioned API/WS; deny-by-default security; measurable SLOs and rollback.

## Architecture / Data Flow

Input CVEvent v1 → validate/auth/scope → explicit adapter → canonical command. Outputs are versioned schemas/ADR only in this phase; no runtime mutation. Map string `candidateId` unchanged; generate numeric `incidentId` downstream. Preserve lifecycle separately from operator state.

## Related Code Files

- Source/read: branch paths listed above.
- Proposed create: `docs/adr/cv-incident-integration-contract.md`, `docs/integration/selective-port-manifest.md` (exact docs location re-verify against repository conventions at implementation).
- Proposed modify: CV contract docs/tests only if additive clarification is required; no schema break.
- Ownership: contract/ADR/docs files only; later phases must not edit them concurrently.

## Implementation Steps

1. Create later integration branch `codex/<descriptive-slug>` from exact `f04c452`; record SHA and clean status. Never merge whole source branches.
2. Write failing contract/security tests first: allowed event types, ID type preservation, lifecycle/operator-state separation, advisory immutability, WS envelope, auth/scope denial.
3. Trace and inventory every selected source file/commit; classify port/adapt/reject with rationale. Explicitly exclude Mobile, manager UI, simulator, legacy YOLO/VLM and unsafe backend patterns.
4. Define canonical records and state transitions, idempotency key, version increment semantics, artifact redaction/authorization gate, metadata allowlist for LLM.
5. Define API error model, auth principals/roles/scopes, CORS allowlist, WS authentication/close behavior, ACK/escalation preconditions.
6. Record migration compatibility, feature flags, SLO measurement points, and per-phase rollback gates.

## Todo List

- [x] Contract tests authored before implementation
- [x] ADR and field/state mapping reviewed
- [x] Selective-port manifest pins commits
- [x] Threat boundaries and SLO probes defined
- [x] No unresolved ID/state semantics

## Expected Outputs

- Approved ADR with field tables, state machine, data classification, API/WS versions, idempotency and error semantics.
- Port manifest naming every accepted/rejected seam and pinned source commit.
- Test matrix: unit contract validation; integration auth/adapter; E2E lifecycle/reconnect; security negative cases; performance probes.
- Branch/bootstrap and rollback checklist with no application code merged yet.

## Success Criteria

- [x] Contract suite green: 34/34 tests pass, including 12 JSON parse cases; compile and diff-check pass.
- [x] Review scenario proves `candidateId="0012"` stays string while incident ID is independently numeric.
- [x] Review scenario proves CV END cannot close/resolve an operator incident and LLM cannot mutate effective fields.
- [x] Manifest has no whole-branch merge instruction and no excluded feature.

## Risk Assessment

- High×High contract ambiguity: mitigate with executable fixtures and ADR approval before P2.
- High×High auth ambiguity: explicit principal/scope matrix and deny tests.
- Medium×Medium branch drift: pin SHA and re-diff each ported file.

## Security Considerations

Authenticate internal ingest, REST and WS; scope camera/zone server-side; strict CORS; never infer/fallback guard identity. Define artifact gate as redaction `COMPLETE` plus authorized URI; LLM metadata-only.

## Next Steps / Dependencies

Unblocks P2. P3/P4 may scout sources after this contract is locked but cannot implement against draft semantics.
