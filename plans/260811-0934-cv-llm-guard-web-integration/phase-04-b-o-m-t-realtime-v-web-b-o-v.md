---
phase: 4
title: "Bảo mật realtime và Web bảo vệ"
status: pending
priority: P1
effort: 3d
dependencies: [2]
---

# Phase 4: Bảo mật realtime và Web bảo vệ

## Context Links

- Selective UI sources: `origin/hiep-01156:front-end/src/api/**`, `auth/**`, `realtime/**`, `components/alerts/**`, `components/hitl/**`, `components/incidents/**`, guard pages.
- Backend concept sources: `origin/hiep-01156:back-end/app/api/{alerts,auth}.py`, `back-end/app/services/websocket.py`.
- Reject source behavior: auth fallback, unauthenticated REST/WS, wildcard CORS; exclude manager pages/actions and `mobile/**`.

## Overview

Priority P1, pending, 3d. Deliver secure REST/WS and Guard-first Web experience for provisional/update notifications, reconciliation, ACKNOWLEDGE and REQUEST_ESCALATION.

## Key Insights

- WS is a lossy hint, never a state transport/source of truth. UI fetches/reconciles via REST and dedupes by incident/version.
- Guard actions are state transitions with authorization, optimistic concurrency and atomic audit—not UI-only buttons.

## Requirements

- Functional: scoped incident list/detail; authenticated WS hints; reconnect reconciliation; artifact access gate; ACK/escalation with reason/version; provisional and assessed states.
- Non-functional: provisional visibility p95 `<1s` LAN; accessible/responsive UX; no manager approve/decline or Mobile.

## Architecture / Data Flow

Outbox publisher → authenticated/scoped WS hub → envelope hint → client dedupe `(incidentId,version)` → scoped REST fetch → render canonical incident. Guard action sends expected version/reason → backend locks/checks role+scope+state+version → action + audit + version/outbox atomically → clients reconcile.

## Related Code Files

- Source: branch paths above.
- Proposed target backend: authenticated incident/action REST routes, scoped WS hub, artifact authorization endpoint, CORS config `[UNVERIFIED target paths]`.
- Proposed target frontend: `front-end/src/api/**`, `auth/**`, `realtime/**`, Guard incident/alert/HITL components/pages; prune manager-only routes/actions.
- Tests: backend auth/scope/action/WS tests; frontend adapter/reconnect/dedupe/action/accessibility tests.
- Ownership: P4 owns REST/WS/auth/CORS and `front-end/**`; it consumes, not edits, P2/P3 repositories except agreed interfaces.

## Implementation Steps

1. Write failing backend/frontend tests first: unauthorized/forbidden, cross-camera/zone access, CORS, WS auth expiry, dropped/reordered/duplicate hints, reconnect, stale action version, invalid state/reason/role, atomic audit rollback.
2. Port/adapt API types/transports and explicit auth context/protected routes; remove mock transport from production path and forbid fallback guard identity.
3. Implement scoped REST list/detail with version/ETag-like concurrency semantics and artifact response only when redaction COMPLETE plus URI authorization.
4. Implement authenticated WS handshake and per-principal subscription filtering; emit only required envelope fields and close/re-authenticate on expiry/revocation.
5. Implement client reconnect/backoff, last-known version cache, REST reconciliation and dedupe by `(incidentId,version)`; tolerate update-before-create and missed hints.
6. Port Guard-only pages/components; show provisional vs assessed advisory clearly; mark abandoned as requiring human verification.
7. Implement ACKNOWLEDGE and REQUEST_ESCALATION backend transitions with required reason policy, expected version, atomic audit/outbox; do not add manager approve/decline.
8. Validate accessibility, responsive behavior, security headers/CORS and LAN visibility timing.

## Todo List

- [ ] Tests-first backend/frontend matrix complete
- [ ] REST/WS auth and scope enforced
- [ ] Reconnect/reconcile/dedupe verified
- [ ] Guard-only UI ported
- [ ] ACK/escalation audit atomic
- [ ] Artifact gate and strict CORS verified

## Expected Outputs

- Secure versioned REST and WS endpoints, scoped queries/subscriptions, authorized artifact delivery.
- Guard Web incident queue/detail with provisional then advisory update, reliable reconciliation and only two MVP actions.
- Atomic action/audit records and update hints; frontend/backend contract fixtures.
- Security, accessibility and notification-latency test reports.

## Success Criteria

- Unauthorized ingest/REST/WS and cross-scope requests are rejected; wildcard CORS absent; no fallback identity path.
- Drop WS messages, reconnect, and verify REST reaches latest version with one rendered update per `(incidentId,version)`.
- Concurrent/stale ACK or escalation returns conflict and creates no partial audit/action; valid action creates exactly one audit row atomically.
- Provisional incident becomes visible p95 `<1s` LAN; LLM failure does not remove/suppress it.

## Risk Assessment

- High×High authorization leak: scoped repository queries + subscription filtering + adversarial tests.
- High×High action race: row lock/optimistic version + atomic audit transaction.
- Medium×High WS loss/order: REST reconciliation and version dedupe.
- Medium×Medium XSS from advice: render as text/sanitize and apply CSP.

## Security Considerations

Deny-by-default role/scope checks on every path; short-lived WS auth or revocation handling; CSRF strategy per credential mode; rate/size limits; strict origin allowlist; no sensitive WS payload. Artifact URI must not become SSRF/open redirect.

## Next Steps / Dependencies

Requires P2; consumes P3 update event when available. P5 requires P3+P4. Rollback feature-flags Guard routes/WS/actions, leaves REST read compatibility and durable outbox intact, then restores prior UI build.
