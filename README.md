# Smart Security Monitoring System MVP (Hệ Thống Giám Sát An Ninh Thông Minh)

Mô tả: Hệ thống giám sát an ninh thông minh (Web Application) cung cấp giao diện quản lý camera, theo dõi sự cố an ninh, tự động phân tích và nhận cảnh báo thời gian thực (Real-time Alerts qua WebSockets).

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

### 3. Computer Vision (CV) & LLM Assessment
- **CV Models**: DEIMv2, YOLO (Ultralytics / `yolo26m.pt`), Supervision, ByteTrack / StrongSORT tracking
- **LLM Assessment Service**: Integration với OpenAI API / Hugging Face Router để đánh giá rủi ro sự cố tự động ngầm.

### 4. Cơ Sở Dữ Liệu & Hạ Tầng (Database & Infrastructure)
- **Database**: PostgreSQL 15 (Alpine)
- **Containerization & Orchestration**: Docker & Docker Compose

---

## 📁 Cấu Trúc Thư Mục Dự Án (Project Structure)

```text
.
├── app/                    # Mô-đun Computer Vision Engine & Event Publisher
│   ├── cv/                 # CV Pipeline (Detector, Tracker, Multi-Camera Runner, Demo CLI)
│   ├── services/           # CV Engine Services
│   └── config.py           # Cấu hình cài đặt CV Engine & Ingest URL
├── back-end/               # FastAPI Backend Service & Assessment Worker
│   ├── app/                
│   │   ├── api/            # REST API endpoints & WebSockets (/ws/alerts, /api/v1/events/ingest)
│   │   ├── db/             # Models DB, SQLAlchemy session, Database Seeding
│   │   ├── services/       # Ingest Service, Assessment Worker & Assessment Policy (LLM)
│   │   └── main.py         # Entrypoint ứng dụng FastAPI
│   ├── Dockerfile          # Dockerfile build backend container
│   └── pyproject.toml      # Khai báo thư viện dependencies backend
├── front-end/              # React TypeScript Frontend Service
│   ├── src/                # Mã nguồn frontend (Components, Pages, Hooks, WebSockets)
│   ├── Dockerfile          # Multi-stage Dockerfile (Node.js build -> Nginx serving)
│   └── package.json        # Khai báo thư viện dependencies frontend
├── configs/                # File cấu hình camera (cameras.yaml), CV demo (cv-web-demo.yaml)
├── scripts/                # Scripts tiện ích & khởi chạy (run_cv_loop.ps1, run_mvp.ps1, _pyrun.sh)
├── tests/clips/            # Video clips mẫu dùng cho CV testing & demo
├── docker-compose.yml      # Cấu hình orchestration (PostgreSQL + DB Init + Backend + LLM Worker + Frontend)
├── .env.example            # File mẫu cấu hình biến môi trường
└── README.md               # Tài liệu hướng dẫn dự án
```

---

## 🐳 Hướng Dẫn Chạy Fullstack Bằng Docker (Fullstack Docker Setup Guide)

Hệ thống cung cấp file `docker-compose.yml` để khởi chạy trọn bộ 5 dịch vụ thành phần (Fullstack Stack):

1. `postgres`: Cơ sở dữ liệu PostgreSQL 15 (cổng `5432`).
2. `db-init`: Container tự động tạo bảng DB và khởi tạo dữ liệu mẫu (Seeding) rồi dừng.
3. `backend`: FastAPI REST API Server & WebSockets (cổng `8000`).
4. `assessment-worker`: Service ngầm lắng nghe và đánh giá mức độ rủi ro của sự cố bằng LLM (`app.services.assessment_worker`).
5. `frontend`: Giao diện Web React phục vụ qua Nginx (cổng `5173`).

---

### Bước 1: Yêu cầu chuẩn bị (Prerequisites)

- Máy tính đã cài đặt **Docker Engine** và **Docker Compose** (hoặc **Docker Desktop**).
- Đảm bảo Docker Daemon đang hoạt động.

### Bước 2: Khởi tạo file cấu hình môi trường `.env`

Từ thư mục gốc dự án, sao chép file `.env.example` thành `.env`:

#### Dành cho Windows (PowerShell):
```powershell
copy .env.example .env
```

#### Dành cho Linux / macOS:
```bash
cp .env.example .env
```

> ⚠️ **LƯU Ý QUAN TRỌNG VỀ EVENT_INGEST_TOKEN**:
> Backend yêu cầu token xác thực để nhận sự kiện từ CV Engine. Trong `.env`, mặc định `EVENT_INGEST_TOKEN=dummy` đã được cấu hình sẵn cho Docker Compose. Nếu đổi token trong backend, hãy đảm bảo đặt token tương ứng khi chạy luồng CV.

---

### Bước 3: Build và khởi chạy Fullstack

Chạy lệnh Docker Compose để build image và chạy toàn bộ các dịch vụ dưới dạng ngầm (`-d`):

```bash
docker compose up --build -d
```
*(Đối với hệ thống sử dụng Docker Compose v1 cũ hơn, dùng lệnh: `docker-compose up --build -d`)*

---

### Bước 4: Kiểm tra trạng thái và theo dõi Logs

#### 1. Kiểm tra danh sách các container đang chạy:
```bash
docker compose ps
```
Cột `STATUS` của `postgres`, `backend`, `assessment-worker`, `frontend` cần hiển thị `Up` / `healthy`, riêng `db-init` hiển thị `Exited (0)` là thành công.

#### 2. Xem log của toàn bộ hệ thống theo thời gian thực:
```bash
docker compose logs -f
```

#### 3. Xem log của từng dịch vụ cụ thể:
```bash
# Xem log Backend API
docker compose logs -f backend

# Xem log Assessment Worker (LLM)
docker compose logs -f assessment-worker

# Xem log Frontend Web Application
docker compose logs -f frontend
```

---

### Bước 5: Các Đường Dẫn Truy Cập (Access URLs)

Sau khi khởi chạy Docker thành công, truy cập các dịch vụ tại:

| Dịch Vụ | Đường Dẫn / URL | Mô Tả |
|---|---|---|
| **Front-End Web UI** | [http://localhost:5173](http://localhost:5173) | Giao diện quản lý giám sát an ninh (Nginx) |
| **Back-End REST API** | [http://localhost:8000](http://localhost:8000) | FastAPI Server |
| **Swagger API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Tài liệu API tương tác tự động |
| **ReDoc API Docs** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Giao diện tài liệu API ReDoc |
| **PostgreSQL Database** | `localhost:5432` | DB: `security_db` \| User: `postgres` \| Pass: `postgres` |

- **Tài khoản đăng nhập mặc định (Web UI)**:
  - **Nhân viên bảo vệ (Guard)**: Username `guard` / Password `guard123`
  - **Quản lý (Manager)**: Username `manager` / Password `manager123`

---

### Bước 6: Dừng và Dọn Dẹp Container

Để dừng tất cả các container:
```bash
docker compose down
```

Nếu muốn xóa sạch toàn bộ dữ liệu PostgreSQL trong Docker Volume để khởi tạo lại từ đầu:
```bash
docker compose down -v
```

---

## 📹 Hướng Dẫn Luồng Computer Vision (CV) Thủ Công (Manual CV Workflow)

Phân hệ Computer Vision (CV Engine) chạy độc lập với Backend API. CV Engine thực hiện đọc luồng video (hoặc file clip MP4), chạy mô hình AI nhận diện đối tượng/sự cố (như đồ vật bỏ quên, xâm nhập trái phép...), đóng gói dữ liệu sự kiện (`EventCandidate`) và gửi tới Backend qua HTTP POST ingest boundary `/api/v1/events/ingest`.

```text
[ Video Clip / Stream ] 
          │
          ▼
   [ CV Engine ] ──(HTTP POST + Bearer Token)──► [ Backend API ]
   (Detect & Track)                                      │
                                                         ▼
   [ Frontend UI ] ◄━━━━━(WebSockets /ws/alerts)━━━━━━━  │ (Tạo Incident)
```

---

### 1. Yêu cầu môi trường CV

Chạy CV thủ công trực tiếp trên máy host (ngoài Docker) cần:
1. **Python 3.11+** và môi trường ảo `.venv` đã cài đặt các thư viện trong `requirements.txt`:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate

   pip install -r requirements.txt
   ```
2. **File Checkpoint / Weights Model**:
   - Weights YOLO (`yolo26m.pt` nằm ở thư mục gốc repo) hoặc DEIMv2 checkpoint trong `artifacts/` (nếu dùng DEIMv2).
3. **Video mẫu**: Các file video clip thử nghiệm nằm trong `tests/clips/` (ví dụ: `tests/clips/walking_people.mp4`).

---

### 2. Thiết lập Biến Môi Trường cho CV Engine

Đặt `EVENT_INGEST_TOKEN` khớp với token của Backend API (`dummy` nếu dùng mặc định trong `docker-compose.yml` hoặc token cấu hình trong file `.env`):

#### Trên Windows (PowerShell):
```powershell
$env:EVENT_INGEST_TOKEN = "dummy"
```

#### Trên Linux / macOS (Bash):
```bash
export EVENT_INGEST_TOKEN="dummy"
```

---

### 3. Các Cách Chạy Luồng CV Thủ Công

#### 🔹 Cách 1: Chạy Demo CLI Tự Động Kiểm Tra End-to-End (`app.cv.demo_cli`)

Script `demo_cli` sẽ kết nối tới WebSocket `/ws/alerts` trước, khởi chạy mô hình nhận diện trên clip demo mẫu, đẩy sự kiện về backend và xác nhận WebSocket nhận được cảnh báo mới (`NEW_ALERT`) thời gian thực.

```bash
# Đảm bảo Backend Docker đang chạy tại http://localhost:8000
python -m app.cv.demo_cli --config configs/cv-web-demo.yaml
```

**Kết quả kỳ vọng**:
```text
PASS candidate=cand_... incident=...
```

---

#### 🔹 Cách 2: Chạy Pipeline CV Đơn / Đa Camera (`app.cv.run_pipeline`)

Chạy pipeline quét các camera được cấu hình trong `configs/cameras.yaml` (hoặc camera chỉ định):

```bash
# 1. Chạy tất cả camera trong configs/cameras.yaml
python -m app.cv.run_pipeline

# 2. Chạy camera chỉ định (ví dụ cam_01), giới hạn 400 frames, không lặp lại video
python -m app.cv.run_pipeline --camera cam_01 --max-frames 400 --no-loop

# 3. Chạy chế độ tốc độ tối đa không pacing thời gian thực (--fast)
python -m app.cv.run_pipeline --camera cam_01 --fast
```

---

#### 🔹 Cách 3: Chạy CV Vòng Lặp Liên Tục Để Giả Lập Camera Real-time (`scripts/run_cv_loop.ps1`)

Dành cho môi trường Windows PowerShell, script này sẽ phát lại video clip liên tục theo chu kỳ để gửi dữ liệu cảnh báo đều đặn về giao diện Web:

```powershell
powershell -File scripts/run_cv_loop.ps1 -Clip tests/clips/walking_people.mp4 -Frames 400 -Interval 5
```
- `-Clip`: Đường dẫn tới clip video mẫu.
- `-Frames`: Số frame xử lý mỗi lượt.
- `-Interval`: Thời gian nghỉ (giây) giữa các vòng lặp.

---

#### 🔹 Cách 4: Chạy MVP Local Không Cần Docker (`scripts/run_mvp.ps1`)

Nếu không muốn chạy bằng Docker, bạn có thể tự khởi chạy Backend, Frontend và CV Engine trên máy tính cá nhân bằng script PowerShell:

```powershell
powershell -File scripts/run_mvp.ps1
```
Script sẽ tự động bật FastAPI Backend trên port `8000` và React Frontend trên port `5173`. Sau đó bạn mở terminal thứ 2 để chạy CV script (`python -m app.cv.run_pipeline`).

---

### 4. Khắc Phục Lỗi Thường Gặp Khi Chạy CV (Troubleshooting)

- **Lỗi `401 Unauthorized` hoặc `Ingest token invalid`**:
  - Nguyên nhân: `EVENT_INGEST_TOKEN` của CV Engine không trùng khớp với `EVENT_INGEST_TOKEN` của Backend API.
  - Sửa lỗi: Đặt lại biến môi trường `$env:EVENT_INGEST_TOKEN = "dummy"` (hoặc token bạn đã thiết lập trong `.env` backend).
- **Lỗi `Clip không tồn tại` / `FileNotFoundError`**:
  - Kiểm tra xem file video clip trong `tests/clips/` có tồn tại hay không.
- **Lỗi thiếu file weights YOLO/DEIMv2**:
  - Đảm bảo file `yolo26m.pt` nằm ở gốc thư mục dự án hoặc tải đúng checkpoint DEIMv2 như đã định nghĩa trong `configs/`.
