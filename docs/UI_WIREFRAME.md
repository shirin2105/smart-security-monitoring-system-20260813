# UI_WIREFRAME — Wireframe & Luồng UX cho Web/PWA vận hành

**Phiên bản:** v1  
**Mục tiêu:** Định nghĩa information architecture, layout logic, state và interaction; không áp đặt visual branding cụ thể.

---

## 1. Nguyên tắc UX

1. Incident quan trọng hơn decoration.
2. Severity không chỉ biểu diễn bằng màu.
3. Camera grid là context; incident queue là action surface.
4. Protected action phải tạo “friction đúng chỗ”.
5. UI không tự authoritative state.
6. Realtime disconnect phải visible.
7. Evidence privacy được phản ánh trong UX.
8. Desktop-first responsive PWA; không xây native mobile riêng.

## 2. Kiến trúc thông tin

```text
/login
/dashboard
  ├─ camera grid
  ├─ incident queue
  └─ system/realtime status
/incidents/:id
  ├─ evidence
  ├─ timeline
  ├─ assessment
  ├─ acknowledge
  └─ approval (nếu có quyền)
/approvals
/audit               [SECURITY_MANAGER]
```

Route chính xác có thể thay đổi; information structure giữ nguyên.

## 3. Khung giao diện chung

```text
┌──────────────────────────────────────────────────────────────────────┐
│ AI CAMERA SECURITY      [Realtime ●]       User: Guard A      [⋮]   │
├───────────────┬──────────────────────────────────────────────────────┤
│ Navigation    │ Main content                                         │
│               │                                                      │
│ Dashboard     │                                                      │
│ Incidents     │                                                      │
│ Approvals*    │                                                      │
│ Audit*        │                                                      │
│               │                                                      │
│ * manager     │                                                      │
└───────────────┴──────────────────────────────────────────────────────┘
```

Responsive nhỏ hơn có thể chuyển navigation thành drawer.

## 4. Login

```text
┌──────────────────────────────────────────┐
│          AI Camera Security              │
│                                          │
│  Email / Username                        │
│  ┌────────────────────────────────────┐  │
│  │                                    │  │
│  └────────────────────────────────────┘  │
│                                          │
│  Password                                │
│  ┌────────────────────────────────────┐  │
│  │ •••••••••••                        │  │
│  └────────────────────────────────────┘  │
│                                          │
│  [ Đăng nhập ]                           │
│                                          │
│  Error area: thông báo an toàn,          │
│  không expose stack trace                │
└──────────────────────────────────────────┘
```

### Trạng thái
- idle;
- submitting;
- invalid credentials;
- backend unavailable;
- session expired.

## 5. Dashboard

Bố cục desktop đề xuất:

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Header: Realtime ● | 6 camera | 2 incidents mở                            │
├───────────────────────────────────────────┬────────────────────────────────┤
│ CAMERA GRID                               │ INCIDENT QUEUE                  │
│                                           │                                │
│ ┌──────────────┐ ┌──────────────┐         │ [HIGH] Intrusion              │
│ │ CAM-01       │ │ CAM-02       │         │ CAM-03 / Zone A               │
│ │ ONLINE       │ │ DEGRADED     │         │ 20:14:03 • OPEN              │
│ │ [stream]     │ │ [stream]     │         │ [Xem chi tiết]                │
│ └──────────────┘ └──────────────┘         │ ───────────────────────────── │
│                                           │ [MED] Crowd                   │
│ ┌──────────────┐ ┌──────────────┐         │ CAM-01 / Lobby                │
│ │ CAM-03       │ │ CAM-04       │         │ 20:13:10 • OPEN              │
│ │ ONLINE       │ │ OFFLINE      │         │ [Xem chi tiết]                │
│ │ [stream]     │ │ no signal    │         │                                │
│ └──────────────┘ └──────────────┘         │                                │
└───────────────────────────────────────────┴────────────────────────────────┘
```

### Camera card

Hiển thị:

- display name;
- `ONLINE|DEGRADED|OFFLINE`;
- timestamp last update;
- optional event badge.

Không hiển thị:

- RTSP URL;
- credential;
- internal secret.

### Incident card

Hiển thị:

- severity text + icon;
- event type label;
- camera/zone;
- elapsed/start time;
- status;
- unread/new indicator;
- CTA xem detail.

Không tạo card mới nếu nhận duplicate message cùng `incident_id`.

## 6. Trạng thái realtime

### Đã kết nối

```text
Realtime ● Đã kết nối
```

### Đang kết nối lại

```text
Realtime ◌ Đang kết nối lại...
Dữ liệu incident hiện tại vẫn có thể được tải từ server.
```

### Mất kết nối

```text
⚠ Mất kết nối realtime
[Thử kết nối lại]   [Tải lại incident]
```

UI không được im lặng khi socket mất.

## 7. Incident detail

```text
┌────────────────────────────────────────────────────────────────────────┐
│ ← Incidents      [HIGH] Xâm nhập vùng cấm          Status: OPEN       │
│ CAM-03 • Restricted Zone A • 20:14:03                                │
├─────────────────────────────────┬──────────────────────────────────────┤
│ EVIDENCE                        │ INCIDENT                             │
│                                 │ Event: restricted_zone_intrusion     │
│ ┌─────────────────────────────┐ │ Confidence: 0.86                    │
│ │                             │ │ Severity source: baseline_rule      │
│ │       KEYFRAME              │ │ Started: ...                        │
│ │                             │ │ Updated: ...                        │
│ └─────────────────────────────┘ │                                      │
│ [Evidence access protected]     │ [ Acknowledge ]                      │
├─────────────────────────────────┴──────────────────────────────────────┤
│ AGENT ASSESSMENT (nếu có)                                              │
│ Severity: HIGH       Confidence: 0.78                                  │
│ Reason: ...                                                            │
│ Recommended action: request_guard_verification                         │
│ Model/Prompt version: accessible in technical/audit metadata           │
├────────────────────────────────────────────────────────────────────────┤
│ TIMELINE                                                                │
│ 20:14:03 Event opened                                                   │
│ 20:14:04 Incident persisted                                             │
│ 20:14:05 Agent assessment completed                                     │
│ 20:14:08 Guard acknowledged                                             │
└────────────────────────────────────────────────────────────────────────┘
```

## 8. Protected approval UX

### Approval requested

```text
┌──────────────────────────────────────────────────────────────┐
│ ⚠ YÊU CẦU XÁC NHẬN HÀNH ĐỘNG NHẠY CẢM                      │
│                                                              │
│ Incident: inc-...                                            │
│ Requested action: trigger_alarm                              │
│ Severity: CRITICAL                                           │
│                                                              │
│ AI recommendation không tự động thực thi hành động này.      │
│ Cần xác nhận của SECURITY_MANAGER.                           │
│                                                              │
│ [Từ chối]                            [Xác nhận hành động]     │
└──────────────────────────────────────────────────────────────┘
```

### Hành vi xác nhận

Khi bấm approve:

1. button -> loading;
2. send request;
3. chỉ khi server trả `APPROVED` mới show success;
4. nếu stale/expired => show authoritative status;
5. retry không execute lại action.

Không dùng optimistic “Đã báo động” trước server confirmation.

## 9. Guard vs Manager

### `GUARD`

Có thể:

- xem dashboard;
- xem incidents/evidence theo quyền;
- acknowledge;
- thấy approval required state.

Không được:

- manager-only approve protected action nếu policy không cho phép;
- xem manager audit nếu không có quyền.

### `SECURITY_MANAGER`

Có thêm:

- approval queue;
- approve/reject;
- audit view;
- actor/action history.

## 10. Approval queue

```text
┌─────────────────────────────────────────────────────────────────┐
│ Approval Requests                                                │
├─────────────┬────────────┬─────────────┬──────────┬──────────────┤
│ Incident    │ Action     │ Severity    │ Age      │ Status       │
├─────────────┼────────────┼─────────────┼──────────┼──────────────┤
│ inc-101     │ alarm      │ CRITICAL    │ 00:18    │ PENDING      │
│ inc-103     │ gate_lock  │ HIGH        │ 01:04    │ PENDING      │
└─────────────┴────────────┴─────────────┴──────────┴──────────────┘
```

Click row -> detail + evidence + decision controls.

## 11. Audit view

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Audit                                                                   │
│ [Time range] [Actor] [Action] [Result] [Incident]                      │
├──────────┬─────────────┬────────────────────┬──────────┬───────────────┤
│ 20:18:12 │ manager-01  │ approval.approve   │ SUCCESS  │ inc-101       │
│ 20:18:03 │ guard-02    │ incident.ack       │ SUCCESS  │ inc-101       │
│ 20:17:55 │ guard-02    │ approval.approve   │ DENIED   │ inc-101       │
└──────────┴─────────────┴────────────────────┴──────────┴───────────────┘
```

Không render sensitive media trực tiếp trong audit table.

## 12. Trạng thái rỗng/đang tải/lỗi

### Incident queue empty

```text
Không có incident đang mở.
Hệ thống vẫn đang giám sát các camera đã cấu hình.
```

### API loading

Skeleton hoặc explicit loading, không blank screen.

### Permission denied

```text
Bạn không có quyền thực hiện hành động này.
Trạng thái hệ thống không thay đổi.
```

### Evidence unavailable

Phân biệt:

- unauthorized;
- expired/deleted by retention;
- storage temporarily unavailable.

Không dùng một generic “Image failed” cho mọi trường hợp.

## 13. Camera offline UX

```text
┌─────────────────────────┐
│ CAM-04                  │
│ OFFLINE                 │
│ Last frame: 20:05:11    │
│                         │
│ Không có tín hiệu       │
│ Đang thử kết nối lại... │
└─────────────────────────┘
```

Camera offline không làm toàn dashboard unusable.

## 14. Hành vi responsive

### Desktop
Grid + queue side-by-side.

### Tablet
Grid 2 columns; incident queue có thể slide panel.

### Mobile/PWA
Ưu tiên incident queue; camera detail mở theo card. Không cần native app.

## 15. Khả năng tiếp cận / an toàn thao tác

- severity có label text;
- action dangerous có explicit wording;
- focus state rõ;
- keyboard navigation cho incident queue;
- không dùng animation gây mất tập trung;
- time hiển thị timezone operator nhưng server data giữ UTC;
- confirmation action không đặt quá gần cancel theo cách dễ bấm nhầm.

## 16. Đo lường UX

Nếu có telemetry, ưu tiên:

- realtime reconnect count;
- incident received -> opened detail time;
- approval request -> decision duration;
- UI error count;
- evidence access error.

Không thu sensitive content không cần thiết.

## 17. Thiết kế giao diện chưa chốt

Tài liệu này **không tự quyết**:

- brand colors;
- logo;
- font family;
- dark/light theme;
- exact spacing system;
- final icon library.

Các mục này có thể chốt sau mà không thay đổi product flow.
