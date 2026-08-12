# Smart Security Monitoring System MVP (Hệ Thống Giám Sát An Ninh Thông Minh)

Mô tả: Hệ thống giám sát an ninh thông minh (Web Application) cung cấp giao diện quản lý camera, theo dõi sự cố an ninh và nhận cảnh báo thời gian thực (Real-time Alerts qua WebSockets).

---

## 🛠️ Công Nghệ Sử Dụng (Tech Stack)

### 1. Front-End
- **Core Framework**: [React 18](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/)
- **Build Tool**: [Vite](https://vitejs.dev/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) + PostCSS + Autoprefixer
- **UI Components & Icons**: [Lucide React](https://lucide.dev/)
- **Web Server (Production/Docker)**: [Nginx](https://www.nginx.com/)

### 2. Back-End
- **Language & Runtime**: Python 3.11+
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
- **Database ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Database Driver**: Psycopg2 (PostgreSQL)
- **Validation & Settings**: [Pydantic v2](https://docs.pydantic.dev/) & Pydantic-Settings
- **Authentication & Security**: PyJWT, Passlib (Bcrypt)
- **Real-time Communication**: WebSockets

### 3. Cơ Sở Dữ Liệu & Hạ Tầng (Database & Infrastructure)
- **Database**: PostgreSQL 15 (Alpine)
- **Containerization & Orchestration**: Docker & Docker Compose

> *Lưu ý: Các phân hệ Computer Vision (CV) và Large Language Model (LLM) do đội ngũ khác phụ trách và phát triển riêng.*

---

## 📁 Cấu Trúc Thư Mục Dự Án (Project Structure)

```text
.
├── back-end/               # FastAPI Backend Service
│   ├── app/                # Mã nguồn backend (API, DB models, Services, WebSockets)
│   ├── Dockerfile          # Dockerfile build backend container
│   └── pyproject.toml      # Khai báo thư viện dependencies backend
├── front-end/              # React TypeScript Frontend Service
│   ├── src/                # Mã nguồn frontend (Components, Pages, Hooks...)
│   ├── Dockerfile          # Multi-stage Dockerfile (Node.js build -> Nginx serving)
│   └── package.json        # Khai báo thư viện dependencies frontend
├── docker-compose.yml      # Cấu hình container orchestration (PostgreSQL + Backend + Frontend)
├── .env.example            # File mẫu cấu hình biến môi trường
└── README.md               # Tài liệu hướng dẫn dự án
```

---

## 🐳 Hướng Dẫn Chạy Dự Án Bằng Docker (Docker Setup Guide)

Yêu cầu tiền đề (Prerequisites):
- Máy tính đã cài đặt **Docker** và **Docker Compose**.

---

### 1. Dành cho người dùng Windows

#### Bước 1: Yêu cầu chuẩn bị
- Cài đặt **Docker Desktop cho Windows** (Khuyến nghị sử dụng WSL 2 Backend).
- Đảm bảo ứng dụng **Docker Desktop** đang chạy (biểu tượng cá voi hiển thị dưới khay hệ thống).

#### Bước 2: Clone dự án & Cấu hình môi trường
Mở **PowerShell**, **Command Prompt (CMD)** hoặc **Git Bash**:
```powershell
# 1. Di chuyển tới thư mục dự án (nếu đã clone)
cd P-176

# 2. Tạo file cấu hình môi trường từ file mẫu
copy .env.example .env
```

#### Bước 3: Build và khởi chạy hệ thống
Chạy lệnh sau để Docker Compose tự động build image và khởi chạy toàn bộ 3 services (PostgreSQL, Backend, Frontend):
```powershell
docker compose up --build -d
```
*(Đối với các bản Docker Desktop cũ hơn, sử dụng lệnh: `docker-compose up --build -d`)*

#### Bước 4: Kiểm tra trạng thái và xem log
- **Kiểm tra các container đang chạy**:
  ```powershell
  docker compose ps
  ```
- **Xem log toàn bộ hệ thống theo thời gian thực**:
  ```powershell
  docker compose logs -f
  ```
- **Xem log riêng biệt của Backend hoặc Frontend**:
  ```powershell
  docker compose logs -f backend
  docker compose logs -f frontend
  ```

#### Bước 5: Dừng hệ thống
Để dừng các container đang chạy:
```powershell
docker compose down
```
*(Nếu muốn xóa toàn bộ dữ liệu PostgreSQL trong volume, thêm cờ `-v`: `docker compose down -v`)*

---

### 2. Dành cho người dùng Linux (Ubuntu / Debian / Fedora...)

#### Bước 1: Yêu cầu chuẩn bị
- Cài đặt **Docker Engine** và **Docker Compose plugin** (`docker-compose-plugin`).
- (Khuyến nghị) Thêm user hiện tại vào group `docker` để chạy lệnh không cần `sudo`:
  ```bash
  sudo usermod -aG docker $USER
  ```
  *(Sau đó đăng xuất và đăng nhập lại hoặc chạy `newgrp docker` để áp dụng).*

#### Bước 2: Clone dự án & Cấu hình môi trường
Mở Terminal:
```bash
# 1. Di chuyển tới thư mục dự án
cd P-176

# 2. Tạo file cấu hình môi trường từ file mẫu
cp .env.example .env
```

#### Bước 3: Build và khởi chạy hệ thống
```bash
docker compose up --build -d
```
*(Nếu chưa phân quyền user group docker, chạy với `sudo`: `sudo docker compose up --build -d`)*

#### Bước 4: Kiểm tra trạng thái và xem log
- **Kiểm tra danh sách container**:
  ```bash
  docker compose ps
  ```
- **Xem log hệ thống**:
  ```bash
  docker compose logs -f
  ```

#### Bước 5: Dừng hệ thống
```bash
docker compose down
```

---

## 🌐 Các Đường Dẫn Truy Cập (Access URLs)

### CV event ingest credential

Before starting the backend, generate a random token with at least 32 bytes using your
deployment secret manager, then set `EVENT_INGEST_TOKEN` to the same value for the CV
producer and backend. Keep the value outside source control; `.env.example` intentionally
leaves it blank, and Docker Compose refuses to start the backend without it.

Sau khi chạy thành công `docker compose up --build -d`, các dịch vụ sẽ sẵn sàng tại các đường dẫn sau:

| Dịch vụ | Địa chỉ / URL | Mô tả |
|---|---|---|
| **Front-End (Web Application)** | [http://localhost:5173](http://localhost:5173) | Giao diện quản lý giám sát an ninh (Nginx) |
| **Back-End REST API** | [http://localhost:8000](http://localhost:8000) | FastAPI Server |
| **Swagger API Documentation** | [http://localhost:8000/docs](http://localhost:8000/docs) | Tài liệu API tương tác tự động |
| **ReDoc API Documentation** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Giao diện xem tài liệu API ReDoc |
| **PostgreSQL Database** | `localhost:5432` | DB: `security_db` \| User: `postgres` \| Pass: `postgres` |

## Demo video → cảnh báo Web

Sau khi backend và frontend đang chạy, đặt cùng một `EVENT_INGEST_TOKEN` không rỗng
cho backend và terminal hiện tại. Lệnh dưới đây dùng DEIMv2 thật, clip mẫu cố định,
kết nối `/ws/alerts` trước khi chạy CV, rồi kiểm tra cùng incident qua WebSocket và REST:

```powershell
$env:EVENT_INGEST_TOKEN = '<same-secret-as-backend>'
python -m app.cv.demo_cli
```

Demo không khởi động hoặc dừng service, không in token, và fail sớm nếu service,
video, source/checkpoint/backbone DEIMv2 hoặc checksum chưa sẵn sàng. Config demo
ép mọi VLM/LLM validator về `disabled`; sau khi backend trả duplicate, runner tiếp tục
quan sát WebSocket trong 2 giây (cấu hình được, không cho phép thấp hơn) để bắt rebroadcast trễ.
Mỗi lần chạy có namespace ngẫu nhiên cho `candidateId`, nên lần chạy mới tạo incident
mới trong khi publish lặp ngay trong cùng lần chạy vẫn dùng đúng ID để kiểm tra idempotency.
CV thật chạy trong process `spawn` riêng (an toàn trên Windows). Timeout sẽ phát tín
hiệu dừng, chờ grace period, rồi terminate và join dứt điểm trước khi báo lỗi; vì vậy
không còn child nào có thể publish cảnh báo sau khi CLI đã trả failure.
