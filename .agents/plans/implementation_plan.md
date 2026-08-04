# Implementation Plan: Smart Security Monitoring System MVP (Bảo vệ Xem Cam Web)

Xây dựng MVP hệ thống giám sát an ninh thông minh dành cho vai trò **Bảo vệ trực cam**, tích hợp **FastAPI** backend, **PostgreSQL (Docker)**, và **React** frontend với 6 luồng camera giả lập, thông báo thời gian thực qua **WebSocket**, và hạ tầng sẵn sàng để nhóm CV & LLM tích hợp về sau.

## User Review Required

> [!IMPORTANT]
> - **PostgreSQL Docker & Database Architecture**:
>   - Đã cấu hình dịch vụ PostgreSQL trong `docker-compose.yml` chạy trên cổng `5432` với đĩa lưu trữ (volume persistent).
>   - Backend sử dụng **SQLAlchemy 2.0** với các bảng: `users` (đăng nhập/phân quyền), `cameras` (thông tin 6 camera), `incidents` (nhật ký cảnh báo xâm nhập/đám đông), `audit_logs` (thao tác HITL của bảo vệ).
>   - Khi khởi chạy, DB sẽ tự động khởi tạo bảng và seed dữ liệu mẫu (Tài khoản mẫu: `guard`/`guard123`, `manager`/`manager123`, 6 camera mặc định).
>   - Đồng thời hỗ trợ chế độ fallback tự động sang SQLite local nếu chưa chạy Docker để dev/test cực nhanh.
> - **Cấu trúc dự án**: Backend tại `back-end` (dùng `uv`), Frontend tại `front-end` (Vite + React + TypeScript, dùng `nvm`).

## Proposed Changes

### Backend & Database (`back-end` & `src`)

#### [NEW] [pyproject.toml](file:///home/hungdreamer/Desktop/all-in-one/old-stuffs/temp/ProjectBase/python/VIN_AI/P-176/back-end/pyproject.toml)
Cấu hình gói backend với `uv`, bao gồm FastAPI, Uvicorn, WebSockets, SQLAlchemy, Psycopg2-binary / Asyncpg, PyJWT, Passlib/Bcrypt.

#### [NEW] [database.py](file:///home/hungdreamer/Desktop/all-in-one/old-stuffs/temp/ProjectBase/python/VIN_AI/P-176/back-end/app/db/database.py)
Kết nối PostgreSQL database engine, SessionLocal, và hàm seed data ban đầu (người dùng mẫu `guard`, 6 camera khu vực).

#### [NEW] [models.py](file:///home/hungdreamer/Desktop/all-in-one/old-stuffs/temp/ProjectBase/python/VIN_AI/P-176/back-end/app/db/models.py)
SQLAlchemy ORM models:
- `User`: id, username, hashed_password, role (`bao_ve`, `quan_ly`), full_name
- `Camera`: id, name, location, stream_url, status (`online`, `warning`, `offline`)
- `Incident`: id, camera_id, event_type (`xam_nhap`, `dam_dong`), severity (`warning`, `critical`), description, status (`pending`, `acknowledged`, `escalated`), created_at
- `AuditLog`: id, user_id, action, incident_id, timestamp

#### [NEW] [main.py](file:///home/hungdreamer/Desktop/all-in-one/old-stuffs/temp/ProjectBase/python/VIN_AI/P-176/back-end/app/main.py)
Cổng vào ứng dụng FastAPI: Khởi tạo DB, CORS, REST routers, WebSocket endpoint `/ws/alerts`, và Background Event Simulator.

#### [NEW] [auth.py](file:///home/hungdreamer/Desktop/all-in-one/old-stuffs/temp/ProjectBase/python/VIN_AI/P-176/back-end/app/api/auth.py)
API Đăng nhập (`/api/v1/auth/login`) truy vấn user từ Postgres, xác thực mật khẩu bcrypt và trả về JWT token. API `/api/v1/auth/me` lấy thông tin user hiện tại.

#### [NEW] [cameras.py](file:///home/hungdreamer/Desktop/all-in-one/old-stuffs/temp/ProjectBase/python/VIN_AI/P-176/back-end/app/api/cameras.py)
API danh sách 6 camera (`/api/v1/cameras`) lấy từ PostgreSQL DB, bao gồm thông tin vùng và trạng thái.

#### [NEW] [alerts.py](file:///home/hungdreamer/Desktop/all-in-one/old-stuffs/temp/ProjectBase/python/VIN_AI/P-176/back-end/app/api/alerts.py)
API quản lý cảnh báo (`/api/v1/alerts`): Lưu trữ sự cố vào Postgres, xử lý xác nhận (HITL acknowledge) và ghi Audit Log.

#### [NEW] [websocket.py](file:///home/hungdreamer/Desktop/all-in-one/old-stuffs/temp/ProjectBase/python/VIN_AI/P-176/back-end/app/services/websocket.py)
ConnectionManager điều phối WebSocket connections, broadcast tin nhắn cảnh báo realtime đến các bảo vệ đang online.

#### [NEW] [simulator.py](file:///home/hungdreamer/Desktop/all-in-one/old-stuffs/temp/ProjectBase/python/VIN_AI/P-176/back-end/app/services/simulator.py)
Service giả lập phát hiện sự kiện bất thường (Xâm nhập T4, Đám đông T4), tự động ghi nhận vào Postgres và phát qua WebSocket.

---

### Frontend (`front-end`)

#### [NEW] [package.json](file:///home/hungdreamer/Desktop/all-in-one/old-stuffs/temp/ProjectBase/python/VIN_AI/P-176/front-end/package.json)
Cấu hình Vite + React + Lucide Icons + TailwindCSS / Custom Security UI styling.

#### [NEW] [App.tsx](file:///home/hungdreamer/Desktop/all-in-one/old-stuffs/temp/ProjectBase/python/VIN_AI/P-176/front-end/src/App.tsx)
Cấu trúc giao diện chính: Login screen kết nối API `/auth/login` -> Command Center Dashboard.

#### [NEW] [CameraGrid.tsx](file:///home/hungdreamer/Desktop/all-in-one/old-stuffs/temp/ProjectBase/python/VIN_AI/P-176/front-end/src/components/CameraGrid.tsx)
Grid 6 camera (2x3 layout) hiển thị luồng stream giả lập sôi động với canvas HUD overlay, bounding boxes khi có cảnh báo, chế độ phóng to camera.

#### [NEW] [AlertSidebar.tsx](file:///home/hungdreamer/Desktop/all-in-one/old-stuffs/temp/ProjectBase/python/VIN_AI/P-176/front-end/src/components/AlertSidebar.tsx)
Thanh bên danh sách cảnh báo thời gian thực nhận từ WebSocket, hiển thị mức độ nghiêm trọng (Warning/Critical), nút "Xác nhận xử lý" (HITL) & "Chuyển Quản lý".

#### [NEW] [AuditLogModal.tsx](file:///home/hungdreamer/Desktop/all-in-one/old-stuffs/temp/ProjectBase/python/VIN_AI/P-176/front-end/src/components/AuditLogModal.tsx)
Bảng tra cứu lịch sử sự cố và nhật ký thao tác bảo vệ truy vấn trực tiếp từ DB Postgres.

---

### Docker & Environment

#### [MODIFY] [docker-compose.yml](file:///home/hungdreamer/Desktop/all-in-one/old-stuffs/temp/ProjectBase/python/VIN_AI/P-176/docker-compose.yml)
Cấu hình 3 container:
1. `postgres`: PostgreSQL 15, container DB lưu trữ data với volume `postgres_data`.
2. `backend`: FastAPI app chạy bằng Python 3.11.
3. `frontend`: React Web App build & serve.

---

## Verification Plan

### Automated Tests
- Kiểm tra kết nối PostgreSQL DB và khởi tạo bảng.
- Pytest kiểm tra API endpoints: `/health`, `/api/v1/auth/login`, `/api/v1/cameras`, `/api/v1/alerts`.
- Test WebSocket connection và broadcast message script.

### Manual Verification
- Khởi chạy Postgres container: `docker compose up -d postgres` (hoặc SQLite local fallback).
- Khởi chạy Backend bằng `uv` / Uvicorn trên port 8000.
- Khởi chạy Frontend bằng Vite trên port 5173.
- Mở Dashboard trên trình duyệt:
  1. Đăng nhập với tài khoản bảo vệ lưu trong DB (`guard` / `guard123`).
  2. Kiểm tra hiển thị đủ 6 camera grid sôi động.
  3. Kích hoạt/nhận cảnh báo thời gian thực qua WebSocket (Xâm nhập / Đám đông).
  4. Thực hiện nút bấm "Xác nhận xử lý" và xác minh thông tin được lưu vào Postgres & hiển thị trên Audit Log.
