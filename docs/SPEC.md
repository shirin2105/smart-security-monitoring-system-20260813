# SPEC — Đặc tả hệ thống AI Camera Security Agent

**Phiên bản:** v1  
**Loại tài liệu:** Đặc tả kỹ thuật/hệ thống  
**Nguyên tắc:** Những giá trị chưa có evidence được biểu diễn dưới dạng configurable parameter, không tự điền số giả định.

---

## 1. Các bất biến của hệ thống

1. `Detection != Track != EventCandidate != Incident != Alert`.
2. Event Engine deterministic là primary event detector cho MVP.
3. Agent không được xóa/đảo ngược sự tồn tại của persisted incident.
4. Incident phải persist trước realtime notification.
5. Protected action phải qua deterministic policy + authorized human approval.
6. External LLM/VLM không nhận continuous raw video stream.
7. IDs/timestamps phải explicit; không suy identity chỉ từ timestamp.
8. Cross-camera identity không thuộc MVP.

## 2. Logical pipeline

```text
Video Source
   |
   v
FramePacket
   |
   v
Detector -> Detection[]
   |
   v
Tracker -> Track[]
   |
   v
Temporal Event Engine -> EventCandidate
   |
   v
Incident Service -> PostgreSQL
   |
   +--> WebSocket -> React/PWA
   |
   +--> Agent Assessment (optional, gated)
            |
            v
         Policy
            |
            +--> normal notify/log
            |
            +--> Approval(PENDING) -> HITL -> audited result
```

## 3. Hợp đồng dữ liệu dùng chung

### 3.1 `FramePacket`

```json
{
  "schema_version": "1.0",
  "camera_id": "cam-001",
  "frame_id": "cam-001:12345",
  "captured_at": "2026-08-10T02:00:00.123Z",
  "received_at": "2026-08-10T02:00:00.150Z",
  "source_type": "file|rtsp",
  "frame_ref": "opaque-internal-reference"
}
```

Rules:

- `frame_id` unique trong camera stream;
- `frame_ref` không phải public evidence URL;
- persisted timestamps dùng UTC ISO-8601.

### 3.2 `Detection`

```json
{
  "schema_version": "1.0",
  "camera_id": "cam-001",
  "frame_id": "cam-001:12345",
  "class_id": 0,
  "class_name": "person",
  "confidence": 0.91,
  "bbox_xyxy": [100.0, 80.0, 220.0, 410.0],
  "model_name": "configured-model",
  "model_version": "configured-version",
  "detected_at": "2026-08-10T02:00:00.180Z"
}
```

### 3.3 `Track`

```json
{
  "schema_version": "1.0",
  "camera_id": "cam-001",
  "track_id": "cam-001:t-17",
  "frame_id": "cam-001:12345",
  "class_name": "person",
  "confidence": 0.89,
  "bbox_xyxy": [105.0, 82.0, 225.0, 412.0],
  "first_seen_at": "2026-08-10T01:59:58Z",
  "last_seen_at": "2026-08-10T02:00:00.180Z"
}
```

`track_id` chỉ có guarantee trong một camera.

### 3.4 `EventCandidate`

```json
{
  "schema_version": "1.0",
  "event_id": "evt-uuid",
  "event_type": "restricted_zone_intrusion",
  "camera_id": "cam-001",
  "zone_id": "restricted-A",
  "state": "OPEN",
  "started_at": "2026-08-10T02:00:01Z",
  "updated_at": "2026-08-10T02:00:03Z",
  "ended_at": null,
  "confidence": 0.86,
  "involved_track_ids": ["cam-001:t-17"],
  "evidence_refs": ["evidence-ref-1"],
  "rule_version": "intrusion-v1",
  "attributes": {}
}
```

`event_type` MVP:

- `restricted_zone_intrusion`
- `crowd_gathering`
- `abandoned_object`

`event_id` ổn định trong lifetime của một logical event.

### 3.5 `Incident`

```json
{
  "schema_version": "1.0",
  "incident_id": "inc-uuid",
  "event_id": "evt-uuid",
  "event_type": "restricted_zone_intrusion",
  "camera_id": "cam-001",
  "zone_id": "restricted-A",
  "status": "OPEN",
  "severity": "high",
  "severity_source": "baseline_rule",
  "confidence": 0.86,
  "started_at": "2026-08-10T02:00:01Z",
  "updated_at": "2026-08-10T02:00:03Z",
  "resolved_at": null,
  "evidence_refs": ["evidence-ref-1"]
}
```

Allowed severity:

`low | medium | high | critical`

Suggested status set:

`DETECTED | ASSESSING | OPEN | PENDING_APPROVAL | APPROVED | REJECTED | EXPIRED | RESOLVED`

### 3.6 `AgentAssessment`

```json
{
  "schema_version": "1.0",
  "assessment_id": "assess-uuid",
  "incident_id": "inc-uuid",
  "event_type": "restricted_zone_intrusion",
  "severity": "high",
  "confidence": 0.78,
  "reason": "Mô tả ngắn có cấu trúc",
  "recommended_action": "request_guard_verification",
  "requires_human_approval": true,
  "model_name": "configured-model",
  "model_version": "configured-version",
  "prompt_version": "assessment-v1",
  "created_at": "2026-08-10T02:00:04Z"
}
```

Malformed output => reject assessment, không execute action.

### 3.7 `Approval`

```json
{
  "schema_version": "1.0",
  "approval_id": "apr-uuid",
  "incident_id": "inc-uuid",
  "requested_action": "trigger_alarm",
  "status": "PENDING",
  "requested_at": "2026-08-10T02:00:05Z",
  "decided_at": null,
  "decided_by": null,
  "reason": null
}
```

Approval status:

`PENDING | APPROVED | REJECTED | EXPIRED`

## 4. Ngữ nghĩa chung của Event Engine

Logical event lifecycle:

`INACTIVE -> CANDIDATE -> OPEN -> UPDATED* -> CLOSED -> COOLDOWN`

Các tham số cấu hình chung:

- `min_confidence`
- `min_duration`
- `observation_window`
- `gap_tolerance`
- `close_grace`
- `cooldown`

Tên config cuối cùng có thể khác; semantics phải tương đương.

## 5. Event specification

### 5.1 Restricted-zone intrusion

**Input**
- `Track.class_name=person`
- polygon zone
- membership method
- dwell
- gap tolerance

**Logical key**
`camera_id + zone_id + person_track_id`

**Open**
Person track ở trong restricted zone đủ configured dwell.

**Update**
Cùng track ở cùng zone => update same event.

**Close**
Track outside/missing quá configured grace.

**Trường hợp âm tính**
- đi sát zone nhưng không vào;
- vào ngắn hơn dwell;
- boundary jitter;
- non-person object.

**Unknown cần chốt bằng test**
- membership = center/foot point/overlap;
- dwell seconds;
- hysteresis/grace/cooldown.

### 5.2 Crowd gathering

**Input**
- unique active person tracks
- optional zone
- `crowd_min_people`
- duration/window
- close grace

**Logical key**
`camera_id + zone_id + crowd`

**Open**
Unique person count >= threshold đủ thời lượng/window.

**Không được**
Dùng raw box count của một frame làm event trực tiếp.

**Update attributes**
- current count
- peak count
- bounded involved track IDs
- duration

**Close**
Count dưới close threshold đủ grace.

### 5.3 Abandoned object

MVP definition: eligible object track stationary đủ thời lượng.

**Không yêu cầu**
- owner recognition;
- chứng minh owner đi khỏi scene;
- person-object ReID.

**Các cách xác định đứng yên có thể dùng**
- centroid displacement;
- IoU stability;
- tracker velocity.

Chọn cách đơn giản nhất có thể test/reproduce.

**Logical key**
`camera_id + object_track_id` (+ `zone_id` nếu rule dùng zone)

**Unknown**
- eligible classes;
- motion tolerance;
- duration;
- gap tolerance.

## 6. Incident idempotency

Hai tầng bảo vệ:

1. Event Engine không emit repeated `OPEN` cho same logical event.
2. Incident service upsert/idempotency theo stable `event_id`/event key.

Concurrent duplicate input phải được DB constraint/transaction xử lý phù hợp.

## 7. Hợp đồng REST mục tiêu

Exact `/api/v1` prefix chưa chốt.

### Health

`GET /health`
- liveness.

`GET /ready`
- database và required dependencies sẵn sàng.

### Camera

`GET /cameras`
- display-safe metadata;
- no RTSP credentials.

### Incident

`GET /incidents`
- filter: status, event type, camera;
- pagination;
- optional severity/time.

`GET /incidents/{incident_id}`

`POST /incidents/{incident_id}/acknowledge`

### Approval

Interface tương đương:

`POST /approvals/{approval_id}/approve`

`POST /approvals/{approval_id}/reject`

Server phải authorize role và validate current status.

## 8. Hợp đồng WebSocket mục tiêu

```json
{
  "type": "incident.created",
  "message_id": "msg-uuid",
  "sent_at": "2026-08-10T02:00:05Z",
  "correlation_id": "corr-uuid",
  "payload": {
    "incident_id": "inc-uuid"
  }
}
```

Message types dự kiến:

- `incident.created`
- `incident.updated`
- `incident.resolved`
- `approval.requested`
- `approval.updated`
- `camera.health_changed`

Rules:

- persistence before publish;
- client dedupe bằng `message_id`/resource ID;
- reconnect => REST reconciliation;
- WS không mặc định là durable event history.

## 9. Agent specification

### Input được phép

- persisted incident;
- event/camera/zone metadata;
- bounded evidence;
- bounded structured context.

### Mặc định không được phép

- continuous raw stream;
- secrets;
- arbitrary DB access;
- unrestricted resident history.

### Hành vi output bắt buộc

- structured schema only;
- enum validation;
- prompt/model/version logged;
- timeout/invalid schema => fallback.

### Tập action khuyến nghị

Allowlist-based, ví dụ:

- `log_only`
- `notify_guard`
- `request_guard_verification`
- `request_manager_review`
- `request_alarm`
- `request_gate_lock`

Exact enum phải được shared contract hóa trước implementation.

## 10. Policy + HITL

Baseline invariant:

- `request_alarm` và `request_gate_lock` luôn require approval trong MVP.
- Agent không được override policy.
- unauthorized role reject.
- repeated approve/reject idempotent.
- expired approval không execute.

Protected action adapter có thể là simulation trong demo; phải ghi rõ nếu simulated.

## 11. RBAC/privacy

Roles:

- `GUARD`
- `SECURITY_MANAGER`

Server authorize:

- incident/evidence reads;
- acknowledge;
- approval decision;
- manager audit.

Privacy:

- evidence reference không public by default;
- no raw media in logs;
- no continuous video to external AI;
- retention configurable;
- blur advanced, access control mandatory.

## 12. Các bảng miền mục tiêu trong PostgreSQL

Schema logical tối thiểu:

- `camera`
- `zone`
- `incident`
- `incident_evidence`
- `approval`
- `user`
- `role`
- `audit_log`

Table/column name chính xác sẽ do migration implementation chốt.

Vector DB không required cho MVP baseline.

## 13. Observability

Structured log fields khuyến nghị:

- timestamp
- service/module
- level
- camera_id
- event_id
- incident_id
- correlation_id
- error_code
- duration_ms

Latency checkpoints:

- `frame_received_at`
- `detection_finished_at`
- `event_created_at`
- `incident_saved_at`
- `ws_pushed_at`
- `ui_received_at`

## 14. Hành vi khi lỗi/sự cố

### Camera source failure
- isolate per camera;
- health `ONLINE|DEGRADED|OFFLINE`;
- backoff, không tight loop.

### DB failure
- `/ready` false;
- không report realtime incident success nếu chưa persist.

### WS failure
- incident vẫn ở DB;
- UI recover qua REST.

### Agent timeout
- incident vẫn visible;
- fallback baseline handling.

### Invalid Agent schema
- reject;
- no action.

### Unauthorized approval
- reject + audit.

## 15. Evaluation protocol

Fixed versioned test set.

Per event type:

- TP/FP/FN
- precision
- recall
- F1
- miss rate
- false alerts/camera-hour
- duplicate incidents

Load benchmark:

- 1 source
- 2 sources
- 4 sources

Capture:

- hardware
- model/config
- FPS
- drops
- CPU/GPU
- p50/p95
- errors/restarts

## 16. Ablation

A — detector + simple rules  
B — + tracking + temporal aggregation  
C — + Agent assessment  
D — + context (nếu stable)

C/D không được mô tả là tăng detector recall nếu Agent không tham gia event detection.

## 17. Danh mục cấu hình

Không hard-code:

- DB URL
- camera URLs
- local video path
- ROI polygons
- model name/path/device
- sampling FPS
- detector thresholds
- tracker config
- event thresholds
- evidence retention
- Agent provider/model/timeout
- frontend API/WS URL
- auth secrets

## 18. Các kiểm thử an toàn bắt buộc trước release

- event storm test;
- duplicate EventCandidate test;
- duplicate WS message test;
- WS reconnect + REST reconcile;
- Agent malformed output;
- Agent protected action với `requires_human_approval=false`;
- unauthorized approval;
- duplicate approval click;
- evidence unauthorized access;
- service restart basic smoke;
- negative clip cho từng event.

## 19. Những mục không được giả định

Chưa có repo/source code trong input hiện tại, do đó SPEC **không xác nhận**:

- package/framework version;
- exact folder names đang tồn tại;
- actual DB migration tool;
- actual REST prefix;
- actual model checkpoint;
- actual Docker service names;
- actual ports;
- actual deployment command;
- actual test result.

Khi repository được cung cấp, cập nhật SPEC theo implementation evidence và ghi ADR cho divergence.
