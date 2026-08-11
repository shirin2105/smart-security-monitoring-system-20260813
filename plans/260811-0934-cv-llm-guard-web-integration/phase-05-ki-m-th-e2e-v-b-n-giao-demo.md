---
phase: 5
title: "Kiểm thử E2E và bàn giao demo"
status: pending
priority: P1
effort: 1.5d
dependencies: [3, 4]
---

# Phase 5: Kiểm thử E2E và bàn giao demo

## Context Links

- All prior phase contracts, migrations, services and UI.
- CV fixtures/contracts: `f04c452:tests/contracts/**` and `app/cv/contracts/**`.
- Separate non-blocking plans: `plans/260810-phase8-cv-e2e-validation`, `plans/260807-2227-deimv2-phase5b-kaggle-sweep`; their model metrics are not deliverables here.

## Overview

Priority P1, pending, 1.5d. Prove the integrated system under success, security and failure conditions; add observability, deployment/rollback runbooks and reproducible demo handoff.

## Key Insights

- Happy-path demo alone cannot validate durability. Restart, duplicate, outage, authorization and reconciliation scenarios are release gates.
- SLOs need timestamps at ingest commit, outbox publish, Guard render and assessment commit—not subjective observation.

## Requirements

- Functional: execute three event journeys, provisional/update UI, two Guard actions, artifact gate, audit trail and fallback.
- Non-functional: stated latency SLOs, zero duplicate incidents, recovery after component restart, deploy/rollback reproducibility.

## Architecture / Data Flow

Controlled CVEvent fixtures → deployed ingest → real PostgreSQL/outbox/workers → authenticated Guard browser → REST/WS/action/audit. Telemetry correlates `candidateId`, `incidentId`, version and job/outbox IDs; no sensitive payload logged.

## Related Code Files

- Proposed create/modify: E2E fixtures/tests, load/failure-injection scripts, metrics/dashboard/alert config, deployment manifests, operator/demo/rollback runbooks `[exact paths re-verified during implementation]`.
- Read-only sources: all runtime files from P2–P4.
- Ownership: test/observability/deployment/runbook files only; production fixes return to owning phase/file owner sequentially.

## Implementation Steps

1. Finalize tests before demo changes: matrix spans unit, PostgreSQL integration, API/WS contract, browser E2E, security negative, concurrency/replay, restart/recovery and latency.
2. Provision production-like PostgreSQL and authenticated principals/scopes; use deterministic CV fixtures, not fake persistence or bypassed auth.
3. Run each event type end-to-end; verify abandoned remains human-verification candidate, provisional precedes advisory, and effective state/severity remain independent.
4. Inject duplicate/reordered events, DB/dispatcher/worker restart, WS drop/reconnect, LLM timeout/error/invalid result, stale actions and unauthorized/cross-scope access.
5. Measure p50/p95 ingest ack, commit-to-Guard render, enrichment completion/fallback; record sample size/environment and assert thresholds.
6. Add dashboards/alerts for ingest errors/latency, queue/outbox age, retry/dead-letter state, WS connections/errors, fallback rate and action conflicts.
7. Exercise forward migration, rolling deploy compatibility, feature disable and rollback without losing committed incidents/jobs/outbox; document recovery.
8. Produce demo script and handoff with credentials setup (no secrets), expected outputs, troubleshooting and explicit out-of-scope list.

## Todo List

- [ ] Full test matrix passes
- [ ] Failure/restart/replay cases pass
- [ ] Security negative cases pass
- [ ] SLO evidence captured
- [ ] Observability alerts exercised
- [ ] Deploy/rollback and demo rehearsed

## Expected Outputs

- Machine-readable E2E/security/performance results for all three event types and failure scenarios.
- Dashboards/alerts plus correlation and privacy-safe logging guidance.
- Versioned deployment manifest, migration order, rollback/recovery runbook and reproducible Guard-first demo script.
- Release checklist stating manager approve/decline, Mobile, simulator, legacy YOLO/VLM and CV Phase8 metrics are out of scope.

## Success Criteria

- Full project compile/lint/unit/integration/browser E2E commands (resolved from live package config) exit 0; no test is skipped to hide a failure.
- Ingest ack p95 `<250ms`; provisional Guard visibility p95 `<1s` LAN; LLM update or fallback `≤5s`, with environment/sample evidence.
- 100 repeated/concurrent identical events create one incident and zero extras; reconnect converges to latest REST version.
- Every unauthorized ingest/REST/WS and cross-scope case rejects; valid ACK/escalation has exactly one atomic audit entry.
- Rollback drill preserves committed data and allows later job/outbox replay without cascading damage.

## Risk Assessment

- High×High false confidence from mocks: real PostgreSQL/browser/network path required; fakes limited to deterministic provider/publisher failure injection.
- Medium×High flaky timing: synchronized timestamps, warm-up, adequate samples and separated LAN/provider measurements.
- Medium×High rollback data incompatibility: expand/contract migrations and old/new version compatibility rehearsal.

## Security Considerations

Use least-privilege test principals, synthetic/redacted artifacts, secret injection outside git, sanitized telemetry and retention controls. Include dependency/container scan if configured; never weaken auth for demo.

## Next Steps / Dependencies

Requires P3 and P4. Release only after all gates pass. If a production file needs correction, return sequentially to its owner and rerun the entire affected matrix. Unresolved questions: exact deployment target and repository-standard command names must be discovered from live configuration during implementation.
