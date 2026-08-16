# Smart Security Monitoring System (Hệ Thống Giám Sát An Ninh Thông Minh)

[![Gate G2](https://img.shields.io/badge/Milestone-Gate%20G2%20MVP-success)](#)
[![Tests](https://img.shields.io/badge/Tests-308%20Passed-brightgreen)](#)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](#)
[![React](https://img.shields.io/badge/React-18.x-61DAFB.svg)](#)
[![LangGraph](https://img.shields.io/badge/AI%20Agent-LangGraph-orange.svg)](#)
[![CV Detector](https://img.shields.io/badge/CV-DEIMv2%20%2B%20ByteTrack-blueviolet.svg)](#)

> **Dự án:** P-176 — Hệ Thống Giám Sát An Ninh Thông Minh (AI Camera Security System)  
> **Mục tiêu Gate G2:** Luồng xử lý hoàn chỉnh end-to-end với mô hình Computer Vision và AI Agent LLM thực tế (không mock), hỗ trợ giám sát thời gian thực và điều phối an ninh có con người kiểm soát (Human-in-the-loop).

---

## 🌟 Tính Năng Cốt Lõi (Core Features)

1. **Phát hiện sự cố an ninh bằng Computer Vision:**
   - Sử dụng mô hình **DEIMv2 (Phase 7A Checkpoint)** và thuật toán bám vết đa đối tượng **ByteTrack**.
   - Tự động nhận diện 3 hành vi an ninh trọng yếu:
     - 🚨 **Xâm nhập vùng cấm (`ZONE_INTRUSION`):** Phát hiện người đi vào khu vực hạn chế hoặc cổng cấm.
     - 👥 **Tụ tập đông người (`CROWD_THRESHOLD`):** Phát hiện số lượng người vượt quá ngưỡng an toàn.
     - 🎒 **Vật thể / Hành lý bỏ quên (`ABANDONED_OBJECT`):** Phát hiện hành lý bị chủ nhân bỏ lại quá thời gian quy định.
2. **AI Agent phân tích & cố vấn an ninh (LangGraph + Real LLM):**
   - Đóng gói đồ thị suy luận **LangGraph** (StateGraph) gọi API LLM thực tế (`upstage/solar-pro4` hoặc `google/gemma-3-4b-it`).
   - Tự động đánh giá mức độ nghiêm trọng (`recommendedSeverity`), trích xuất lý do chuyên môn (`rationale`) và đề xuất hành động.
   - Cơ chế bảo vệ quyền riêng tư: **Chỉ gửi metadata số học** (tọa độ, số người, thời gian lưu trú), tuyệt đối không gửi ảnh khuôn mặt hay video thô ra bên ngoài.
   - Cơ chế chịu lỗi (Fault-tolerance): Tự động kích hoạt **Deterministic Fallback** nếu mất mạng hoặc LLM quá tải.
3. **Cảnh báo thời gian thực & Phòng trực ban trực quan (Real-time Web UI):**
   - Đẩy thông báo tức thời qua **WebSockets (`/ws/alerts`)** không độ trễ.
   - Vẽ **Bounding Box** trực tiếp trên khung hình video để nhân viên an ninh dễ dàng nhận biết vị trí đối tượng.
4. **Quy trình tương tác có con người kiểm soát (Human-In-The-Loop):**
   - Nhân viên an ninh xem xét nhận định của AI và đưa ra quyết định xử lý (Xác nhận / Phản hồi / Điều phối xử lý).

---

## 🛠️ Công Nghệ Sử Dụng (Tech Stack)

| Phân hệ | Công nghệ cốt lõi | Mô tả / Thư viện |
|---|---|---|
| **Front-End** | React 18, TypeScript, Vite | Tailwind CSS, Lucide React, Nginx (Docker container) |
| **Back-End API** | Python 3.11+, FastAPI, Uvicorn | Pydantic v2, SQLAlchemy 2.0 ORM, WebSockets, PyJWT, Passlib (Bcrypt) |
| **AI Agent** | LangGraph, LangChain Core | Private state machine workflow, OpenAI-compatible LLM Adapter |
| **Computer Vision** | DEIMv2 (Phase 7A), ByteTrack | OpenCV, PyTorch, Multi-adapter lifecycle engine |
| **Database & Storage** | PostgreSQL 15 & JSONL Store | Quản lý dữ liệu sự cố, tài khoản, camera và audit trail bất biến |
| **DevOps & Testing** | Docker, Docker Compose, Pytest | 308 automated tests, Vitest UI tests, Multi-stage Docker build |

---

## 📁 Cấu Trúc Thư Mục Dự Án (Project Structure)

```text
.
├── app/                        # Mã nguồn lõi AI Agent & Computer Vision Engine
│   ├── agents/                 # LangGraph Workflow, AssessmentRunner, Policies & Records
│   ├── cv/                     # DEIMv2 Detector, ByteTrack Tracker, Event Adapters & Manager
│   ├── llm/                    # OpenAI-compatible LLM Adapter kết nối Real Models
│   ├── common/                 # Pydantic Schemas & Contracts (EventCandidate, AgentAssessment)
│   └── config.py               # Cấu hình hệ thống tập trung (AppConfig)
├── back-end/                   # FastAPI Backend Service
│   ├── app/                    # API Routers, Database Models, WebSocket Manager, Auth & Ingest
│   ├── Dockerfile              # Dockerfile build backend API
│   └── pyproject.toml          # Dependencies backend
├── front-end/                  # React TypeScript Frontend Service
│   ├── src/                    # React Components, Dashboard, Pages, Realtime WebSocket Hooks
│   ├── Dockerfile              # Multi-stage Dockerfile (Node.js build -> Nginx serving)
│   └── package.json            # Dependencies frontend
├── configs/                    # File cấu hình Camera, Zone ROI và Event Rules (YAML)
├── docs/                       # Tài liệu thiết kế, PRD, SPEC, BRD và Sơ đồ kiến trúc chi tiết
├── eval/results/               # Báo cáo đánh giá chất lượng sản phẩm & 5 test cases thực tế
├── presentation/               # Video demo 3 phút (mp4) & Kịch bản thuyết trình
├── scripts/                    # Scripts tiện ích: run_mvp.ps1, demo_cli, submit_log
├── tests/                      # Bộ 308 automated tests (unit, contracts, integration, agents, api)
├── ARCHITECTURE.md             # Tài liệu kiến trúc toàn diện và sơ đồ Mermaid
├── docker-compose.yml          # Container orchestration (PostgreSQL + Backend + Frontend)
├── .env.example                # File mẫu biến môi trường
└── README.md                   # Tài liệu hướng dẫn dự án
```

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Dự Án (Getting Started)

### Cách 1: Khởi Chạy Nhanh Bằng 1 Lệnh Script (Khuyến nghị cho Windows)

Đảm bảo bạn đã clone repo và mở PowerShell tại thư mục gốc:

```powershell
# 1. Cấu hình biến môi trường
copy .env.example .env

# 2. Khởi chạy toàn bộ hệ thống (Backend API + Frontend Web UI)
.\scripts\run_mvp.ps1
```

Script sẽ tự động kiểm tra endpoint `/health`, mở Backend tại `http://localhost:8000` và Frontend tại `http://localhost:5173`.

---

### Cách 2: Khởi Chạy Bằng Docker Compose (Windows & Linux)

Yêu cầu: Máy tính đã cài đặt **Docker Desktop** (Windows) hoặc **Docker Engine & Docker Compose** (Linux).

#### 1. Cấu hình biến môi trường
```bash
# Windows PowerShell
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

#### 2. Khởi chạy toàn bộ 3 dịch vụ (PostgreSQL + Backend + Frontend)
```bash
docker compose up --build -d
```

#### 3. Kiểm tra trạng thái và theo dõi log
```bash
# Kiểm tra danh sách container
docker compose ps

# Xem log theo thời gian thực
docker compose logs -f

# Dừng hệ thống
docker compose down
```

---

## 🌐 Các Đường Dẫn Truy Cập (Access URLs) & Tài Khoản Mẫu

Sau khi hệ thống khởi động thành công:

| Dịch vụ | Địa chỉ / URL | Mô tả |
|---|---|---|
| **Front-End (Web Dashboard)** | [http://localhost:5173](http://localhost:5173) | Giao diện phòng giám sát an ninh (React) |
| **Back-End REST API** | [http://localhost:8000](http://localhost:8000) | FastAPI Server |
| **Swagger API Documentation** | [http://localhost:8000/docs](http://localhost:8000/docs) | Tài liệu API tương tác tự động Swagger |
| **ReDoc API Documentation** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Giao diện API ReDoc |
| **PostgreSQL Database** | `localhost:5432` | DB: `security_db` \| User: `postgres` \| Pass: `postgres` |

### 🔑 Tài khoản đăng nhập mẫu:
- **Tài khoản Bảo vệ (Guard):** `guard` / `guard123` (Xem Dashboard, trực ca, xử lý cảnh báo)
- **Tài khoản Quản lý (Manager):** `manager` / `manager123` (Toàn quyền, xem thêm Bản đồ điểm nóng `/heatmap`)

---

## 🧪 Chạy Demo Video & Kiểm Thử Sự Cố Thực Tế

### 1. Chạy Demo CLI Kiểm Thử Luồng End-to-End
Sau khi backend đang chạy, bạn có thể kích hoạt luồng phát hiện sự cố mẫu bằng mô hình DEIMv2 thực tế và kiểm tra phản hồi tức thì qua WebSocket:

```powershell
$env:EVENT_INGEST_TOKEN = 'secret-security-token-2026'
python -m app.cv.demo_cli
```

### 2. Chạy Luồng Giám Sát Multi-Camera (CV Stream)
```powershell
python -m app.cv.multi_camera_runner
```

### 3. Xem Video Demo 3 Phút
- File video demo hoàn chỉnh cho Gate G2 được lưu tại: [`presentation/mvp-demo-2026-08-16.mp4`](file:///D:/Coding/P-176/presentation/mvp-demo-2026-08-16.mp4).
- Kịch bản thuyết trình và checklist chi tiết xem tại: [`presentation/README.md`](file:///D:/Coding/P-176/presentation/README.md).

---

## 📝 Ví Dụ Gọi API (Sample Queries)

Dùng các lệnh sau để thao tác trực tiếp với Backend API qua REST và WebSocket:

### 1. Đăng nhập lấy Token xác thực (JWT)
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"guard","password":"guard123"}'
```
*Phản hồi mẫu:* `{"access_token":"<YOUR_JWT_TOKEN>","token_type":"bearer","user":{"id":1,"username":"guard","role":"bao_ve"}}`

### 2. Lấy danh sách sự cố cảnh báo
```bash
curl -X GET "http://localhost:8000/api/v1/alerts" \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>"
```

### 3. Bảo vệ xác nhận xử lý sự cố (Acknowledge Action)
```bash
curl -X POST "http://localhost:8000/api/v1/alerts/1/acknowledge" \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>"
```

### 4. Kết nối WebSocket nhận cảnh báo thời gian thực
```javascript
const socket = new WebSocket("ws://localhost:8000/ws/alerts");
socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Cảnh báo mới từ hệ thống:", data);
};
```

---

## 📊 Kết Quả Đánh Giá Chất Lượng (Evaluation & Metrics)

Báo cáo nghiệm thu kỹ thuật chi tiết tại [`eval/results/report.md`](file:///D:/Coding/P-176/eval/results/report.md):
- **Độ chính xác đánh giá AI (Reasoning Accuracy):** $100\%$ trên bộ test cases benchmark.
- **Độ trễ trung bình gọi LLM thực tế:** $2.5\text{s} - 2.9\text{s}$ (đo bằng telemetry).
- **Khả năng chống trùng lặp (Duplicate Suppression):** $100\%$ qua cơ chế SHA-256 payload digest.
- **Bộ Test Suite tự động:** **308 tests** đã được thu thập và vượt qua toàn bộ kiểm thử.
- **Kiểm thử hồi quy Video thật (CV Regression):** $4/4$ clips đạt chuẩn (ABODA vật thể bỏ quên, Walk1 xâm nhập, Meet_Crowd tụ tập, Browse1 âm tính).

---

## 🏛️ Tài Liệu Tham Khảo (Documentation)

- Sơ đồ kiến trúc & Data Flow toàn diện: [`ARCHITECTURE.md`](file:///D:/Coding/P-176/ARCHITECTURE.md)
- Chi tiết thiết kế AI Agent: [`docs/architecture_diagram.md`](file:///D:/Coding/P-176/docs/architecture_diagram.md)
- Báo cáo đánh giá Gate G2: [`eval/results/report.md`](file:///D:/Coding/P-176/eval/results/report.md)
- Kịch bản Demo & Slide: [`presentation/README.md`](file:///D:/Coding/P-176/presentation/README.md)
