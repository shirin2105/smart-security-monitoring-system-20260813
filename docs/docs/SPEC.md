# Spec

> **Trạng thái:** Baseline kỹ thuật đề xuất — cần approve trước khi scaffold source code. 
> **Jira:** BAC — Backpropagation

---

## 1. Mục tiêu

Xây MVP trong 5 tuần: chuyển video camera (được duyệt/giả lập) thành các sự kiện an ninh có audit cho 3 loại core:

- `ZONE_INTRUSION`
- `CROWD_THRESHOLD`
- `ABANDONED_OBJECT`

Hệ thống bắt buộc cung cấp:

- Hiển thị sự kiện realtime.
- Evidence đã redaction và AI enrichment minh bạch.
- 2 vai trò ứng dụng: `security_guard` và `security_manager`.
- HITL do server enforce cho sự kiện nghiêm trọng và escalation.
- Lịch sử incident và action/audit append-only.
- Deploy bằng Docker, tái lập được.

AI/CV không bao giờ được phân duyệt escalation, thực hiện hành động bên ngoài, suy đoán danh tính hoặc kết luận ý định phạm tội.

---

## 2. Baseline Kiến trúc

Dùng **modular monolith + một CV worker**:

```text
apps/
  api/        FastAPI + domain modules + WebSocket + LangGraph enrichment
  web/        React dashboard
workers/
  cv/         OpenCV + YOLO + tracking + rules + redaction
packages/
  contracts/  JSON/OpenAPI fixtures versioned, dùng chung các workstream
infra/
  docker/     Compose, proxy, health config
  migrations/ Database migrations

tests/
  contract/
  integration/
  e2e/
  fixtures/

docs/
  architecture/
  api/
  evaluation/
  operations/
```

### Boundary bắt buộc

- CV worker sở hữu stream/inference/rules/redaction; không sở hữu user hay HITL.
- API/Postgres sở hữu policy, effective severity, state, audit và dữ liệu source-of-truth.
- LLM enrichment chạy async, chỉ advisory; không được mutate severity/state.
- WebSocket chỉ là kênh notification; REST/Postgres vẫn là source of truth.
- React không enforce bảo mật; backend RBAC mới enforce.

### Complexity bị cấm trong MVP

- Kubernetes, Kafka, RabbitMQ, Redis/Celery trừ khi có ADR được duyệt chứng minh cần thiết cho P0.
- RAG/vector DB trên critical path.
- Lưu trữ raw video, facial recognition, dữ liệu biometric.
- Escalation tự động ra ngoài hoặc điều khiển vật lý.

---

## 3. Cấu trúc Project mục tiêu

```text
P-176/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── auth/
│   │   │   ├── cameras/
│   │   │   ├── events/
│   │   │   ├── incidents/
│   │   │   ├── policies/
│   │   │   ├── audit/
│   │   │   ├── enrichment/
│   │   │   └── core/
│   │   └── tests/
│   └── web/
│       ├── src/
│       │   ├── app/
│       │   ├── features/
│       │   │   ├── auth/
│       │   │   ├── cameras/
│       │   │   ├── alerts/
│       │   │   ├── hitl/
│       │   │   └── incidents/
│       │   ├── components/
│       │   ├── lib/
│       │   └── styles/
│       └── tests/
├── workers/
│   └── cv/
│       ├── core_cv/
│       │   ├── ingestion/
│       │   ├── inference/
│       │   ├── tracking/
│       │   ├── rules/
│       │   ├── evidence/
│       │   └── telemetry/
│       └── tests/
├── packages/
│   └── contracts/
│       ├── schemas/
│       ├── fixtures/
│       └── openapi/
├── infra/
│   ├── docker/
│   └── migrations/
├── tests/
│   ├── contract/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
├── docs/
├── .env.example
├── compose.yaml
└── README.md
```

Ưu tiên tổ chức theo feature/domain, module nhỏ gắn kết và boundary rõ ràng. File thường giữ 200–400 dòng và không vượt 800 dòng nếu không có kế hoạch tách được duyệt.

---

## 4. Commands — Interface mục tiêu

> Source repository chưa tồn tại. Các command dưới đây định nghĩa interface mà scaffold phải cung cấp; **không khẳng định đã chạy được hôm nay**.

Chọn một task runner duy nhất (`Makefile`, `justfile`, hoặc scripts repo-owned) và expose các command tương đương:

| Command | Hành vi mong đợi |
|---|---|
| `make bootstrap` | Kiểm tra prerequisites, tạo local env từ example, cài dependencies repo-owned |
| `make dev` | Start Postgres, API, web và CV simulator cho local dev |
| `make dev-api` | Chạy FastAPI với reload |
| `make dev-web` | Chạy React dev server |
| `make dev-cv` | Chạy CV worker với fixture video đã duyệt |
| `make test` | Chạy tất cả unit và contract test deterministic |
| `make test-unit` | Unit test API/CV/web |
| `make test-contract` | Contract test Candidate/API/WS/React |
| `make test-integration` | Integration test API+DB+WS |
| `make test-e2e` | Critical operator flows |
| `make coverage` | Xuất coverage report; enforce ≥80% domain logic deterministic |
| `make lint` | Lint Python và TypeScript |
| `make format` | Formatters repo-owned |
| `make typecheck` | Static typing Python + typecheck TypeScript |
| `make build` | Build production API/web/CV images/artifacts |
| `make up` | Start Docker Compose stack |
| `make down` | Stop stack, mặc định không xóa data |
| `make migrate` | Apply DB migrations |
| `make seed-demo` | Seed demo data deterministic, không nhạy cảm |
| `make smoke` | Health + một end-to-end event smoke check |
| `make verify` | Lint + typecheck + tests + build + security baseline |

Ràng buộc:

- Không remote one-off package execution trong command thường.
- Dùng pinned/project-owned dependencies.
- Cleanup destructive phải là command riêng, yêu cầu confirm ngoài CI.
- `.env.example` chỉ chứa tên biến/placeholder, không bao giờ có secret thật.

---

## 5. Code Style & Design Rules

### Cross-cutting

- Immutable mặc định; trả về giá trị mới thay vì mutate domain state chung.
- Validate mọi input tại system boundary bằng schemas.
- Xử lý lỗi tường minh; không silent fallback.
- Hàm thường <50 dòng; nesting ≤4 mức.
- Constants/config cho thresholds, retention, timeouts, policies; không magic number.
- Correlate log với `requestId`, `eventId`, `cameraId` khi liên quan.
- Không bao giờ log frame bytes, credentials, tokens hoặc personal data chưa sanitize.

### Python/FastAPI/CV

- Type hints bắt buộc cho public/internal service interfaces.
- Pydantic models tại API/contract boundaries.
- Domain/state-transition logic tách khỏi FastAPI route functions.
- ORM/query APIs parameterized; không nối chuỗi SQL.
- CV rules là deterministic modules testable, độc lập với OpenCV loops.
- Worker chạy non-root trong container nếu khả thi.
- Configuration immutable sau startup, trừ policy reload có version.

### TypeScript/React

- Strict TypeScript; không unbounded `any` tại contracts.
- Tách server state, URL state, form state và local UI state.
- Presentational components giữ pure; containers sở hữu data/side effects.
- Semantic HTML accessible, keyboard navigation và visible focus.
- Design tokens qua CSS custom properties; không hardcode palette/spacing lặp lại.
- WebSocket events update cache/state model reconcile với REST; không phải source of truth.
- Không `dangerouslySetInnerHTML` cho LLM/user content.

### API conventions

- Version public endpoints dưới `/api/v1`.
- Envelope nhất quán: `success`, `data`, `error`, `meta`.
- `Idempotency-Key` cho retryable writes.
- Optimistic concurrency bằng `expectedVersion`/`If-Match`; stale → `409`.
- State change và audit write trong cùng transaction.
- Pagination bắt buộc cho event/audit lists.

---

## 6. Domain Invariants

### Candidate/event

- Observations không trực tiếp thành confirmed incidents.
- Temporal rules và deduplication bắt buộc.
- Mọi event lưu `modelVersion`, `ruleVersion`, `policyVersion` và timestamps.
- Nguồn `SIMULATED` phải gắn nhãn rõ.

### Severity

- LLM `recommendedSeverity` chỉ advisory.
- Backend policy tính `effectiveSeverity`.
- Confidence score không phải xác suất nguy hiểm/ý định.
- Severe overrides phải kèm audit.

### HITL

- Trong site/camera scope được gán, Guard được acknowledge/resolve/dismiss INFO/WARNING và request escalation.
- Manager kế thừa quyền Guard và là vai trò duy nhất được confirm/dismiss HIGH/CRITICAL, resolve severe event đã confirm, hoặc approve/decline escalation.
- Mọi action validate theo canonical state/role/scope matrix với allow/deny unit và E2E tests.
- Không service account, CV worker, LLM hay scheduler nào được confirm hay approve escalation.
- Reasons bắt buộc cho quyết định severe.
- Human security actions và audit records append-only, commit cùng transaction với state transition.
- Review timeout sinh trạng thái overdue/expired, không tự động escalation.
- External action ngoài phạm vi MVP; chỉ có trạng thái phê duyệt trong app.

### Privacy

- Không facial recognition hay identity inference.
- Raw frames chỉ tồn tại tạm trong worker memory.
- Face blur/redaction phải hoàn tất trước khi artifact persist hoặc serve.
- Redaction thất bại thì drop artifact, chỉ giữ metadata được phép.
- Evidence access phải authorized, no-store và audited.
- LLM chỉ nhận controlled metadata; không frame/artifact/user/audit content.

---

## 7. Chiến lược Test

### Các tầng test bắt buộc

1. **Unit**
   - Polygon/ROI, dwell, count, stationary/proximity, dedupe.
   - Severity policy và state transitions.
   - RBAC matrix và action validation.
   - Idempotency/concurrency validation.
   - LLM output schema/fallback.
   - React reducers/view states.

2. **Contract**
   - CV Candidate fixture → FastAPI validation.
   - REST/OpenAPI và WebSocket payload fixtures.
   - React parsing/rendering cho từng contract version.

3. **Integration**
   - FastAPI + Postgres migrations/transactions.
   - Candidate idempotency và append-only action/audit.
   - Artifact redaction gate/access control.
   - WebSocket authentication/scope/reconnect/reconcile.

4. **E2E**
   - Intrusion/crowd/abandoned object bật trên Gate 2 test clips.
   - Full state/role/scope matrix: Guard acknowledge/resolve/dismiss INFO/WARNING + request; Manager thêm confirm/dismiss HIGH/CRITICAL, resolve confirmed severe + approve/decline.
   - Denied transition, wrong-role, stale-version, site- và camera-scope paths cho REST, artifacts và WebSocket.
   - LLM outage fallback.
   - WebSocket disconnect và REST reconcile.

5. **Security/privacy/resilience**
   - Secret/dependency/image scans.
   - RBAC/scope bypass, guessed IDs, expired WS token và malformed RTSP/config.
   - Failed blur không upload image.
   - Retention approval và scheduled-deletion behavior trước pilot.
   - Camera, worker, API, DB, disk, WebSocket và LLM failure modes.

6. **Evaluation**
   - Versioned calibration và hold-out video manifests.
   - Event-level metrics, không chỉ frame metrics.
   - Hardware/video/sample-size disclosure.

### Coverage

- Tối thiểu 80% cho deterministic domain logic do team viết.
- Exclude model weights, generated artifacts và framework internals, ghi minh bạch.
- Visual tests bổ sung nhưng không thay thế behavioral coverage.

### TDD

Cho mỗi deterministic behavior mới:

1. Thêm unit/contract test fail.
2. Chạy và ghi nhận RED.
3. Implement tối thiểu để pass.
4. Chạy GREEN.
5. Refactor trong khi giữ tests.
6. Chạy integration/E2E liên quan và coverage.

---

## 8. Security & Operational Baseline

- TLS tại reverse proxy cho deploy không phải local.
- Postgres private; CV worker cô lập trong camera network/internal API.
- RTSP schemes/CIDR/DNS allow-listed; credentials qua secret reference.
- CORS/WS origins allow-listed; WebSocket authentication, expiry và per-event site/camera scope được enforce.
- REST, artifact, action và audit queries enforce cùng site/camera scope; guessed IDs không vượt được authorization.
- Rate limit login/write.
- Security headers và CSP trên web.
- Structured logs không chứa sensitive payloads.
- Health/readiness/metrics chỉ internal.
- Pin Docker/dependencies và scan.
- Backup/restore và rollback test trước release.

Proposed retention chờ owner/legal phê duyệt:

- Redacted evidence: 7 ngày.
- Event metadata: 90 ngày.
- Audit: 365 ngày.

Pilot deploy là No-Go cho tới khi retention owner duyệt policy và scheduled deletion được test. Privacy-closed evidence, zero auto-approval, append-only audit và authorization-scope integrity là release invariants không điều kiện, không phải performance targets `Proposed`.

---

## 9. Hành vi khi lỗi

- Camera stale → degraded/offline; không bao giờ hiển thị stale như live.
- Worker failure → bounded restart + health alert; reset track state an toàn.
- API/DB unavailable → hiển thị coverage degradation rõ; không claim zero-loss.
- LLM failure → deterministic fallback; không chặn workflow.
- WebSocket failure → reconnect + REST reconcile.
- Disk/artifact issue → metadata có thể persist; không bao giờ lưu raw fallback.
- Invalid policy → atomic reject, giữ version trước đó.
- Review timeout → overdue, không bao giờ auto-escalate.

Durable CV-worker spool nằm ngoài scope rõ ràng; nếu backend unavailable, coverage gaps phải observable và được ghi lại.

---

## 10. Boundaries — Luôn làm / Hỏi trước / Không bao giờ

### Luôn làm

- Validate mọi input từ user, camera, contract và external service.
- Persist critical Event/Incident state trước realtime broadcast.
- Enforce RBAC/state transitions tại backend.
- Thêm audit cùng human security decisions trong một transaction.
- Fail privacy-closed khi redaction lỗi.
- Có fallback cho LLM/provider errors.
- Thêm tests trước hoặc cùng implementation.
- Báo cáo measured metrics kèm dataset/hardware context.
- Cập nhật API contract và fixtures trước khi đổi cross-workstream schema.

### Hỏi trước

- Đổi core event definitions hoặc severity policy.
- Thêm/bớt yêu cầu P0.
- Gửi evidence tới bất kỳ external service/LLM nào.
- Bật external notifications hoặc physical actions.
- Đổi retention hoặc evidence storage.
- Thêm infrastructure dependency/broker/database mới.
- Dùng footage chưa được duyệt.
- Deploy public Internet hoặc đổi auth strategy.
- Bắt đầu fall detection trước khi Gate 2 conditions đạt.

### Không bao giờ làm

- Auto-confirm hoặc auto-approve escalation.
- Suy đoán identity, criminal intent, protected traits hoặc guilt.
- Persist/serve unredacted evidence khi policy yêu cầu redaction.
- Commit secrets hoặc lộ RTSP credentials.
- Xem LLM output là state/severity authoritative.
- Im lặng nuốt detection, security, privacy hoặc audit failures.
- Claim production accuracy/SLA vượt ngoài measured pilot context.
- Thêm Kafka/Kubernetes/RAG/vector DB vào MVP khi chưa có approved decision và P0 need.
- Đánh Done khi chưa có acceptance/test evidence.

---

## 11. Definition of Ready / Done

### Ready

- Requirement/acceptance, owner, due date và priority rõ ràng.
- Contracts/fixtures tồn tại cho cross-workstream changes.
- Dependencies/data/hardware/permissions sẵn sàng hoặc có fallback.
- Test/eval/security/privacy impacts được ghi rõ.

### Story Done

- Acceptance criteria và tests phù hợp PASS.
- Errors/fallbacks và boundary validation tồn tại.
- Không vi phạm secrets/PII.
- Logs/metrics đủ chẩn đoán.
- Contract/docs cập nhật.
- Review xong và evidence link trong Jira.

### Release Done

- Fresh deployment/migration/health PASS.
- Backup/restore/rollback đã diễn tập.
- Cả ba core events, gồm abandoned object, đều bật và PASS Gate 2 E2E fixtures.
- RBAC/HITL/privacy negative tests PASS trên REST, evidence và WebSocket site/camera scope.
- Retention được duyệt và scheduled deletion đã test.
- Human security actions/audit append-only; zero auto-confirm/auto-approve.
- Không critical/high issue chưa xử lý.
- Evaluation/limitations/runbook/demo fallback đã publish.

---

## 12. Quyết định mở trước khi code

- Repository/package manager/task runner.
- Python/Node versions và lockfile tools cụ thể.
- YOLO/tracker models và hardware target.
- LLM provider/model/timeout/budget/data terms.
- OIDC hay private-network demo auth.
- Artifact storage và approved retention.
- Deployment target và public/private exposure.
- Proposed metric floor approval tại BAC-22.

Tới khi được duyệt, implementation phải dùng replaceable adapters/configuration và tránh hardcode provider-specific assumptions.

---

_Last updated: 29/07/2026 · Cần approval trước khi scaffold repository._
