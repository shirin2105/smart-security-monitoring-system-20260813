# BRD — Tài liệu yêu cầu nghiệp vụ

**Sản phẩm:** AI Camera Security Agent  
**Phiên bản:** v1  
**Mục tiêu:** Chuyển bài toán an ninh camera thành yêu cầu nghiệp vụ có thể kiểm thử, trước khi đi vào chi tiết kỹ thuật.

---

## 1. Bối cảnh nghiệp vụ

Một khu đô thị có thể có nhiều camera ở cổng, hành lang, sảnh, bãi xe và khu vực hạn chế. Quy trình giám sát thủ công yêu cầu nhân viên quan sát nhiều màn hình cùng lúc, dẫn đến:

- bỏ sót sự kiện;
- phát hiện muộn;
- phản ứng không đồng nhất;
- khó truy lại ai đã xác nhận/đã xử lý;
- khó đo false alarm và chất lượng vận hành.

Hệ thống cần chuyển mô hình “người xem camera liên tục” thành “hệ thống sàng lọc sự kiện + người xác nhận quyết định quan trọng”.

## 2. Mục tiêu kinh doanh

### BO-01 — Rút ngắn thời gian phát hiện

Hệ thống phải chủ động tạo incident khi phát hiện sự kiện đủ điều kiện thay vì phụ thuộc vào việc nhân viên tình cờ nhìn đúng màn hình.

### BO-02 — Giảm tải giám sát thủ công

Người trực tập trung vào incident queue thay vì xem mọi frame của mọi camera.

### BO-03 — Giảm báo động giả

Sự kiện phải dùng tracking/temporal rules và có khả năng bổ sung context thay vì alert trực tiếp từ một detection đơn lẻ.

### BO-04 — Kiểm soát escalation

Hành động có tác động lớn phải có human approval và audit.

### BO-05 — Tạo bằng chứng vận hành

Incident, thời điểm, evidence, quyết định của người dùng và kết quả phải có khả năng truy xuất.

## 3. Stakeholders

### 3.1 Bảo vệ trực (`GUARD`)

Nhu cầu:

- biết camera nào đang có incident;
- xem ảnh/evidence và mô tả;
- acknowledge incident;
- theo dõi incident còn mở/đã xử lý;
- không bị spam nhiều incident từ một sự kiện vật lý.

### 3.2 Quản lý an ninh (`SECURITY_MANAGER`)

Nhu cầu:

- nhận sự cố quan trọng;
- xem đầy đủ incident/audit;
- approve/reject protected escalation;
- xem ai đã xử lý và khi nào.

### 3.3 Ban quản lý/chủ đầu tư

Nhu cầu:

- biết hệ thống có thực sự giảm bỏ sót/false alarm;
- biết capacity đo được;
- biết privacy và HITL được kiểm soát;
- có báo cáo metric dựa trên test set cố định.

### 3.4 Team vận hành kỹ thuật

Nhu cầu:

- biết camera/service health;
- chẩn đoán source offline, event không sinh, incident không tới UI;
- không lộ camera credentials/secrets trong logs/UI.

## 4. Phạm vi nghiệp vụ MVP

### Trong phạm vi

- 2 role: `GUARD`, `SECURITY_MANAGER`.
- simulated camera grid trên Web/PWA.
- phát hiện 3 event:
  - restricted-zone intrusion;
  - crowd gathering;
  - abandoned object.
- incident queue + incident detail.
- evidence image/keyframe reference.
- severity + mô tả.
- Agent assessment dạng structured output sau khi baseline ổn định.
- HITL cho protected escalation.
- incident log/audit.
- evaluation event-level.
- deployment/demo có thể tái lập.

### Ngoài phạm vi

- nhận diện danh tính cư dân;
- cross-camera person ReID;
- autonomous physical response;
- native mobile app riêng;
- production-scale hundreds-camera guarantee;
- fall detection trong MVP;
- heatmap/auto report là nâng cao.

## 5. Quy trình nghiệp vụ mục tiêu

### 5.1 Phát hiện và tạo incident

1. Camera/video cung cấp frame.
2. CV phát hiện và tracking đối tượng.
3. Temporal Event Engine xác định sự kiện có thực sự đủ điều kiện.
4. Hệ thống tạo hoặc cập nhật một `Incident`.
5. `Incident` được persist.
6. Operator nhận realtime notification.
7. Operator xem evidence/detail.

### 5.2 Đánh giá bằng Agent

1. Incident đã persist được chọn để assessment.
2. Agent nhận bounded metadata/evidence/context.
3. Agent trả structured `AgentAssessment`.
4. Output được schema validate.
5. Deterministic policy quyết định action class.
6. Agent failure không làm mất incident.

### 5.3 Protected escalation

1. Policy đánh dấu action cần approval.
2. Tạo `Approval` trạng thái `PENDING`.
3. Người có quyền xem request.
4. `SECURITY_MANAGER` approve hoặc reject.
5. Server ghi actor/time/result.
6. Chỉ sau approval hợp lệ mới được phép trigger action adapter tương ứng.

## 6. Yêu cầu nghiệp vụ

### BR-001 — Event-to-Incident

Mỗi sự kiện vật lý đang hoạt động phải map tới một logical incident, không phải một incident mỗi frame.

**Tiêu chí nghiệm thu:**
- event kéo dài không tạo uncontrolled duplicate incidents;
- retry input không tạo duplicate incident do backend.

### BR-002 — Incident visibility

Incident đã persist phải xuất hiện trong operator UI gần realtime.

**Tiêu chí nghiệm thu:**
- có thể query lại qua REST;
- WebSocket disconnect không làm mất incident;
- reconnect có reconciliation.

### BR-003 — Evidence

Incident phải có evidence đủ để người trực hiểu tình huống.

**Tiêu chí nghiệm thu:**
- có ít nhất metadata/reference của keyframe;
- evidence access được authorize server-side;
- storage reference không mặc định là public URL.

### BR-004 — Role separation

`GUARD` và `SECURITY_MANAGER` có quyền khác nhau đối với protected approval/audit.

**Tiêu chí nghiệm thu:**
- unauthorized action bị backend reject;
- UI hiding không được coi là security control duy nhất.

### BR-005 — HITL

Protected escalation không được tự động thực thi chỉ vì Agent đề xuất.

**Tiêu chí nghiệm thu:**
- action protected tạo approval;
- Agent setting `requires_human_approval=false` không bypass policy;
- duplicate approval không execute action hai lần.

### BR-006 — Privacy

Dữ liệu camera/evidence phải được xử lý theo principle of minimum necessary access.

**Tiêu chí nghiệm thu:**
- không gửi continuous raw video tới external LLM/VLM;
- không expose RTSP/API secrets ra frontend;
- logs không chứa raw media bytes/secrets;
- retention configurable.

### BR-007 — Auditability

Các quyết định quan trọng phải có audit.

**Tiêu chí nghiệm thu:**
- approval/rejection có actor và timestamp;
- unauthorized protected access/action có record phù hợp;
- incident state source/provenance truy được.

### BR-008 — Resilience

Lỗi của một thành phần không được gây mất sự thật nghiệp vụ ở thành phần khác.

**Tiêu chí nghiệm thu:**
- one camera failure không crash tất cả camera workers;
- Agent outage không xóa incident;
- slow WebSocket client không block persistence.

### BR-009 — Measurable quality

Kết quả phải được đánh giá ở event level.

**Tiêu chí nghiệm thu:**
- precision/recall/F1 theo event type;
- false alerts/camera-hour;
- duplicate event/incident metric;
- latency p50/p95;
- test hardware/version được ghi lại.

## 7. Quy tắc nghiệp vụ

### RULE-01 — Event existence và severity tách nhau

Agent có thể thay đổi/đề xuất severity nhưng không phủ nhận việc deterministic event engine đã tạo event.

### RULE-02 — Policy thắng Agent

Khi Agent recommendation xung đột protected-action policy, policy là authoritative.

### RULE-03 — Persist trước notify

Realtime notify chỉ xảy ra sau khi durable incident write thành công.

### RULE-04 — Không claim scale ngoài số đo

Nếu benchmark chỉ chạy 1/2/4 sources thì chỉ được báo cáo capacity trong phạm vi đo được.

### RULE-05 — Abandoned object MVP

Không cần chứng minh “owner đã rời đi”; baseline là eligible object stationary đủ lâu theo rule cấu hình.

## 8. KPI nghiệp vụ / Chỉ số đánh giá

Các chỉ số cần thu thập:

- event-level precision;
- event-level recall;
- F1;
- miss rate;
- false alerts/camera-hour;
- duplicate incidents/physical event;
- event start delay;
- p50/p95 end-to-end latency;
- supported processing FPS;
- dropped frames;
- Agent schema-valid rate;
- HITL bypass test result.

Numeric pass threshold cuối cùng **chưa được chốt** vì chưa có baseline data/hardware. PM/TL chỉ chốt sau khi có benchmark đầu tiên.

## 9. Rủi ro nghiệp vụ chính

| Rủi ro | Tác động | Kiểm soát |
|---|---|---|
| Alert storm | Người trực mất niềm tin | tracking + temporal + dedupe + metric |
| Missed incident | Sự cố bị bỏ sót | fixed test set + recall/miss rate |
| Privacy leak | Nghiêm trọng | RBAC, protected evidence, retention, bounded Agent input |
| Agent hallucination | Action sai | structured schema + deterministic policy |
| HITL bypass | Critical | server-side approval state machine |
| Scale claim sai | Mất độ tin cậy | đo 1/2/4 sources và ghi hardware |
| CV overload 4 tuần | Trễ critical path | local video first, intrusion vertical slice first |

## 10. Phụ thuộc ở cấp nghiệp vụ

Ưu tiên theo thứ tự:

1. shared contracts/config;
2. video -> detection -> tracking;
3. temporal event engine;
4. incident persistence;
5. realtime UI;
6. fixed evaluation baseline;
7. Agent;
8. policy/HITL/RBAC/audit;
9. final evaluation/release.

Agent không nằm trên critical path tuần 1.

## 11. Các quyết định còn mở

Chỉ được chốt sau khi có evidence:

- threshold numeric cho từng event;
- official demo hardware;
- retention period;
- Agent provider/model;
- auth mechanism;
- evidence storage backend;
- exact go/no-go metric threshold.
