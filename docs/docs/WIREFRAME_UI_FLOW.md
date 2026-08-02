vi

# Wireframe & UI Flow

> **Gate 1 deliverable** · Team Backpropagation · 29/07/2026

---

## 1. Sitemap / Navigation

| Route                 | Role           | Mô tả                                   |
| --------------------- | -------------- | ----------------------------------------- |
| `/login`            | Public         | Đăng nhập (demo account hoặc OIDC)    |
| `/dashboard`        | Guard, Manager | Grid camera + alert feed realtime         |
| `/alerts`           | Guard, Manager | Alert queue, lọc theo severity/camera    |
| `/events/:id`       | Guard, Manager | Chi tiết sự kiện + HITL actions        |
| `/incidents`        | Guard, Manager | Incident log, filter/pagination           |
| `/audit`            | Manager        | Audit trail, filter theo actor/thời gian |
| `/settings/cameras` | Manager        | Camera/zone/policy config                 |

---

## 2. Key Screens (Text Wireframe)

### A. Login

```text
+----------------------------------+
|                       |
|                                  |
|  Email      [________________]   |
|  Password   [________________]   |
|             [  Đăng nhập  ]      |
|                                  |
|  Sai thông tin → lỗi chung       |
|  (không lộ tài khoản tồn tại)    |
+----------------------------------+
```

### B. Dashboard — màn chính của Guard

```text
+--------------------------------------------------------------------------------+
|    ● LIVE   | Site: Khu A          | guard_01 (Bảo vệ)   [Logout]   |
+--------------------------------------------------------------------------------+
| ALERT FEED (WebSocket)          | CAMERA GRID (2x2)                            |
| --------------------------------|--------------------------------------------- |
| 🔴 HIGH · Cam 02 · Cổng B       |  [Cam 01 LIVE ●]   [Cam 02 LIVE ●]           |
|    Xâm nhập vùng cấm · 10:30:15 |   Sảnh chính       Cổng B                    |
|    [thumbnail đã blur]          |                                              |
|    [Xem chi tiết]               |  [Cam 03 LIVE ●]   [Cam 04 ⚠ DEGRADED]      |
| --------------------------------|   Bãi xe           Kho hàng                  |
| 🟡 WARNING · Cam 01 · Sảnh      |                                              |
|    Tụ tập 6 người · 10:28:00    |  Simulated badge trên mọi stream giả lập     |
|    [Acknowledge] [Xem chi tiết] |                                              |
| --------------------------------|                                              |
| 🔵 INFO · Cam 04                |                                              |
|    Stream degraded · 10:25:40   |                                              |
+--------------------------------------------------------------------------------+
```

- Alert mới nhất trên cùng; mỗi alert gắn severity badge, camera, thời gian, thumbnail.
- Camera offline/degraded hiển thị state, không replay frame cũ như live.

### C. Event Detail — HITL Review (route `/events/:id`)

```text
+--------------------------------------------------------------------------------+
| Sự kiện #evt_12345   🔴 HIGH · Xâm nhập vùng cấm   Trạng thái: PENDING_REVIEW  |
+--------------------------------------------------------------------------------+
| EVIDENCE                          | THÔNG TIN & AI ENRICHMENT                   |
|  +-----------------------------+  |  Camera: Cam 02 — Cổng B                   |
|  | ảnh đã face-blur, bbox đỏ  |  |  Phát hiện: 10:30:05 · cuối: 10:30:15      |
|  | (blur fail → không hiển    |  |  Model: yolo-v8.x · Rule: roi-dwell v3     |
|  |  thị, chỉ metadata)        |  |  Policy v1                                 |
|  +-----------------------------+  |                                             |
|                                   |  Mô tả AI [AI-generated]:                   |
|                                   |  "1 người đứng trong vùng cấm 10 giây."     |
|                                   |  Checklist đề xuất [AI-generated]:          |
|                                   |  ☐ Kiểm tra trực quan ☐ Liên hệ ca trưởng    |
|                                   |  (LLM lỗi → template fallback, không chặn)   |
+--------------------------------------------------------------------------------+
| HÀNH ĐỘNG (theo state/role/scope matrix — nút không hợp lệ bị ẩn/vô hiệu)      |
|                                                                                |
|  GUARD thấy:                                                                   |
|    [Acknowledge] [Request escalation] (HIGH → chỉ request, không confirm)       |
|  MANAGER thấy thêm:                                                            |
|    Reason: [________________________]  (bắt buộc cho dismiss/approve/decline)  |
|    [Confirm] [Dismiss] [Approve escalation] [Decline]                          |
|  Mọi action: double-submit prevention, 403 khi sai scope, 409 khi stale version|
+--------------------------------------------------------------------------------+
| 4. LỊCH SỬ (append-only): actor · action · reason · timestamp                  |
|    10:30:20 guard_01 acknowledged                                              |
|    10:31:02 guard_01 requested escalation "ngoài giờ, vùng cấm"                 |
+--------------------------------------------------------------------------------+
```

### D. Incident Log

```text
+------------------------------------------------------------------+
| Incident Log                              [Filter ▾] [Search __] |
|  Filter: thời gian | camera | loại | severity | trạng thái       |
+------------------------------------------------------------------+
| Thời gian   | Camera | Loại        | Sev   | Trạng thái   | ...  |
| 10:30:15    | Cam 02 | Xâm nhập    | HIGH  | PENDING      | view |
| 09:12:43    | Cam 01 | Tụ tập      | WARN  | RESOLVED     | view |
| 08:01:05    | Cam 03 | Vật bỏ quên | HIGH  | DISMISSED    | view |
+------------------------------------------------------------------+
|                       < 1 2 3 ... >  (cursor pagination)         |
+------------------------------------------------------------------+
```

### E. Empty / Error / Offline states

- **Empty:** chưa có event → minh họa + chữ "Chưa có sự kiện trong khoảng lọc".
- **Loading:** skeleton trên grid + feed.
- **Error:** banner lỗi + nút retry; không màn trắng.
- **WS mất kết nối:** badge "Reconnecting…", feed đánh dấu stale; REST reconcile khi reconnect.

---

## 3. User Flow chính

### Flow A — Sự cố nghiêm trọng được xác nhận

1. CV worker phát hiện intrusion → evidence blur xong → Backend persist Event (HIGH).
2. WebSocket `event.created` → cả Guard và Manager thấy alert (trong scope).
3. Guard mở Event Detail → xem evidence → `Acknowledge` → `Request escalation` kèm reason.
4. Manager mở Event Detail → review AI summary/checklist → `Confirm`.
5. Manager `Approve escalation` kèm reason → trạng thái escalation: `NONE → REQUESTED → APPROVED` (chỉ trong app, không gửi ra ngoài).
6. Manager `Resolve` sau khi xử lý xong.
7. Mọi transition: append-only action + audit, cùng transaction.

```text
Guard:   alert → detail → acknowledge → request escalation
Manager: alert → detail → confirm → approve → resolve
Audit:   actor | action | reason | timestamp  (không sửa/xóa)
```

### Flow B — False positive

1. Guard/Manager xem evidence → `Dismiss` kèm reason.
2. Trạng thái → `DISMISSED`; dữ liệu dismiss dùng để tune eval (không auto-train).

### Flow C — LLM lỗi

1. Event vẫn persist và hiển thị bình thường.
2. AI summary hiển thị template fallback + nhãn "enrichment unavailable".
3. HITL flow không bị chặn.

### Flow D — Mất kết nối

1. Camera stale → badge DEGRADED/OFFLINE, không hiển thị frame cũ như live.
2. WS rớt → reconnect tự động + REST reconcile theo version/cursor.

---

## 4. Ràng buộc UI (từ SPEC/PRD)

- UI chỉ hiển thị; **mọi enforcement ở backend** (role + site/camera scope). Ẩn nút không phải biện pháp bảo mật.
- Không `dangerouslySetInnerHTML` cho nội dung LLM/user.
- Evidence chỉ hiển thị khi redaction COMPLETE; nếu không, chỉ hiển thị metadata + trạng thái.
- Keyboard navigation, focus rõ, độ tương phản đạt, icon + text badge (không phân biệt severity chỉ bằng màu).
- Simulated camera luôn có nhãn `SIMULATED`.
