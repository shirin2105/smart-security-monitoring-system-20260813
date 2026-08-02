# Product Requirements Document

---

## 1. Executive Summary

hỗ trợ đội an ninh khu đô thị giám sát nhiều camera bằng cách:

1. Phân tích video bằng Computer Vision.
2. Phát hiện candidate cho ba sự kiện core: xâm nhập vùng cấm, tụ tập và vật thể bỏ quên.
3. Đánh giá theo policy, bổ sung mô tả/checklist bằng AI Agent.
4. Gửi cảnh báo realtime kèm evidence đã bảo vệ quyền riêng tư.
5. Yêu cầu con người xác nhận mọi escalation nghiêm trọng.
6. Lưu incident timeline và audit trail để quản lý theo dõi.

MVP không thay thế bảo vệ, không xác định danh tính và không tự thực hiện hành động vật lý/đối ngoại. Giá trị của sản phẩm là **giảm tải quan sát và rút ngắn thời gian phát hiện/xác minh**, không phải trao quyền quyết định an ninh cho AI.

---

## 2. Problem & Opportunity

### 2.1. Hiện trạng

- Khu đô thị có nhiều camera nhưng số người trực hữu hạn.
- Việc nhìn liên tục nhiều màn hình dẫn tới bỏ sót và mệt mỏi.
- Sự cố thường được tìm thấy sau khi xem lại video, thay vì được xử lý sớm.
- Các cảnh báo rule-based đơn giản dễ gây false positive và mất niềm tin.
- Quy trình xác nhận, escalation và audit thường rời rạc.

### 2.2. Problem statement

> Nhân viên an ninh cần một công cụ ưu tiên các sự kiện đáng chú ý từ nhiều camera, cung cấp evidence và ngữ cảnh rõ ràng, nhưng vẫn giữ quyền xác minh và escalation ở con người.

### 2.3. Cơ hội

Kết hợp CV, policy engine, AI enrichment, realtime dashboard và HITL trong một pipeline đơn giản giúp:

- Giảm số luồng cần quan sát chủ động.
- Rút ngắn thời gian từ sự kiện tới cảnh báo.
- Chuẩn hóa quyết định xử lý và audit.
- Tạo dữ liệu định lượng để cải thiện detector/policy theo từng khu vực.

---

## 3. Objective, Goals & Non-goals

### 3.1. Objective

Trong 5 tuần, bàn giao MVP deploy được, chứng minh end-to-end rằng video có thể tạo candidate event, được policy/Agent enrich, hiển thị realtime, con người xác nhận/từ chối và hệ thống lưu incident/audit.

### 3.2. Product goals

| ID   | Goal                                                                    | Success evidence                                    |
| ---- | ----------------------------------------------------------------------- | --------------------------------------------------- |
| G-01 | Phát hiện 3 sự kiện core trên nguồn video giả lập/được phép | Eval report theo event, test clips và demo         |
| G-02 | Cảnh báo realtime có evidence, description và severity              | BAC-59, BAC-60 E2E PASS                             |
| G-03 | HITL bắt buộc cho escalation nghiêm trọng                           | Negative tests: zero auto-approval; audit 100%      |
| G-04 | Hai role sử dụng đúng chức năng                                   | RBAC integration/E2E tests                          |
| G-05 | Incident có thể truy vết                                             | Timeline, action history, version fields            |
| G-06 | MVP deploy reproducibly                                                 | Fresh Docker deployment + runbook                   |
| G-07 | Báo cáo chất lượng minh bạch                                      | Dataset/model/hardware/sample size đi kèm metrics |

### 3.3. Non-goals

- Facial recognition, biometric database, identity matching hoặc person re-identification.
- Tự động gọi cảnh sát/cấp cứu, SMS/email hàng loạt, khóa cổng hay điều khiển thiết bị.
- NVR/full-video archive hoặc forensic evidence platform.
- Multi-tenant public SaaS, multi-region, HA/Kubernetes.
- Fine-tune model/MLOps platform nếu pretrained + rules đủ cho MVP.
- Cam kết SLA/accuracy production ngoài tập dữ liệu và hardware công bố.

---

## 4. Users, Personas & Jobs-to-be-Done

## 4.1. Persona A — Bảo vệ trực

**Mục tiêu:** phát hiện nhanh sự kiện, xem evidence, acknowledge và yêu cầu escalation khi cần.

**Pain points:**

- Quá nhiều camera.
- Cảnh báo thiếu ngữ cảnh hoặc quá nhiều false positive.
- Không rõ cảnh báo đã được ai xử lý.

**JTBD:**

> Khi có một sự kiện bất thường, tôi muốn nhận cảnh báo rõ ràng kèm evidence và hành động phù hợp để xác minh nhanh mà không bỏ sót hoặc xử lý trùng.

**Quyền MVP:**

- Xem camera/event trong phạm vi được cấp.
- Xem evidence đã blur.
- Acknowledge, thêm ghi chú, resolve/dismiss INFO/WARNING trong scope và request escalation.
- Không confirm/dismiss HIGH/CRITICAL hoặc approve/decline escalation.

## 4.2. Persona B — Quản lý an ninh

**Mục tiêu:** duyệt sự cố nghiêm trọng, kiểm soát policy, xem lịch sử/audit và đánh giá khu vực rủi ro.

**Pain points:**

- Thiếu trạng thái thống nhất giữa cảnh báo và xử lý.
- Khó truy vết ai đã quyết định gì.
- Khó đo false alert hoặc thời gian phản ứng.

**JTBD:**

> Khi sự cố được đánh dấu nghiêm trọng, tôi muốn xem evidence, lý do severity và lịch sử hành động để phê duyệt/từ chối escalation có trách nhiệm và audit được.

**Quyền MVP:**

- Tất cả quyền Guard trong site.
- Confirm/dismiss HIGH/CRITICAL.
- Resolve HIGH/CRITICAL đã confirm; resolve/dismiss INFO/WARNING khi cần theo scope.
- Approve/decline escalation kèm reason.
- Xem audit, báo cáo, heatmap nếu feature được GO.

## 4.3. Operational persona — Người vận hành hệ thống

Không phải role UI bắt buộc trong MVP. Trách nhiệm qua runbook:

- Deploy/config/secrets/backup.
- Kiểm tra camera/worker/API/DB health.
- Phản ứng khi coverage degraded hoặc disk/API/DB lỗi.

---

## 5. User Journeys

## 5.1. Journey A — Intrusion được xác nhận

1. Person track vào restricted ROI đủ dwell time.
2. CV worker tạo `EventCandidate` và evidence đã blur.
3. Backend validate/deduplicate/persist và áp dụng effective severity.
4. WebSocket gửi `event.created`; dashboard reconcile qua REST khi cần.
5. Guard mở event, xem evidence và acknowledge.
6. Nếu HIGH/CRITICAL, Manager review và confirm/dismiss.
7. Nếu cần escalation, Manager approve/decline kèm reason.
8. Mọi transition được ghi audit; incident được resolve.

**Outcome:** con người quyết định; AI chỉ giúp phát hiện và hiểu sự kiện.

## 5.2. Journey B — False positive

1. Candidate được tạo và hiển thị.
2. Operator xem evidence và chọn dismiss với reason.
3. Backend ghi action và audit.
4. Dữ liệu dismiss được dùng để đánh giá/tune; không tự huấn luyện model trong MVP.

## 5.3. Journey C — LLM không khả dụng

1. Candidate được persist bình thường.
2. LLM timeout/schema invalid/rate-limited.
3. Hệ thống dùng deterministic description/checklist fallback.
4. UI hiển thị enrichment unavailable nhưng vẫn cho review/HITL.

## 5.4. Journey D — Camera/API mất kết nối

- Camera stale → `DEGRADED/OFFLINE`, không dùng frame cũ như live.
- API/DB unavailable → dashboard/monitoring hiển thị coverage degraded; không tuyên bố đang giám sát bình thường.
- WebSocket disconnect → reconnect và REST reconcile theo version/cursor.

---

## 6. Scope — MoSCoW

### Must have

- 3 event core: `ZONE_INTRUSION`, `CROWD_THRESHOLD`, `ABANDONED_OBJECT`.
- Camera/video simulator và metadata.
- Evidence đã face-blur/redaction thành công trước persist/serve; nếu redaction lỗi chỉ giữ metadata được phép.
- Deterministic policy + Agent enrichment có schema/fallback.
- FastAPI/Postgres source of truth.
- WebSocket realtime + REST reconciliation.
- React camera grid, alert queue, event detail.
- Authentication/RBAC 2 roles.
- HITL confirm/dismiss và escalation approval/decline.
- Incident log/filter/pagination.
- Audit trail.
- Docker Compose, health, logs, backup/rollback baseline.
- Test/evaluation report.

### Should have

- Face blur tự động trước persist/serve evidence.
- Configurable ROI/dwell/count/stationary thresholds.
- Camera health states.
- LLM cost/latency/fallback telemetry.
- Security/privacy hardening.
- UI empty/loading/error/reconnect states.

### Could have

- Heatmap điểm nóng.
- Context memory theo khu vực/giờ.
- Té ngã shadow mode.
- Cross-camera object tracking không định danh.

### Won't have trong MVP

- Autonomous external escalation.
- Recognition/identity/biometric inference.
- Durable message broker, RAG/vector DB bắt buộc, Kubernetes.
- Public multi-tenant SaaS và mobile native.

---

## 7. Product & System Boundaries

### 7.1. Kiến trúc MVP

```text
MP4/RTSP Simulator
        │
        ▼
CV Worker
OpenCV → YOLO → tracking → zone/rule engine → redaction
        │ EventCandidate
        ▼
FastAPI / Incident Management
validate → dedupe → policy/RBAC → Postgres/audit → WebSocket
        │                                      │
        │                                      ▼
        │                                  React Dashboard
        ▼
Async LangGraph/LLM Enrichment
controlled metadata → structured summary/checklist → fallback
```

### 7.2. Quyết định đơn giản hóa

- **Modular monolith + một CV worker**, không microservice fleet.
- FastAPI/Postgres là source of truth.
- WebSocket không phải source of truth.
- Không Kafka/Redis/Celery trong MVP.
- LangGraph có thể chạy trong backend process/task boundary phù hợp; không trên đường persist critical.
- Docker Compose cho pilot/site đơn; không tuyên bố HA.

### 7.3. Boundary table

| Module    | Owns                                                                   | Không owns                                               |
| --------- | ---------------------------------------------------------------------- | --------------------------------------------------------- |
| CV worker | Stream, frame sampling, detection, tracking, temporal rules, redaction | Auth, HITL, external action                               |
| FastAPI   | Validation, event/incident state, policy, RBAC, audit, REST/WS         | RTSP decode, model inference                              |
| Agent     | Recommended severity, fact-only summary, checklist                     | Effective severity, state transition, escalation approval |
| React     | Presentation, user input, realtime UX                                  | Source of truth, security enforcement                     |
| Postgres  | Events, incidents, actions, audit, configuration                       | Raw video/blob payload                                    |

---

## 8. Event, Severity & HITL Models

## 8.1. Event types

| Type                  | Candidate rule                                                     | MVP note                         |
| --------------------- | ------------------------------------------------------------------ | -------------------------------- |
| `ZONE_INTRUSION`    | Person track trong armed polygon vượt dwell threshold            | Core                             |
| `CROWD_THRESHOLD`   | Distinct person tracks vượt count threshold trong hold duration  | Core                             |
| `ABANDONED_OBJECT`  | Object stationary đủ lâu và không có person association gần | Core; conservative policy        |
| `SUSPECTED_FALL`    | Pose/temporal detector riêng                                      | Stretch, shadow/review candidate |
| `COVERAGE_DEGRADED` | Camera/worker/API/model unhealthy                                  | Operational event                |

### Invariants

- Một frame không đủ tạo incident; cần temporal condition.
- Model confidence không đồng nghĩa mức nguy hiểm.
- Mỗi Event có `modelVersion`, `ruleVersion`, `policyVersion`.
- Simulated source phải được gắn `SIMULATED`.

## 8.2. Severity

| Severity     | Ý nghĩa                                      | Default Proposed                            |
| ------------ | ---------------------------------------------- | ------------------------------------------- |
| `INFO`     | Health/observation không cần phản ứng ngay | Operational/reconnect                       |
| `WARNING`  | Guard cần kiểm tra                           | Crowd nhẹ, public-zone intrusion           |
| `HIGH`     | Manager review bắt buộc trước escalation   | Restricted intrusion, abandoned candidate   |
| `CRITICAL` | Review ưu tiên; không auto-escalate         | Sensitive zone ngoài giờ, policy explicit |

### Effective severity rule

```text
recommendedSeverity = Agent output (validated, advisory)
effectiveSeverity   = policy(eventType, zone, schedule, thresholds)
```

- Agent không được tự đổi `effectiveSeverity`.
- Manager có thể quyết định theo workflow, nhưng mọi override phải audit.
- `ABANDONED_OBJECT` tối đa HIGH trong MVP.
- `SUSPECTED_FALL` WARNING/shadow; không auto-escalate.

## 8.3. Lifecycle state

```text
DETECTED → ASSESSED → ALERTED

INFO/WARNING:
OPEN → ACKNOWLEDGED → RESOLVED | DISMISSED

HIGH/CRITICAL:
PENDING_REVIEW → CONFIRMED → RESOLVED
               → DISMISSED
               → EXPIRED
```

## 8.4. Escalation state — chỉ trong ứng dụng

```text
NONE → REQUESTED → APPROVED | DECLINED
```

`APPROVED` chỉ ghi nhận quyết định có audit trong . MVP không gửi thông báo ra ngoài, gọi lực lượng bên ngoài hoặc điều khiển thiết bị vật lý.

### HITL invariants

- Guard được acknowledge/resolve/dismiss INFO/WARNING và tạo `REQUESTED` trong site/camera scope; Manager có các quyền đó, đồng thời mới được confirm/dismiss HIGH/CRITICAL, resolve event đã confirm và approve/decline escalation.
- Mọi action phải PASS state, role và site/camera scope; allow/deny matrix được unit/E2E test.
- CV, Agent, service account và scheduler không được confirm, approve hoặc thực hiện hành động ngoài hệ thống.
- Lý do bắt buộc cho severe dismiss/resolve và escalation approve/decline.
- Overdue review không tự escalation.
- State transition, `EventAction` và `AuditLog` append-only phải được ghi trong cùng transaction; không update/delete lịch sử quyết định.

---

## 9. Functional Requirements

### 9.1. Camera & CV

| ID       | Requirement                                                                      | Acceptance criteria                                                                                                                                                              | Jira           |
| -------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| FR-CV-01 | Hệ thống nhận MP4/RTSP giả lập và gắn`cameraId`, timestamp, source type | ≥4 video source có thể hiển thị trong demo; stale source có health state                                                                                                   | BAC-23, BAC-50 |
| FR-CV-02 | YOLO/tracker tạo observation person/object                                      | Output có class, bbox, confidence, trackId và modelVersion                                                                                                                     | BAC-18, BAC-24 |
| FR-CV-03 | Intrusion theo polygon/dwell configurable                                        | Test clip inside tạo candidate; near-boundary negative không tạo sai theo threshold                                                                                           | BAC-25         |
| FR-CV-04 | Crowd theo distinct count/ROI/hold                                               | Threshold chỉnh được; không đếm duplicate track như người mới                                                                                                         | BAC-26         |
| FR-CV-05 | Abandoned object theo stationary/proximity                                       | Conservative candidate; có positive/negative clip; phải bật và PASS E2E trên test clip tại Gate 2; feature flag chỉ dùng theo camera sau khi P0 đã được chứng minh | BAC-27         |
| FR-CV-06 | Candidate có evidence/bbox/metadata                                             | Payload đúng contract; candidateId stable cho idempotency; evidence chỉ được persist/serve khi redaction`COMPLETE`, nếu không phải drop artifact                      | BAC-28         |
| FR-CV-07 | Productionize face blur trước persist/serve                                    | Privacy gate áp dụng từ vertical slice; blur fail → không persist/serve image; BAC-29 tăng độ phủ/hiệu năng và test                                                  | BAC-29, BAC-61 |
| FR-CV-08 | Té ngã chỉ stretch/shadow                                                     | Không chặn core; không external escalation                                                                                                                                    | BAC-30         |
| FR-CV-09 | Cross-camera tracking không định danh là optional advanced                   | Chỉ bắt đầu sau Gate 2 và không là dependency của ba core event; không face recognition/re-identification định danh                                                   | BAC-31         |

### 9.2. AI Agent

| ID       | Requirement                                          | Acceptance criteria                                                       | Jira           |
| -------- | ---------------------------------------------------- | ------------------------------------------------------------------------- | -------------- |
| FR-AI-01 | LangGraph chạy detect/assess/plan/enrich tối giản | Event metadata tạo output schema hợp lệ hoặc fallback                 | BAC-19, BAC-33 |
| FR-AI-02 | Agent tạo recommended severity và rationale        | Output validated; không ghi trực tiếp effective severity/state         | BAC-34         |
| FR-AI-03 | Agent tạo fact-only summary/report                  | Không suy đoán identity/intent/criminality; UI gắn nhãn AI-generated | BAC-35         |
| FR-AI-04 | Agent tạo action checklist từ allow-list           | Không tool call/external action                                          | BAC-39         |
| FR-AI-05 | HITL interrupt/wait cho severe workflow              | Không có đường auto-confirm; timeout thành overdue                  | BAC-36         |
| FR-AI-06 | Timeout/schema/provider failure có fallback         | Event persist và review vẫn hoạt động; status enrichment unavailable | BAC-40         |
| FR-AI-07 | Memory là optional advanced                         | Chỉ làm sau Gate 2; không là dependency core                          | BAC-37, BAC-38 |

### 9.3. Backend & Data

| ID       | Requirement                                           | Acceptance criteria                                                                                                                                                                                                                                                      | Jira   |
| -------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ |
| FR-BE-01 | FastAPI có config, logging và health endpoints      | Missing config fail fast;`/health/live`/`ready` phản ánh dependency                                                                                                                                                                                                | BAC-41 |
| FR-BE-02 | Postgres lưu camera/event/incident/user/action/audit | Migration từ môi trường sạch PASS;`EventAction` và `AuditLog` append-only, không có API update/delete lịch sử                                                                                                                                              | BAC-42 |
| FR-BE-03 | Internal candidate ingestion validate/idempotent      | Duplicate candidate không tạo incident trùng; invalid payload 4xx                                                                                                                                                                                                     | BAC-43 |
| FR-BE-04 | WebSocket push event versioned                        | Auth + origin allow-list; chỉ subscribe event thuộc site/camera scope; unauthorized cross-scope bị deny; reconnect + REST reconcile                                                                                                                                   | BAC-44 |
| FR-BE-05 | Auth/RBAC 2 role server-side                          | Guard/Manager allow/deny matrix và site/camera query scope PASS; ID đoán được vẫn không vượt scope; UI hiding không là security control                                                                                                                      | BAC-45 |
| FR-BE-06 | HITL action transactional + audit                     | Full state/role/scope matrix: Guard acknowledge/resolve/dismiss INFO/WARNING + request; Manager thêm confirm/dismiss HIGH/CRITICAL, resolve confirmed severe + approve/decline; allow/deny tests; actor/reason/timestamp/expectedVersion + append-only audit; stale 409 | BAC-46 |
| FR-BE-07 | Incident query/filter/pagination                      | Filter time/camera/type/severity/state; cursor/page metadata                                                                                                                                                                                                             | BAC-47 |
| FR-BE-08 | Heatmap API optional                                  | Chỉ làm khi core xanh; aggregate không lộ PII                                                                                                                                                                                                                        | BAC-48 |

### 9.4. Frontend

| ID       | Requirement                                         | Acceptance criteria                                                                                                                                               | Jira   |
| -------- | --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| FR-FE-01 | React app có routing/layout/API client             | Mock fixture đúng contract; auth routes được bảo vệ                                                                                                        | BAC-49 |
| FR-FE-02 | Camera grid hiển thị source/health                | ≥4 camera, source simulated có badge, detail view                                                                                                               | BAC-50 |
| FR-FE-03 | Realtime alert hiển thị evidence/summary/severity | Không cần refresh; reconnect state; duplicate protection                                                                                                        | BAC-51 |
| FR-FE-04 | Login và role routing                              | Hai tài khoản test; role-specific UI; expired session handled                                                                                                   | BAC-52 |
| FR-FE-05 | HITL UI theo full action matrix                     | Guard và Manager chỉ thấy action hợp lệ theo state/role/scope; resolve severe sau confirm; double-submit prevention; reason validation; clear 403/409 errors | BAC-53 |
| FR-FE-06 | Incident timeline/filter/detail                     | Pagination/filter/detail/action history                                                                                                                           | BAC-54 |
| FR-FE-07 | Heatmap optional Manager-only                       | Time filter + legend accessible                                                                                                                                   | BAC-55 |
| FR-FE-08 | Demo-quality states                                 | Empty/loading/error/offline; responsive; keyboard/focus                                                                                                           | BAC-56 |

### 9.5. Integration & Deployment

| ID        | Requirement                   | Acceptance criteria                                                                                                 | Jira           |
| --------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------- | -------------- |
| FR-INT-01 | API contract versioned        | CV/Agent/BE/FE sign-off; examples + errors                                                                          | BAC-21         |
| FR-INT-02 | Repository/bootstrap baseline | Quy ước branch, cấu trúc repo,`.env.example` và bootstrap local được tài liệu hóa; không chứa secret | BAC-57         |
| FR-INT-03 | Docker Compose local          | Một lệnh start; healthcheck; private DB; env secrets                                                              | BAC-58         |
| FR-INT-04 | Intrusion vertical slice      | Không mock từ video→incident→WS→dashboard                                                                      | BAC-59         |
| FR-INT-05 | Gate 2 E2E                    | 3 core + roles + HITL + timeline PASS                                                                               | BAC-60         |
| FR-INT-06 | Security/privacy hardening    | Secret/RBAC/scope/PII/error/log checklist và negative tests PASS                                                   | BAC-61         |
| FR-INT-07 | Performance baseline          | p50/p95 từng chặng, hardware/config công bố                                                                     | BAC-62         |
| FR-INT-08 | Production deploy             | Fresh deploy, health/log/backup/rollback runbook                                                                    | BAC-63         |
| FR-INT-09 | Demo resilience               | Seed deterministic, backup video, final regression/freeze                                                           | BAC-64, BAC-65 |

---

## 10. API & Data Contract Baseline

## 10.1. EventCandidate nội bộ

```json
{
  "candidateId": "stable-idempotency-id",
  "cameraId": "cam_01",
  "zoneId": "restricted_gate",
  "sourceType": "SIMULATED",
  "eventType": "ZONE_INTRUSION",
  "detectedAt": "2026-07-29T10:15:30Z",
  "firstSeenAt": "2026-07-29T10:15:25Z",
  "lastSeenAt": "2026-07-29T10:15:30Z",
  "confidence": 0.88,
  "trackCount": 1,
  "modelVersion": "model-version",
  "ruleVersion": "rule-version",
  "policyVersion": 1,
  "artifact": {
    "contentType": "image/jpeg",
    "redactionStatus": "COMPLETE"
  }
}
```

### Validation

- camera/zone/policy tồn tại và active.
- `candidateId` idempotent.
- Redaction chưa COMPLETE → không persist/serve artifact.
- Internal endpoint không public; service credential + private network.

## 10.2. Public API — proposed

| Endpoint                                          | Role                 | Purpose                                            |
| ------------------------------------------------- | -------------------- | -------------------------------------------------- |
| `GET /api/v1/events`                            | Guard/Manager scoped | Filter + cursor pagination                         |
| `GET /api/v1/events/{id}`                       | Guard/Manager scoped | Event/evidence/action/enrichment detail            |
| `POST /api/v1/events/{id}/actions`              | Theo action policy   | Acknowledge, confirm, dismiss, resolve, escalation |
| `GET /api/v1/events/{id}/artifacts/{id}`        | Scoped + audited     | Stream redacted evidence,`no-store`              |
| `GET/POST/PATCH /api/v1/cameras`                | Manager              | Camera metadata; không trả credential            |
| `GET/POST/PATCH /api/v1/zones`                  | Manager              | Polygon/schedule/policy                            |
| `GET /api/v1/audit`                             | Manager              | Audit pagination                                   |
| `/health/live`, `/health/ready`, `/metrics` | Internal             | Operations                                         |

### Write invariants

- `Idempotency-Key` cho retry.
- `expectedVersion`/`If-Match`; stale → `409`.
- Reason bắt buộc cho severe dismiss/resolve/escalation decisions.
- State + audit cùng transaction.

## 10.3. WebSocket

Event types:

- `event.created`
- `event.updated`
- `camera.health.changed`
- `review.overdue`

Mỗi message có `eventId`, `eventVersion`, `emittedAt`, `requestId`. Version gap/reconnect → REST reconcile.

## 10.4. Minimal entities

- `Camera`
- `Zone`
- `EventPolicy`
- `SecurityEvent`
- `EventArtifact`
- `EventAction` — append-only
- `AuditLog`
- `LLMEnrichment`

Không lưu raw video trong PostgreSQL; camera credential dùng secret reference.

---

## 11. Non-functional Requirements

### 11.1. Proposed pilot targets — khóa sau BAC-22/BAC-62

| ID     | Dimension          | Proposed requirement                                             | Verification               |
| ------ | ------------------ | ---------------------------------------------------------------- | -------------------------- |
| NFR-01 | Capacity           | Tối đa 4 streams, 720p, sampled 2–5 FPS trên target hardware | Recorded fixture load test |
| NFR-02 | Detection latency  | p95 <5s, p99 <10s từ temporal rule eligibility tới persist     | Worker/API timestamps      |
| NFR-03 | Realtime           | p95 DB commit→connected browser <2s                             | Server/browser telemetry   |
| NFR-04 | API                | p95 read <300ms; write <500ms, 10k events/5 users                | k6/Locust                  |
| NFR-05 | LLM resilience     | Timeout ≤15s; provider failure không block event/HITL          | Fault tests                |
| NFR-06 | Camera health      | HEALTHY <15s; DEGRADED 15–60s; OFFLINE >60s frame age           | Heartbeat tests            |
| NFR-07 | Pilot availability | Proposed 99.0%, exclude camera/announced maintenance             | Synthetic probes           |
| NFR-08 | Recovery           | Proposed RTO ≤4h, RPO ≤24h sau restore drill                   | Backup/restore test        |
| NFR-09 | Testability        | ≥80% coverage deterministic domain logic                        | Coverage report            |
| NFR-10 | Accessibility      | Keyboard/focus/contrast and responsive key breakpoints           | Automated + manual test    |

### 11.2. Non-negotiable release invariants

Các điều kiện sau **không phải Proposed** và không được hạ ngưỡng qua BAC-22/BAC-62:

- Zero persisted/served artifact khi redaction chưa `COMPLETE` hoặc thất bại.
- 100% human security decisions có append-only action/audit; zero auto-confirm/auto-approve.
- Zero cross-site/cross-camera unauthorized REST, artifact hoặc WebSocket access trong negative tests.
- State transition và audit của HITL commit atomically; không update/delete lịch sử quyết định.

Không quảng bá các pilot target là production SLA hoặc accuracy ngoài test environment.

---

## 12. Data, Privacy & Security

## 12.1. Data minimization

- Raw frame tồn tại tạm trong worker memory; không ghi DB/log/browser/LLM.
- Evidence là artifact đã blur; không public URL dài hạn.
- LLM chỉ nhận metadata kiểm soát, không raw/blurred image trong MVP.
- Không identity/face embedding/age/gender/ethnicity/intent inference.

## 12.2. Proposed retention — cần legal/owner approval

| Data                    | Proposed retention |
| ----------------------- | -----------------: |
| Redacted evidence       |            7 ngày |
| Event/incident metadata |           90 ngày |
| Audit                   |          365 ngày |

Scheduled deletion phải quan sát được và test được.

## 12.3. Auth/RBAC

- Ưu tiên OIDC hiện có; không dựng IdP phức tạp.
- Nếu demo local auth: Argon2id, short-lived token/session, rate limit login; không gọi là production auth.
- RBAC enforce ở service/query layer; mỗi user có site/camera scope, áp dụng nhất quán cho list/detail/artifact/action/audit.
- Không tin `siteId`/`cameraId` từ client nếu ngoài claims/membership; ID đoán được phải trả `403` hoặc `404` theo policy.
- WebSocket authenticate khi connect/subscribe, kiểm tra scope cho từng event và đóng kết nối/token hết hạn; CORS/WS origins allow-list.

## 12.4. RTSP/SSRF safety

- Chỉ `rtsp/rtsps` và allow-listed camera networks.
- Credential nằm trong secrets; mask khỏi logs/API/UI.
- CV worker non-root, hạn chế network/filesystem.
- API không cần quyền tới camera VLAN.

## 12.5. Web security baseline

- TLS, security headers, CSP phù hợp.
- Postgres private network.
- Schema/body validation, rate limit write endpoints.
- Parameterized query/ORM.
- Error không lộ stack, credential, model path hoặc DB schema.
- Dependency/image/secret scanning trong CI khi repo được tạo.

---

## 13. Failure & Fallback Requirements

| Failure                 | Required behavior                                  | Forbidden behavior                     |
| ----------------------- | -------------------------------------------------- | -------------------------------------- |
| Camera stale/disconnect | Retry bounded, health degraded/offline, UI visible | Replay stale frame như live           |
| YOLO/tracker crash      | Restart, metric/log, cooldown/dedupe               | Suy diễn event từ old state          |
| API/DB unavailable      | Coverage degraded visible, monitoring alert        | Tuyên bố zero-loss/normal monitoring |
| Artifact/disk issue     | Metadata may persist; evidence unavailable         | Lưu raw/unblurred fallback            |
| Face blur fail          | Privacy-closed: drop artifact                      | Serve image chưa blur                 |
| LLM fail                | Structured/template fallback                       | Delay/drop Event hoặc HITL            |
| WebSocket fail          | Reconnect + REST reconcile                         | Coi push là đã được đọc        |
| Review overdue          | Mark overdue prominently                           | Auto-escalate                          |
| Config invalid          | Atomic reject, keep previous version               | Partial policy apply                   |

MVP không cam kết durable encrypted worker spool; backend outage có thể gây detection coverage gap và phải hiển thị minh bạch.

---

## 14. Analytics, Metrics & Evaluation

## 14.1. Product/operations metrics

- Events/camera/hour theo type/severity.
- Candidate→confirmed/dismissed rate.
- False-alert feedback rate.
- Time-to-alert, time-to-acknowledge, time-to-review/resolve.
- Pending/overdue review count.
- Camera uptime/frame age/reconnect count.
- LLM valid-output/fallback/timeout/cost estimate.
- Redaction failure và denied artifact access.

## 14.2. CV evaluation protocol

- Calibration/dev set tách hold-out set.
- Đánh giá theo **event**, không frame.
- Bao gồm day/night, occlusion và hard negatives nếu dataset cho phép.
- Mọi metric kèm dataset version, sample size, resolution/FPS và hardware.

## 14.3. Proposed evaluation floor — khóa ở BAC-22

| Metric                             |                                  Proposed |
| ---------------------------------- | ----------------------------------------: |
| Recall mỗi core event             |                  ≥5/6 positive scenarios |
| Candidate precision toàn hold-out |                                     ≥75% |
| False candidates nominal stream    |                           ≤2/camera-hour |
| Event eligibility→browser p95     |                                       <5s |
| Soak                               | 45 phút không crash/mất accepted event |

Privacy, HITL audit, zero auto-approval và authorization scope là release invariants tại §11.2, không phải metric Proposed.

Abandoned object phải bật và PASS Gate 2 E2E trên test clip để đáp ứng P0. Sau đó có thể feature-flag theo từng camera trong pilot nếu policy/evaluation chưa phù hợp, với quyết định của PM + CV owner được ghi trong decision log.

---

## 15. Testing Strategy

| Test type   | Scope                                                                                                                                                            | Exit evidence                    |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- |
| Unit        | CV rules, severity policy, state transitions, RBAC, validation, UI state                                                                                         | Coverage report; core cases PASS |
| Contract    | Candidate/API/WS/React schemas                                                                                                                                   | Versioned fixtures + tests       |
| Integration | API+DB, migration, idempotency, audit, artifact gate, WS                                                                                                         | CI/local report                  |
| Agent eval  | Schema, factuality vs metadata, fallback, no state mutation                                                                                                      | Eval cases/report                |
| E2E         | 3 core bật trên test clips; full state/role/scope action matrix cho Guard/Manager, gồm resolve confirmed severe và denied transitions; LLM outage; reconnect | BAC-59, BAC-60 PASS              |
| Security    | RBAC bypass, guessed ID, cross-site/camera REST/artifact/WS deny, expired token, malformed input, secret/dependency scan                                         | No Critical/High open            |
| Privacy     | Raw sentinel absent, failed blur blocks artifact, retention approval + scheduled-deletion test, access audit                                                     | Privacy test report              |
| Resilience  | Camera/API/DB/WS/LLM/disk failures                                                                                                                               | Expected degraded behavior       |
| Deploy/ops  | Fresh deploy, migration, health, backup/restore/rollback                                                                                                         | BAC-63 PASS                      |
| UX/a11y     | Keyboard, focus, contrast, responsive, reduced motion                                                                                                            | BAC-56 checklist                 |

---

## 16. Release & Rollout

### Phase 0 — Gate 1

- Chốt PRD, dataset, architecture, contract, metric protocol.

### Phase 1 — Vertical slice

- Intrusion end-to-end trên simulated/approved video.

### Phase 2 — Gate 2

- 3 core events + roles + HITL + incident timeline.

### Phase 3 — Pilot deployment

- Docker target, health/log/backup, security/privacy baseline.

### Phase 4 — Demo release

- Deterministic data, regression, rehearsal, freeze.

### Go/No-Go

**No-Go** nếu:

- HITL có thể bypass hoặc human security decision không có append-only audit.
- Evidence chưa blur có thể persist/serve.
- Cross-site/cross-camera REST, artifact hoặc WebSocket access có thể vượt authorization scope.
- Retention chưa được owner phê duyệt trước pilot hoặc scheduled-deletion test không PASS.
- Secret bị lộ.
- Fresh deploy không tái lập được.
- 3 core event/incident pipeline, gồm abandoned object đang bật trên test clip, không chạy.
- Có Critical/High data-loss/security issue không có disposition.

---

## 17. Dependencies & Assumptions

| Dependency                 | Required by      | Owner         | Fallback                          |
| -------------------------- | ---------------- | ------------- | --------------------------------- |
| Approved video/dataset     | Gate 1           | Bách + PM    | Simulated/licensed clips          |
| GPU/target hardware        | Week 2           | Hưng + Bách | 1 stream, lower FPS/resolution    |
| LLM endpoint/quota         | Agent enrichment | Tâm          | Deterministic templates           |
| Deploy host/domain/TLS     | Week 4           | Hưng         | Local/private Docker host         |
| Mentor/acceptance owner    | Gates            | Tâm          | Published baseline + decision log |
| Privacy/retention approval | Pilot            | PM/owner      | Demo-only minimal retention       |

---

## 18. Risks

| Risk               | Impact   | Mitigation                             | Scope response                             | Owner         |
| ------------------ | -------- | -------------------------------------- | ------------------------------------------ | ------------- |
| Dataset gap        | H        | Audit/versioned manifest               | Keep fall stretch; use approved simulation | Bách         |
| Tracking/FPR       | H        | ROI/dwell/proximity + hard negatives   | Conservative candidate/HITL                | Bách         |
| Backend bottleneck | H        | Contract-first + fixtures              | Cut analytics/heatmap                      | Hưng + PM    |
| PM+AI overload     | H        | Timebox, LLM off critical path         | Template fallback                          | Tâm          |
| LLM unreliability  | H        | Schema/timeout/no-tools                | Disable enrichment                         | Tâm          |
| Privacy exposure   | Critical | Face blur/RBAC/minimization            | Drop artifact; no public deploy            | Bách + Hưng |
| HITL bypass        | Critical | Backend state machine + negative tests | Block release                              | Tâm + Hưng  |
| Deploy instability | H        | Docker/health/rollback drill           | Single private host                        | Hưng         |
| Scope creep        | H        | MoSCoW + change budget                 | Cut P1/stretch                             | Tâm          |

---

## 19. Traceability — PRD → Jira

| Requirement group                            | Jira                                                                   |
| -------------------------------------------- | ---------------------------------------------------------------------- |
| Problem/personas/discovery                   | BAC-15→22                                                             |
| CV core/eval/privacy                         | BAC-23→32                                                             |
| Agent/enrichment/HITL/memory                 | BAC-33→40                                                             |
| Backend/data/RBAC/HITL/timeline              | BAC-41→48                                                             |
| Frontend/dashboard/HITL/timeline             | BAC-49→56                                                             |
| Repository/Docker/integration/deploy/release | BAC-57, BAC-58, BAC-59, BAC-60, BAC-61, BAC-62, BAC-63, BAC-64, BAC-65 |
| Gate management/demo/docs                    | BAC-1, BAC-9, BAC-11, BAC-13, BAC-14                                   |

Chi tiết issue/owner/due date được quản lý trong Jira BAC; PRD là source cho yêu cầu và acceptance, Jira là source cho execution/status.

---

## 20. Definition of Ready

Một Story đủ Ready khi:

- Có requirement/acceptance rõ, owner và due date.
- Input/output schema hoặc fixture sẵn nếu cross-workstream.
- Dependency/blocker có owner.
- Data/permission/hardware cần thiết đã sẵn hoặc có fallback.
- Test/evaluation approach xác định.
- Security/privacy impact đã được ghi.
- Scope là P0/P1/stretch và phù hợp Gate.

## 21. Definition of Done

Một Story chỉ Done khi:

- Acceptance criteria PASS với evidence.
- Tests phù hợp đã chạy; không có failure bị che giấu.
- Error/fallback behavior được xử lý.
- Input/output được validate.
- Không hardcode secret; không lộ PII/raw evidence trái policy.
- Observability/logging đủ để chẩn đoán.
- API/schema/docs được cập nhật nếu thay đổi contract.
- Code review hoàn tất khi có code.
- Jira có link PR/commit/test/demo/doc.

### Feature Done

Ngoài Story DoD:

- Vertical slice/integration test PASS.
- Role/HITL/privacy negative cases PASS.
- Performance/eval được đo trên baseline công bố.
- Known limitations được ghi.

### Release Done

- Fresh deploy + migration PASS.
- Health/log/backup/rollback kiểm tra.
- E2E regression PASS.
- No Critical/High unresolved.
- Demo fallback và runbook sẵn sàng.

---

## 22. Open Questions

| ID    | Question                                                                                  | Owner         |                                          Deadline |
| ----- | ----------------------------------------------------------------------------------------- | ------------- | ------------------------------------------------: |
| OQ-01 | Hardware/GPU, stream count, resolution/FPS target?                                        | Hưng + Bách |                                            Gate 1 |
| OQ-02 | LLM provider/model/quota/budget và data processing terms?                                | Tâm          |                                            Gate 1 |
| OQ-03 | Ngưỡng zone/dwell/crowd/stationary theo user policy?                                    | Tâm + Mentor |                                            BAC-22 |
| OQ-04 | Evidence storage và retention được ai phê duyệt?                                    | PM + Hưng    | Trước pilot; chưa phê duyệt thì No-Go pilot |
| OQ-05 | Auth dùng OIDC hay local demo accounts?                                                  | Hưng + PM    |                                           Tuần 2 |
| OQ-06 | Dashboard private LAN/VPN hay public Internet?                                            | Hưng         |                                   Trước Tuần 4 |
| OQ-07 | Gate 2 metric floor có được Mentor chấp thuận?                                      | Tâm          |                                          Gate 1/2 |
| OQ-08 | Policy nào cho phép feature-flag abandoned object theo camera sau khi đã PASS Gate 2? | Bách + PM    |                                     Trước pilot |
| OQ-09 | Té ngã có đủ dataset/pose model để shadow eval?                                    | Bách         |                                             14/08 |

---

## 23. Approval

| Role                    | Name                | Decision                         | Date       |
| ----------------------- | ------------------- | -------------------------------- | ---------- |
| Product/PM              | Phạm Văn Tâm     | `[Proposed/Approved]`          | `[date]` |
| CV Owner                | Trần Đăng Bách  | `[Reviewed]`                   | `[date]` |
| Backend/DevOps Owner    | Ngô Tuấn Hưng    | `[Reviewed]`                   | `[date]` |
| Frontend Owner          | Nguyễn Ngọc Hiệp | `[Reviewed]`                   | `[date]` |
| Mentor/Acceptance Owner | `[Name]`          | `[Approved/Changes requested]` | `[date]` |

---

_Last updated: 28/07/2026 · PRD owner: Phạm Văn Tâm_
