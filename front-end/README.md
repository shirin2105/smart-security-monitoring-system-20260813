# Frontend — Dashboard giám sát an ninh

React 18 + TypeScript + Vite + Tailwind. Phụ trách: Nguyễn Ngọc Hiệp (BAC-6, BAC-49→56).

Baseline UI kế thừa từ nhánh `2A202601409_NgoTuanHung` của Hưng, sau đó tái cấu
trúc theo API contract trong PRD §8 và §10.

---

## Chạy nhanh

```bash
cd front-end
npm install
cp .env.example .env

npm run dev      # http://localhost:5173
npm test         # 28 unit + smoke test
npm run build    # tsc strict + vite build
```

### Không cần backend

Đặt `VITE_USE_MOCK=true` trong `.env` để chạy toàn bộ UI trên fixture in-memory.
Mock tự sinh cảnh báo mới mỗi 45 giây, và **enforce đúng luật nghiệp vụ**: kiểm
tra role, bắt buộc lý do, bump version, trả 409 khi `expectedVersion` cũ. Nhờ vậy
các nhánh lỗi 403/409 kiểm chứng được mà không cần chờ backend.

Tài khoản: `guard / guard123` · `manager / manager123`

---

## Kiến trúc

```
src/
  domain/        Domain model + action matrix (không phụ thuộc React)
    types.ts         EventType, Severity, EventState, EscalationState…
    permissions.ts   Full state × role × scope matrix — lõi của BAC-53
  api/           Tầng truy cập dữ liệu
    types.ts         Interface ApiTransport — hợp đồng duy nhất UI biết tới
    adapters.ts      Quy đổi schema backend ↔ domain model PRD
    httpTransport.ts Gọi FastAPI thật
    mock/            Transport in-memory + fixture
  auth/          AuthContext, ProtectedRoute
  realtime/      useAlertStream (WS + reconnect), EventsProvider
  components/    UI theo nhóm: alerts, camera, hitl, incidents, common, layout
  pages/         Một file cho mỗi route
```

**Nguyên tắc:** UI không bao giờ gọi `fetch` trực tiếp và không bao giờ thấy
schema của backend. Mọi quy đổi nằm trong `api/adapters.ts`.

### Vì sao có lớp adapter

Backend hiện tại dùng schema khác PRD:

| PRD §8, §10 | Backend hiện tại |
| --- | --- |
| `ZONE_INTRUSION` / `CROWD_THRESHOLD` / `ABANDONED_OBJECT` | `xam_nhap` / `dam_dong` |
| `INFO` / `WARNING` / `HIGH` / `CRITICAL` | `warning` / `critical` |
| `state` và `escalation` là hai trục tách rời | gộp vào một cột `status` |
| `GUARD` / `MANAGER` | `bao_ve` / `quan_ly` |

`adapters.ts` chấp nhận cả hai dạng, nên khi BAC-21 khóa contract và backend
nâng cấp theo, **chỉ cần sửa một file** — UI chạy tiếp không đổi.

---

## Định tuyến

| Route | Quyền | Ticket |
| --- | --- | --- |
| `/login` | công khai | BAC-52 |
| `/` | đã đăng nhập | BAC-50, BAC-51 |
| `/incidents` | đã đăng nhập | BAC-54 |
| `/incidents/:id` | đã đăng nhập | BAC-53, BAC-54 |
| `/audit` | đã đăng nhập | BAC-54 |
| `/heatmap` | chỉ `MANAGER` | BAC-55 (chưa mở) |

---

## Action matrix (BAC-53)

`domain/permissions.ts` là nguồn duy nhất quyết định người dùng thấy nút nào.

| Vai trò | INFO / WARNING | HIGH / CRITICAL | Escalation |
| --- | --- | --- | --- |
| Bảo vệ | tiếp nhận, kết thúc, bỏ qua | **chỉ xem** + xin ý kiến | tạo yêu cầu |
| Quản lý | như Bảo vệ | xác nhận, bỏ qua, kết thúc sau xác nhận | phê duyệt / từ chối |

Ba bảo đảm ở tầng UI: chỉ hiện action hợp lệ, khóa toàn bộ nút khi đang gửi
(chống double-submit), và hiện thông điệp đọc được cho 403 / 409 / chưa-có-backend.

> **Đây là lớp trình bày, không phải lớp bảo mật.** FR-BE-05 ghi rõ "UI hiding
> không là security control" — backend bắt buộc enforce lại toàn bộ matrix này.

---

## Kiểm thử

```
src/domain/permissions.test.ts   23 test — allow/deny matrix, scope, yêu cầu lý do
src/App.test.tsx                  5 test — mount, điều hướng, chặn route theo role
```

Bộ test matrix phục vụ trực tiếp điều kiện PASS Gate 2: *"full state/role/scope
action matrix được unit/E2E test"*.

---

## Còn phụ thuộc backend

UI đã làm xong theo contract, nhưng các mục sau chỉ chạy đầy đủ ở mock mode cho
tới khi backend bắt kịp:

| Cần từ backend | Ticket | Hiện trạng UI |
| --- | --- | --- |
| Endpoint `confirm` / `resolve` / `dismiss` / approve / decline | BAC-46 | Bấm vào báo "backend chưa hỗ trợ" |
| `expectedVersion` → 409 | BAC-46 | Đã gửi kèm, backend đang bỏ qua |
| Reason lưu vào audit | BAC-46 | Đã gửi kèm, backend đang bỏ qua |
| Filter / pagination phía server | BAC-47 | Đang lọc tạm ở client trong `api/query.ts` |
| `camera_scope` trong payload user | BAC-45 | Scope rỗng = không chặn ở UI |
| WebSocket có xác thực + lọc theo scope | BAC-44 | Đang kết nối không kèm token |
| `ABANDONED_OBJECT` từ CV | BAC-27 | Đã hỗ trợ sẵn, backend chưa sinh ra |
| Ảnh bằng chứng đã che mặt | BAC-28, BAC-29 | Chỉ hiện khi `redactionStatus === COMPLETE` |
| Timestamp kèm múi giờ | BAC-42 | FE tự bù `Z` trong `normalizeTimestamp` |

### Ghi chú: timestamp không có múi giờ

Backend lưu `datetime.now(timezone.utc)` vào cột `DateTime` **không** khai báo
`timezone=True`, nên API trả về chuỗi trần `2026-08-04T16:38:58.580962`.
Trình duyệt hiểu chuỗi không có offset là **giờ địa phương**, làm mọi mốc thời
gian lệch đúng bằng offset của máy — ở Việt Nam là 7 tiếng.

`api/adapters.ts::normalizeTimestamp` bù `Z` vào để đọc đúng là UTC, và giữ
nguyên giá trị đã có offset để không hỏng khi backend sửa sang
`DateTime(timezone=True)`. Cách sửa gốc vẫn nằm ở phía backend.

---

## Ghi chú triển khai

- Địa chỉ backend lấy từ `VITE_API_BASE_URL`, không hardcode. Vite nhúng biến
  vào bundle **lúc build**, nên Dockerfile nhận qua `--build-arg`.
- `nginx.conf` có fallback `try_files … /index.html`. Thiếu file này thì deep
  link kiểu `/incidents/101` sẽ trả 404.
- Giá trị truyền vào `VITE_API_BASE_URL` là địa chỉ **trình duyệt** gọi tới,
  không phải hostname nội bộ của docker network.
