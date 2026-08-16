# Architecture Diagram — Smart Security Monitoring System

**Project:** P-176 — Hệ Thống Giám Sát An Ninh Thông Minh  
**Milestone:** Gate G2 — MVP  

---

## 1. System Architecture & Components Overview

Sơ đồ tổng quan toàn bộ các thành phần (Components) trong hệ thống:

```mermaid
graph TB
    subgraph VideoSources["🎥 Video Sources & Stream Ingest"]
        CAM1["Camera 1 (RTSP Stream)"]
        CAM2["Camera 2 (Test Video Clips)"]
        INGEST_WORKER["Video Ingest Worker"]
    end

    subgraph VisionSubsystem["👁️ Computer Vision Pipeline (DEIMv2 + ByteTrack)"]
        DEIM["DEIMv2 Object Detector<br/>(Phase 7A Checkpoint)"]
        TRACK["ByteTrack Multi-Object Tracker<br/>(Namespace Isolated)"]
        TSTORE["Shared TrackStore<br/>(Immutable Snapshot per Frame)"]
        ADAPT["Event Adapters<br/>• Zone Intrusion<br/>• Crowd Threshold<br/>• Abandoned Object"]
        EVMGR["CV Event Manager<br/>(Lifecycle & Debounce)"]
        PUB["CV Ingest Client<br/>(JSONL & HTTP Ingest)"]
    end

    subgraph BackendSubsystem["⚡ FastAPI Backend Service"]
        INGEST_ROUTE["POST /api/v1/events/ingest<br/>(HMAC Auth + Deduplication)"]
        INC_SERVICE["Incident Management Service"]
        WS_SERVICE["WebSocket Manager<br/>(/ws/alerts)"]
        REST_ROUTES["REST API Routes<br/>(Auth, Cameras, Zones)"]
    end

    subgraph AgentSubsystem["🧠 AI Agent Subsystem (LangGraph)"]
        RUNNER["AssessmentRunner"]
        GRAPH["Private LangGraph Workflow<br/>(prepare ➔ provider ➔ route ➔ fallback)"]
        LLM_ADAPTER["LLM Adapter<br/>(OpenAI-compatible)"]
        EXT_LLM[("🌐 Real External LLM<br/>Upstage Solar / Gemma / GPT-4o")]
        FALLBACK_POLICY["Deterministic Policy Engine"]
    end

    subgraph DataLayer["💾 Persistence Layer"]
        PG_DB[("🐘 PostgreSQL 15 Database<br/>(incidents, cameras, users, zones)")]
        JSONL_STORE[("📁 JSONL Event Log<br/>(cv-events.jsonl)")]
    end

    subgraph ClientLayer["🖥️ Frontend Web Application (React 18 + Vite)"]
        DASH["Live Surveillance Dashboard"]
        ALERTS_VIEW["Real-time Alerts & Bounding Box"]
        HITL_VIEW["Incident Review & Guard Action (HITL)"]
    end

    %% Edge Connections
    CAM1 --> INGEST_WORKER
    CAM2 --> INGEST_WORKER
    INGEST_WORKER --> DEIM
    DEIM --> TRACK
    TRACK --> TSTORE
    TSTORE --> ADAPT
    ADAPT --> EVMGR
    EVMGR --> PUB

    PUB -->|HTTP Ingest with Token| INGEST_ROUTE
    PUB -.->|Local Audit Sink| JSONL_STORE

    INGEST_ROUTE --> INC_SERVICE
    INC_SERVICE --> PG_DB
    INC_SERVICE --> WS_SERVICE
    INC_SERVICE --> RUNNER

    RUNNER --> GRAPH
    GRAPH --> LLM_ADAPTER
    LLM_ADAPTER -->|Bounded Metadata Only| EXT_LLM
    LLM_ADAPTER -.->|On Timeout / Failure| FALLBACK_POLICY
    GRAPH --> INC_SERVICE

    WS_SERVICE -->|WebSocket Push| DASH
    DASH --> ALERTS_VIEW
    ALERTS_VIEW --> HITL_VIEW
    HITL_VIEW -->|Guard Action: Acknowledge/Resolve| REST_ROUTES
    REST_ROUTES --> INC_SERVICE
```

---

## 2. End-to-End Data Flow Sequence

Sơ đồ tuần tự luồng dữ liệu xử lý xuyên suốt từ khung hình video đến giao diện nhân viên an ninh:

```mermaid
sequenceDiagram
    autonumber
    actor Guard as 👮 Nhân viên An ninh
    participant Cam as 📹 Camera / Video Source
    participant CV as 👁️ CV Pipeline (DEIMv2 + Tracker)
    participant API as ⚡ FastAPI Backend
    participant DB as 🐘 PostgreSQL
    participant Agent as 🧠 AI Agent (LangGraph)
    participant LLM as 🌐 Real LLM Provider
    participant WS as 📡 WebSocket (/ws/alerts)
    participant UI as 🖥️ React Web UI

    Cam->>CV: Stream từng Frame hình ảnh
    CV->>CV: DEIMv2 suy luận đối tượng + ByteTrack gán track_id
    CV->>CV: Event Adapter kiểm tra điều kiện (xâm nhập vùng cấm / thời gian tĩnh)
    CV->>API: POST /api/v1/events/ingest (EventCandidate + Bearer Token)
    
    API->>API: Xác thực Token HMAC & Kiểm tra trùng lặp (SHA-256 Digest)
    API->>DB: Lưu bản ghi Incident (trạng thái: 'pending')
    API->>WS: Broadcast NEW_ALERT
    WS-->>UI: Hiển thị sự cố mới + Bounding Box lên màn hình giám sát

    API->>Agent: Kích hoạt AssessmentRunner(snapshot_metadata)
    Agent->>Agent: Node 'prepare': đóng gói prompt chỉ gồm metadata
    Agent->>LLM: Gửi request phân tích mức độ nguy hiểm & lý do an ninh
    LLM-->>Agent: Trả về JSON { recommendedSeverity, rationale }
    Agent->>API: Cập nhật AgentAssessment vào cơ sở dữ liệu
    
    API->>WS: Broadcast UPDATE_ALERT (bổ sung nhận định AI)
    WS-->>UI: Cập nhật lý do phân tích và khuyến nghị của AI trên giao diện
    
    Guard->>UI: Xem xét cảnh báo và khuyến nghị từ AI
    Guard->>API: Gửi lệnh xử lý (Xác nhận / Điều phối / Đóng sự cố)
    API->>DB: Cập nhật trạng thái sự cố ('resolved')
    API->>WS: Broadcast sự cố đã được xử lý thành công
```

---

## 3. AI Agent Workflow Diagram (LangGraph)

Agent đánh giá rủi ro an ninh hoạt động theo State Machine có kiểm soát fallback chặt chẽ:

```mermaid
stateDiagram-v2
    [*] --> PREPARE: Nhận EventCandidate
    
    state PREPARE {
        [*] --> FormatPrompt: Trích xuất metadata (camera, zone, dwell, personCount)
        FormatPrompt --> ValidateBoundary: Đảm bảo không chứa ảnh thô (Privacy Check)
    }

    PREPARE --> PROVIDER: Prompt sẵn sàng

    state PROVIDER {
        [*] --> InvokeLLM: Gọi ChatOpenAI / Real LLM Adapter
        InvokeLLM --> AwaitResponse: Chờ phản hồi (Timeout = 15s)
    }

    PROVIDER --> ROUTE: Nhận phản hồi

    state ROUTE <<choice>>
    ROUTE --> COMPLETED: Phản hồi hợp lệ & Đạt JSON schema
    ROUTE --> FALLBACK: Timeout / Mất mạng / Schema không hợp lệ

    state FALLBACK {
        [*] --> ApplyRules: Áp dụng Deterministic Rule Policy
        ApplyRules --> AssignSafeSeverity: Gán mức nghiêm trọng an toàn
    }

    FALLBACK --> COMPLETED: Hoàn tất Fallback
    COMPLETED --> [*]: Xuất AgentAssessment
```

---

## 4. Chi Tiết Thành Phần Hệ Thống (Component Specifications)

| Thành phần (Component) | Công nghệ / Thư viện | Trách nhiệm chính (Responsibility) | Giao tiếp (Interfaces) |
|---|---|---|---|
| **Video Ingest & CV** | DEIMv2, ByteTrack, OpenCV | Đọc luồng video, phát hiện người/vật thể, bám vết đối tượng, phát hiện sự cố theo quy tắc thời gian thực. | Output: `EventCandidate` qua HTTP POST / JSONL |
| **Backend API Gateway** | FastAPI, Pydantic v2, Uvicorn | Tiếp nhận sự kiện có xác thực, chống bão cảnh báo (idempotency), quản lý tài khoản và camera. | Ingest: `/api/v1/events/ingest`<br/>REST: `/api/v1/...` |
| **Realtime Engine** | WebSocket (FastAPI Starlette) | Đẩy tức thời sự cố mới và cập nhật nhận định AI đến tất cả các phiên làm việc của bảo vệ. | `/ws/alerts` |
| **AI Agent Orchestrator** | LangGraph, LangChain Core | Quản lý vòng đời suy luận AI, chuẩn hóa cấu trúc prompt, kiểm soát timeout và fallback xác định. | `AssessmentRunner.assess()` |
| **LLM Reasoning Engine** | OpenAI-compatible API (`ChatOpenAI`) | Phân tích metadata sự cố bằng các mô hình LLM thực tế (`upstage/solar-pro4`, `google/gemma-3-4b-it`, `gpt-4o`). | HTTPS JSON Chat Completions |
| **Database Layer** | PostgreSQL 15, SQLAlchemy 2.0 | Lưu trữ bền vững dữ liệu sự cố, cấu hình camera, phân vùng giám sát và nhật ký hành động của bảo vệ. | Port `5432` / SQL Queries |
| **Web UI Dashboard** | React 18, Vite, Tailwind CSS, Lucide | Giao diện phòng trực ban: xem camera live, quan sát bounding box, tiếp nhận cảnh báo và xử lý HITL. | Port `5173` / HTTP REST + WS |

---

## 5. Các Ranh Giới An Toàn & Bảo Mật (Safety & Security Boundaries)

1. **Ranh giới Quyền Riêng Tư (Privacy Boundary):**
   - Không truyền hình ảnh khuôn mặt hoặc video thô lên các mô hình LLM bên ngoài.
   - Chỉ truyền các trường metadata phi định danh: toạ độ vùng, số lượng người, thời gian lưu trú, độ tin cậy của thuật toán CV.
2. **Ranh giới Ra Quyết Định (Human-in-the-Loop Boundary):**
   - AI Agent chỉ đóng vai trò **cố vấn (Advisory Only)**.
   - Không cho phép AI tự động thực hiện các hành động can thiệp vật lý (như khóa cửa, gọi cảnh sát) nếu chưa có sự xác nhận từ con người.
3. **Cơ Chế Chịu Lỗi (Fault-Tolerance):**
   - Nếu LLM không khả dụng hoặc phản hồi quá thời gian quy định, hệ thống tự động kích hoạt `deterministic-fallback` dựa trên luật cố định, đảm bảo mọi sự cố đều được ghi nhận và cảnh báo kịp thời.
