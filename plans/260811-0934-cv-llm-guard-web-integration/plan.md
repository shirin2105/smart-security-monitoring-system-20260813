---
title: "Tích hợp CV, LLM và cảnh báo Web bảo vệ"
description: "Tích hợp có chọn lọc luồng CVEvent v1 → incident bền vững → LLM tư vấn → Guard Web realtime an toàn."
status: in-progress
priority: P1
effort: 12d
branch: "codex/feat/cv-llm-guard-web"
tags: [cv, llm, postgres, realtime, guard-web, security]
blockedBy: []
blocks: []
created: "2026-08-11"
createdBy: "ck:plan"
source: skill
---

# Tích hợp CV, LLM và cảnh báo Web bảo vệ

## Overview

Khởi tạo nhánh tích hợp `codex/*` sau này từ tip `model-CV-v1` `f04c452`; cherry-pick/port theo seam, không merge nguyên nhánh. PostgreSQL là nguồn sự thật; realtime chỉ báo có thay đổi, REST trả trạng thái chuẩn.

Progress: 1/5 phases completed (20%). Phase 1 verified on `codex/feat/cv-llm-guard-web`; Phase 2 implementation is in progress, with live PostgreSQL tests and ack p95 benchmark still open; phases 3-5 pending.

## Scope

- In: ba loại `ZONE_INTRUSION`, `CROWD_THRESHOLD`, `ABANDONED_OBJECT`; ingest có xác thực; incident/outbox PostgreSQL; LLM advisory; Guard Web ACK/escalation; REST/WS bảo mật; quan sát và E2E.
- Out: Mobile, manager UI/approve/decline, simulator, legacy YOLO/VLM, Kafka, filesystem intake, production `BackgroundTasks`.
- `ABANDONED_OBJECT` luôn là candidate cần người xác minh, không tự xác nhận.

## Architecture & Data Flow

`CVEvent v1 → authenticated ingest → canonical adapter → candidate + incident + provisional outbox (one transaction) → Guard hint → durable enrichment worker → assessment/fallback + update outbox → Guard REST reconciliation`.
Artifact chỉ khả dụng khi redaction `COMPLETE` và URI được ủy quyền; LLM chỉ nhận metadata.

## Key Decisions

- Giữ `candidateId` dạng string; backend cấp `incidentId` numeric riêng. CV `START/UPDATE/END` không phải operator incident state.
- CV confidence là fact; LLM severity/advice là advisory, không sửa effective severity/state.
- Alert provisional sau durable commit, trước LLM. Timeout/lỗi LLM dùng fallback xác định, không chặn alert đầu.
- Outbox/job dùng DB durable (`FOR UPDATE SKIP LOCKED` phù hợp). Idempotency bảo đảm duplicate không tạo incident mới.
- WS envelope: `schemaVersion,type,incidentId,version,occurredAt,cameraId`; reconnect gọi REST và dedupe `(incidentId,version)`.
- Mọi ingest/REST/WS cần auth + camera/zone scope server-side; CORS allowlist; không guard identity fallback.

## Expected Final Outputs

- ADR/contract mapping và selective-port manifest; migrations + rollback; authenticated ingest/REST/WS; durable workers/outbox.
- LLM assessment/fallback audit record; Guard Web provisional/update UX và ACK/escalation atomic.
- Unit/integration/E2E/security/performance evidence, dashboards/runbook/deployment-demo handoff.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Khóa contract và nền tích hợp](./phase-01-kh-a-contract-v-n-n-t-ch-h-p.md) | Completed |
| 2 | [Tiếp nhận CV và lưu incident](./phase-02-ti-p-nh-n-cv-v-l-u-incident.md) | In Progress |
| 3 | [Tích hợp LLM enrichment bền vững](./phase-03-t-ch-h-p-llm-enrichment-b-n-v-ng.md) | Pending |
| 4 | [Bảo mật realtime và Web bảo vệ](./phase-04-b-o-m-t-realtime-v-web-b-o-v.md) | Pending |
| 5 | [Kiểm thử E2E và bàn giao demo](./phase-05-ki-m-th-e2e-v-b-n-giao-demo.md) | Pending |

## Dependency Graph

`P1 → P2 → P3`; `P2 → P4`; `P3 + P4 → P5`. Parallel work only where file ownership in phase files does not overlap.

## Risks

- High×High: identity/scope leak → deny-by-default auth, scoped queries, negative tests.
- Medium×High: duplicate/race → unique keys, atomic transaction, locked workers, replay tests.
- Medium×High: alert delayed by LLM → provisional outbox before enrichment + deterministic fallback.
- Medium×Medium: branch drift → pin source commits, port manifest, contract tests; never whole-branch merge.
- High×High: PostgreSQL behavior unverified in current environment → provide `TEST_DATABASE_URL` or Docker, run 7 live integration tests before Phase 2 completion.
- Medium×High: ack p95 unmeasured → run benchmark against live PostgreSQL and retain result before Phase 2 completion.

## Success Criteria

- Ingest ack p95 `<250ms`; provisional Guard visibility p95 `<1s` LAN; LLM update/fallback `≤5s`.
- Duplicate/replay creates zero extra incident; unauthorized ingest/REST/WS rejected.
- Restart/reconnect loses no durable work; Guard reconciles via REST; audit/action updates atomic.

## Cross-Plan Note

`260810-phase8-cv-e2e-validation` and `260807-2227-deimv2-phase5b-kaggle-sweep` remain separate and do not block contract integration. This plan does not claim CV Phase 8 model metrics.
