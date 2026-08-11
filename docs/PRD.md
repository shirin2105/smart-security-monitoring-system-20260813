# PRD — Tài liệu yêu cầu sản phẩm

**Sản phẩm:** AI Camera Security Agent  
**Phiên bản:** v1  
**Mục tiêu phiên bản:** MVP 4 tuần  
**Giao diện vận hành chính:** React/TypeScript Web/PWA

---

## 1. Tầm nhìn sản phẩm

Xây dựng một hệ thống operator-centric giúp nhân sự an ninh chuyển từ việc “theo dõi mọi camera” sang “xử lý incident đã được AI/CV sàng lọc”, trong đó:

- CV xác định event theo quy tắc deterministic;
- incident là durable truth;
- Agent hỗ trợ severity/explanation/recommendation;
- policy + HITL kiểm soát protected actions;
- mọi phần quan trọng có thể đánh giá và audit.

## 2. Nguyên tắc sản phẩm

1. **Human remains accountable:** AI hỗ trợ, không tự quyết protected escalation.
2. **Event, không phải frame:** sản phẩm đo và hiển thị sự kiện logic, không spam detection.
3. **Persistence first:** UI realtime không thay thế durable incident.
4. **Explainable enough for operator:** alert cần evidence + mô tả + severity/provenance.
5. **Privacy by default:** evidence và credentials không public.
6. **Measured, not claimed:** chỉ báo cáo chất lượng/capacity đã đo.
7. **MVP trước feature richness:** đúng 3 event, Web/PWA, không native mobile.

## 3. Personas

### P1 — Bảo vệ trực

**Mục tiêu**
- biết incident mới nào cần xem;
- nhanh chóng hiểu camera/zone/event;
- acknowledge hoặc escalates theo quyền.

**Khó khăn hiện tại**
- quá nhiều camera;
- khó biết màn hình nào quan trọng;
- alert spam làm mất tập trung.

### P2 — Quản lý an ninh

**Mục tiêu**
- xử lý protected approval;
- xem incident severity và audit;
- biết ai đã làm gì.

**Khó khăn hiện tại**
- thiếu traceability;
- khó xác định alert nào thực sự quan trọng;
- không muốn automation tự thực thi action lớn.

## 4. MVP scope

### F1 — Camera grid

- Hiển thị tối thiểu grid camera mô phỏng.
- Mỗi camera có status display-safe.
- Có state loading/offline/degraded/reconnecting phù hợp.
- Không expose camera credentials.

### F2 — Restricted-zone intrusion

- Person track đi vào restricted ROI.
- Chỉ mở event khi thỏa dwell/config.
- Boundary jitter không gây storm.
- Một active logical intrusion map tới một incident.

### F3 — Crowd gathering

- Count unique active person tracks.
- Open event khi count >= configurable threshold đủ thời lượng/window.
- One-frame spike không mở crowd event.

### F4 — Abandoned object

- Eligible tracked object stationary đủ thời lượng.
- Không yêu cầu owner recognition.
- Small bbox jitter không reset timer một cách không hợp lý.

### F5 — Incident queue

- Hiển thị incident realtime.
- Tối thiểu: event type, camera, zone, severity, status, timestamp.
- Merge/update theo `incident_id`.
- WebSocket duplicate không tạo row duplicate.

### F6 — Incident detail

- evidence;
- event/incident time;
- camera/zone;
- severity + provenance;
- Agent assessment nếu có;
- acknowledge state;
- approval state nếu protected action.

### F7 — Agent assessment

Chỉ bật sau baseline gate.

Agent trả structured data:

- `event_type`;
- `severity`;
- `confidence`;
- `reason`;
- `recommended_action`;
- `requires_human_approval`.

Invalid schema phải fail safely.

### F8 — HITL approval

- Protected action tạo `Approval=PENDING`.
- `SECURITY_MANAGER` có quyền approve/reject.
- `GUARD` không được server authorize action vượt quyền.
- duplicate decision idempotent.
- audit actor/time/result.

### F9 — Incident log/audit

- Có lịch sử incident.
- Có các action quan trọng.
- Query theo status/event/camera.
- Manager audit view là P0/P1 theo release gate.

## 5. User stories

### US-01

**Là** bảo vệ trực  
**Tôi muốn** nhìn thấy incident mới xuất hiện trong queue  
**Để** tôi không phải quan sát mọi camera liên tục.

**Tiêu chí nghiệm thu**
- incident persist thành công;
- WebSocket gửi event;
- queue cập nhật không reload thủ công;
- reconnect có thể refetch current state.

### US-02

**Là** bảo vệ trực  
**Tôi muốn** xem evidence và camera/zone của incident  
**Để** tôi biết cần phản ứng thế nào.

**Tiêu chí nghiệm thu**
- evidence authorization pass;
- unauthorized evidence request bị reject;
- UI có error state rõ.

### US-03

**Là** quản lý an ninh  
**Tôi muốn** approve/reject yêu cầu báo động/khóa cổng  
**Để** action quan trọng không được AI tự động thực thi.

**Tiêu chí nghiệm thu**
- server verify role;
- approval còn `PENDING`;
- final state durable;
- action không execute hai lần.

### US-04

**Là** PM/TL  
**Tôi muốn** benchmark event-level  
**Để** biết hệ thống tốt lên hay xấu đi khi thêm tracking/Agent/context.

**Tiêu chí nghiệm thu**
- fixed test set versioned;
- metric machine-readable;
- config/model versions recorded.

## 6. Functional requirements

### FR-001 — Camera configuration

Camera source, display name, ROI, thresholds và health không hard-code trong UI.

### FR-002 — Event lifecycle

Event engine cần logical lifecycle tương đương:

`INACTIVE -> CANDIDATE -> OPEN -> UPDATED* -> CLOSED -> COOLDOWN`

### FR-003 — Incident lifecycle

Incident server-side lifecycle tối thiểu tương đương:

`DETECTED -> ASSESSING -> OPEN -> PENDING_APPROVAL -> APPROVED|REJECTED|EXPIRED -> RESOLVED`

Không phải mọi incident đều đi qua mọi state.

### FR-004 — Realtime

Backend publish các resource change quan trọng sau persistence.

WebSocket envelope dùng stable `message_id`, `type`, `sent_at`, `payload`.

### FR-005 — REST

Tối thiểu:

- `GET /health`
- `GET /ready`
- `GET /cameras`
- `GET /incidents`
- `GET /incidents/{incident_id}`
- `POST /incidents/{incident_id}/acknowledge`
- approval approve/reject endpoint tương đương.

URL prefix cuối cùng chưa chốt.

### FR-006 — Evidence privacy

Evidence access server-side authorized.

### FR-007 — Agent fallback

Agent timeout/invalid output không block guard nhìn thấy incident.

### FR-008 — Audit

Approval, unauthorized protected action và actor changes cần audit phù hợp.

## 7. Non-functional requirements

### NFR-001 — Latency

Phải instrument để đo:

- `frame_received_at`
- `detection_finished_at`
- `event_created_at`
- `incident_saved_at`
- `ws_pushed_at`
- `ui_received_at`

Report p50/p95 trên official test hardware.

Numeric target chưa chốt trước baseline.

### NFR-002 — Reliability

- one camera failure isolated;
- WebSocket failure không mất incident;
- Agent failure không corrupt incident;
- duplicate/retry idempotent.

### NFR-003 — Security

- server-side RBAC;
- no secrets in frontend/logs;
- evidence protected;
- protected action approval enforced server-side.

### NFR-004 — Privacy

- no continuous raw video to external LLM/VLM;
- minimum necessary evidence;
- retention configurable;
- face blur là advanced scope, nhưng privacy controls không optional.

### NFR-005 — Observability

Structured logs/metrics có correlation IDs và stage timing phù hợp.

### NFR-006 — Configurability

Không hard-code:

- camera URL;
- ROI;
- model path/device;
- FPS;
- event thresholds;
- retention;
- Agent config;
- DB secrets.

## 8. Yêu cầu UX sản phẩm

- incident queue ưu tiên readability hơn decorative UI;
- severity không chỉ truyền bằng màu, cần text/icon;
- approval button chỉ báo success khi server xác nhận;
- disconnected/reconnecting state phải visible;
- duplicate WS message không tạo duplicate card;
- error state có recovery action.

## 9. Release gates

### G1 — Week 1 intrusion vertical slice

`local video -> detector -> tracker -> intrusion -> incident DB -> WebSocket -> dashboard`

### G2 — 3 events stable

Cả 3 event có temporal/dedupe semantics.

### G3 — Fixed test set + baseline metric

Có result machine-readable.

### G4 — Agent enablement

Chỉ sau baseline review và không có P0 pipeline blocker.

### G5 — HITL/RBAC/audit

Protected-action bypass test pass.

### G6 — Final release

Evaluation + 1/2/4-source load + deploy + demo rehearsal, không open P1 theo plan hiện tại.

## 10. Success metrics

Chỉ số chính:

- event precision/recall/F1;
- false alerts/camera-hour;
- miss rate;
- duplicate incidents;
- p50/p95 latency;
- load 1/2/4 source.

Chỉ số bổ sung:

- Agent schema-valid rate;
- Agent severity agreement trên controlled scenarios;
- unsafe recommendation blocked rate;
- reconnect correctness.

## 11. Ngoài phạm vi

- native mobile;
- face identification;
- cross-camera ReID;
- fall detection MVP;
- heatmap;
- large-scale Kafka/Kubernetes architecture;
- autonomous protected actions;
- unbounded semantic memory.

## 12. Unknowns cần evidence trước khi khóa

| Mục | Trạng thái | Cách chốt |
|---|---|---|
| YOLO model variant | Chưa chốt | speed/quality trên hardware thật |
| Tracker | Chưa chốt | ID continuity + runtime |
| Numeric event thresholds | Chưa chốt | development clips, sau đó freeze |
| Auth mechanism | Chưa chốt | chọn khi backend auth ticket bắt đầu |
| Agent provider/model | Chưa chốt | sau baseline gate |
| Evidence backend | Chưa chốt | security + deploy simplicity |
| Retention duration | Chưa chốt | product/security decision |
| Go/no-go numeric targets | Chưa chốt | sau baseline metric |
