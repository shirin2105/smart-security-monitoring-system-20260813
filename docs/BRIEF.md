# BRIEF — AI Agent Giám Sát & Cảnh Báo An Ninh Từ Camera AI Khu Đô Thị

**Trạng thái:** Baseline dự án v1  
**Mục đích:** Cung cấp bản tóm tắt 1 nguồn đọc cho team kỹ thuật, PM/TL và người đánh giá.  
**Nguồn chính:** `detai.csv` + các quyết định PM/TL đã chốt trong giai đoạn lập kế hoạch.

---

## 1. Bài toán

Khu đô thị có số lượng camera lớn nhưng nhân sự bảo vệ không thể theo dõi đồng thời tất cả luồng hình ảnh. Các sự cố như xâm nhập khu vực cấm, tụ tập bất thường hoặc vật thể bị bỏ lại có thể bị phát hiện muộn khi chỉ dựa vào việc xem lại camera.

Dự án xây dựng một hệ thống hỗ trợ giám sát chủ động bằng Computer Vision và AI Agent để:

- phát hiện sự kiện bất thường từ camera/video;
- tạo incident có bằng chứng và mức độ;
- thông báo cho người trực theo thời gian gần realtime;
- hỗ trợ đánh giá và đề xuất phản ứng;
- bắt buộc con người xác nhận trước các hành động escalation nhạy cảm;
- lưu vết incident và hành động để phục vụ audit.

## 2. Yêu cầu nguồn từ đề bài

Các yêu cầu sau xuất phát trực tiếp từ đề bài gốc:

- AI Agent giám sát luồng camera.
- Computer Vision phát hiện các sự kiện bất thường.
- Hệ thống có khả năng đánh giá mức độ nghiêm trọng và đề xuất phản ứng.
- Hỗ trợ ghi nhớ ngữ cảnh khu vực để giảm báo động giả.
- Escalation nghiêm trọng như báo động/khóa cổng phải có HITL.
- Hình ảnh khuôn mặt/cư dân là dữ liệu nhạy cảm, cần kiểm soát quyền riêng tư và truy cập.
- Cần kiểm soát false positive và độ trễ cảnh báo realtime.
- Web triển khai có hai vai trò: bảo vệ trực và quản lý an ninh.
- Đầu ra cơ bản cần grid camera mô phỏng, ít nhất 3 loại sự kiện, cảnh báo có ảnh/mô tả, HITL và nhật ký sự cố.

## 3. Quyết định PM/TL đã chốt cho MVP

Các mục dưới đây là **quyết định thực thi của dự án**, không phải nguyên văn yêu cầu nguồn:

### 3.1 Ba sự kiện MVP

1. `restricted_zone_intrusion` — xâm nhập vùng cấm.
2. `crowd_gathering` — tụ tập/đám đông.
3. `abandoned_object` — vật thể bị bỏ lại theo baseline “vật thể phù hợp đứng yên đủ lâu”.

Té ngã (`fall`) không nằm trong MVP bắt buộc 4 tuần.

### 3.2 Operator surface

MVP dùng **React/TypeScript Web/PWA**, không xây native mobile riêng trong 4 tuần.

### 3.3 Kiến trúc trách nhiệm

Luồng chuẩn:

`Camera/Video -> Detection -> Tracking -> Temporal Event Engine -> Incident -> Agent Assessment -> Policy -> HITL -> Alert/Audit -> Operator UI`

Nguyên tắc quan trọng:

- `Detection != Event != Incident != Alert`.
- LLM/VLM không phải primary detector.
- Event Engine deterministic giữ vai trò phát hiện event theo thời gian.
- Agent chỉ đánh giá/enrich incident, không trực tiếp thực thi hành động nhạy cảm.
- Hành động protected phải qua deterministic policy và người có quyền xác nhận.

### 3.4 Thời gian thực thi

Kế hoạch 4 tuần:

- **Tuần 1:** vertical slice intrusion end-to-end.
- **Tuần 2:** hoàn thiện 3 event + baseline metric.
- **Tuần 3:** Agent + Policy + HITL + RBAC/privacy/audit.
- **Tuần 4:** evaluation, load, hardening, deploy, demo.

## 4. Team model

Dự án được tổ chức theo 4 vai trò:

- **CV Lead:** ingest, detection, tracking, event engine, CV evaluation.
- **AI/Agent Lead:** Agent assessment, context, structured output, AI evaluation.
- **Full Stack/Platform Lead:** FastAPI, PostgreSQL, WebSocket, auth/RBAC, incident lifecycle, deploy.
- **Realtime UI Lead:** React/PWA, camera grid, incident queue/detail, HITL UX.

Tên người/Atlassian account không được giả định trong tài liệu này.

## 5. Tech stack mục tiêu

### Được đề bài gợi ý

- YOLOv8/v11 hoặc model tương đương.
- VLM tùy chọn.
- LLM.
- LangGraph.
- OpenCV và luồng video/RTSP mô phỏng.
- Vector DB.
- PostgreSQL.
- FastAPI + WebSocket.
- React.
- Docker, GPU tùy chọn.

### Quyết định MVP

- PostgreSQL là storage chính cho incident/audit.
- Vector DB không phải dependency bắt buộc cho MVP; structured context được ưu tiên nếu đủ.
- Local video là nguồn deterministic cho vertical slice đầu tiên.
- RTSP được tích hợp sau khi local vertical slice ổn định.

## 6. Definition of success

Dự án được coi là đạt MVP khi có bằng chứng tái lập được cho:

- 3 event MVP hoạt động theo event-level semantics;
- incident được persist trước khi realtime notify;
- dashboard nhận incident và hiển thị evidence/status;
- protected escalation không thể bypass HITL;
- 2 vai trò được enforce server-side;
- có event-level precision/recall/F1 và false alerts/camera-hour;
- có p50/p95 latency trên hardware được ghi nhận;
- có test tải 1/2/4 nguồn camera/video;
- không có P0 release blocker.

## 7. P0 release blockers

- rò rỉ dữ liệu nhạy cảm/evidence;
- protected action thực thi không qua HITL;
- incident bị mất âm thầm;
- event/alert storm;
- core service crash trên flow được support.

## 8. Ngoài phạm vi MVP

Trừ khi toàn bộ core gate hoàn thành sớm và có quyết định scope mới:

- multi-camera ReID;
- heatmap;
- face recognition;
- native mobile riêng;
- automatic report nâng cao;
- fall detection;
- advanced semantic memory;
- scale claim “hàng trăm camera” chưa qua benchmark.

## 9. Những điểm chưa được phép tự giả định

Chưa có bằng chứng để chốt:

- model checkpoint YOLO cụ thể;
- tracker cụ thể;
- numeric thresholds cho từng event;
- deployment hardware;
- auth provider;
- evidence storage backend;
- retention duration;
- LLM/VLM provider;
- API base prefix cuối cùng.

Các mục này phải được quyết định bằng implementation evidence/ADR, không điền theo cảm tính.
