# AI Camera Security Agent

Hệ thống giám sát và cảnh báo an ninh từ camera, kết hợp Computer Vision, temporal event detection, incident management, optional AI Agent assessment và Human-in-the-Loop (HITL) cho các hành động escalation nhạy cảm.

> Tài liệu này là entry point cho dự án. Hiện input của bộ docs **chưa bao gồm repository/source code thực tế**, vì vậy README không ghi các lệnh `docker compose`, `pip`, `npm` hoặc port giả định. Khi repo được cung cấp, chỉ bổ sung lệnh đã được chạy/verify thực tế.

---

## 1. Bài toán

Camera khu đô thị có thể rất nhiều, trong khi bảo vệ không thể nhìn tất cả cùng lúc. Hệ thống tập trung vào việc:

- phát hiện sự kiện đáng chú ý;
- gom frame-level detection thành event logic;
- persist incident;
- cảnh báo operator gần realtime;
- dùng Agent để enrich assessment khi baseline đã ổn định;
- yêu cầu người có quyền xác nhận trước protected escalation;
- lưu audit và đo chất lượng bằng event-level metrics.

## 2. MVP

Ba event bắt buộc:

1. `restricted_zone_intrusion`
2. `crowd_gathering`
3. `abandoned_object`

Operator surface:

- React/TypeScript Web/PWA;
- 2 roles: `GUARD`, `SECURITY_MANAGER`.

Core flow:

```text
Camera/Video
  -> Detection
  -> Tracking
  -> Temporal Event Engine
  -> Incident
  -> Agent Assessment (optional/gated)
  -> Policy
  -> HITL
  -> Alert/Audit
  -> Operator UI
```

## 3. Nguyên tắc kiến trúc

- `Detection != Event != Incident != Alert`.
- LLM/VLM không phải primary detector.
- Persist incident trước WebSocket notification.
- Agent output phải schema-validated.
- Protected action không bypass human approval.
- Không gửi continuous raw video tới external LLM/VLM.
- Không claim capacity ngoài benchmark đã chạy.

## 4. Bộ tài liệu

| File | Đọc khi cần |
|---|---|
| [`BRIEF.md`](BRIEF.md) | Tóm tắt bài toán, scope, quyết định chính |
| [`BRD.md`](BRD.md) | Business requirements, stakeholders, business rules |
| [`PRD.md`](PRD.md) | Personas, product scope, user stories, functional/NFR |
| [`SPEC.md`](SPEC.md) | Contracts, event semantics, API, Agent/HITL, testing |
| [`UI_WIREFRAME.md`](UI_WIREFRAME.md) | Sitemap, screen flow, ASCII wireframes, UI states |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Components, data flow, trust boundaries, deployment |
| `README.md` | Entry point và operating model |

### Thứ tự đọc theo vai trò

**CV Lead**  
`BRIEF -> PRD -> SPEC -> ARCHITECTURE`

**AI/Agent Lead**  
`BRIEF -> PRD -> SPEC -> ARCHITECTURE`

**Full Stack Lead**  
`README -> PRD -> SPEC -> ARCHITECTURE -> UI_WIREFRAME`

**Realtime UI Lead**  
`README -> PRD -> UI_WIREFRAME -> SPEC`

**PM/TL**  
`BRIEF -> BRD -> PRD -> ARCHITECTURE -> SPEC`

## 5. Yêu cầu nguồn vs quyết định dự án

### Yêu cầu nguồn

Đề bài gốc yêu cầu:

- AI Agent camera monitoring;
- CV bất thường;
- ≥3 events;
- severity/reaction planning;
- context memory;
- HITL cho escalation;
- privacy hình ảnh cư dân;
- realtime;
- 2 role web;
- incident log.

### Quyết định PM/TL

Dự án đã khóa:

- đúng 3 event MVP: intrusion, crowd, abandoned object;
- fall là post-MVP;
- Web/PWA thay native mobile;
- local video first, RTSP sau;
- deterministic temporal event engine;
- Agent advisory, không primary detector;
- baseline metric trước real Agent;
- protected action qua policy + HITL;
- event-level evaluation;
- test tải 1/2/4 sources.

## 6. Tech stack mục tiêu

### Gợi ý từ đề bài

- YOLOv8/v11 hoặc tương đương;
- optional VLM;
- LLM;
- LangGraph;
- OpenCV;
- PostgreSQL;
- FastAPI + WebSocket;
- React;
- Docker;
- optional GPU;
- optional vector DB.

### Định hướng MVP

- PostgreSQL là authoritative business storage.
- Vector DB không required nếu structured context đủ.
- Không over-engineer Kafka/Kubernetes trong 4 tuần.

## 7. Cấu trúc repository đề xuất

Đây là **cấu trúc đề xuất**, không phải xác nhận repo hiện có:

```text
.
├── apps/
│   ├── api/
│   └── dashboard/
├── services/
│   ├── video_ingest/
│   ├── vision/
│   ├── event_engine/
│   └── agent/
├── packages/
│   ├── contracts/
│   ├── config/
│   └── observability/
├── tests/
├── docs/
├── infra/
├── BRIEF.md
├── BRD.md
├── PRD.md
├── SPEC.md
├── UI_WIREFRAME.md
├── ARCHITECTURE.md
└── README.md
```

Khi repo thực tế có cấu trúc khác, ưu tiên existing conventions và cập nhật docs.

## 8. 4-week execution model

### Tuần 1 — Vertical slice cho intrusion

Mục tiêu:

`local video -> detector -> tracker -> intrusion -> incident DB -> WebSocket -> dashboard`

Agent mock/disabled.

### Tuần 2 — 3 event + baseline

- crowd;
- abandoned object;
- temporal dedupe;
- fixed test set;
- event metrics baseline.

### Tuần 3 — Agent + an toàn

- structured Agent;
- context;
- policy;
- HITL;
- auth/RBAC;
- evidence protection;
- audit.

### Tuần 4 — Hardening/release

- precision/recall/F1;
- false alerts/camera-hour;
- p50/p95;
- 1/2/4-source load;
- ablation;
- deployment;
- bug bash;
- final demo.

## 9. Release blockers

### P0

- privacy leak;
- incident loss;
- HITL bypass;
- event storm;
- core crash.

### P1

Ví dụ:

- severe duplicate incidents;
- claimed RTSP reconnect không hoạt động;
- UI bỏ miss persisted incident;
- tracker/event core failure trên supported path.

Theo project baseline hiện tại: không final release với open P1.

## 10. Evaluation

Primary metrics:

- event-level precision;
- event-level recall;
- F1;
- false alerts/camera-hour;
- miss rate;
- duplicate incidents;
- p50/p95 latency;
- FPS/dropped frames/resource load.

Ablation:

- A: detector + simple rules;
- B: + tracking + temporal;
- C: + Agent;
- D: + context nếu stable.

## 11. Quy tắc phát triển

- Shared contract changes phải version/review.
- Config không hard-code.
- Protected action logic không giao cho LLM.
- PR/merge phải có reproducible acceptance evidence phù hợp.
- Agent chỉ enable sau baseline gate.
- Không dùng UI screenshot đơn lẻ làm bằng chứng event correctness.
- Không tune threshold trên final fixed test set mà không disclose.

## 12. Chạy MVP (đã verify)

Repository thực tế gồm ba mảng đã tích hợp:

| Mảng | Vị trí | Vai trò |
|---|---|---|
| CV pipeline | `app/` | Video → YOLO detection → tracking → event engine → `EventCandidate` |
| Back-end API | `back-end/` | Auth, incidents, audit, WebSocket, ingest endpoint |
| Frontend | `front-end/` | React/PWA dashboard (Vite) |

### 12.1 Cài đặt

```bash
# Root venv chứa cả app/ và back-end/ deps
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/pip install ultralytics   # YOLO model (tự tải yolo26m.pt lần đầu)

cd front-end && npm install && cd ..
```

### 12.2 Chạy từng mảng (3 terminal)

```bash
# Terminal 1 — Back-end API (port 8000, SQLite fallback nếu không có Postgres)
cd back-end && ../.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000

# Terminal 2 — Frontend (port 5173)
cd front-end && npm run dev

# Terminal 3 — CV pipeline (đẩy sự kiện thật vào back-end)
.venv/Scripts/python.exe -m app.cv.run_pipeline --camera cam_01 --max-frames 300
```

Hoặc script gộp: `powershell -File scripts/run_mvp.ps1` (back-end + frontend).

### 12.3 Verify

- Login: `guard` / `guard123` hoặc `manager` / `manager123`
- Incident từ CV thật xuất hiện ở `GET /api/v1/alerts` + realtime qua WebSocket `ws://localhost:8000/ws/alerts`
- Test: `pytest tests/` (root) + `cd back-end && pytest tests/` (6 tests, gồm ingest endpoint)

### 12.4 Lưu ý

- `configs/cameras.yaml` trỏ clip `./tests/clips/intrusion_positive.mp4` — file này **không tồn tại**; dùng `--source-uri` hoặc sửa config nếu muốn.
- DB mặc định SQLite (`security_monitoring.db`) khi không có Postgres; `docker-compose.yml` bật Postgres + cả ba service.
- `yolo26m.pt` tải tự động lần đầu (42MB).

## 13. Nguồn chuẩn

Đối với bộ file này:

1. `detai.csv` là nguồn yêu cầu đề bài.
2. `BRIEF.md` tóm tắt baseline.
3. `BRD.md` định nghĩa business intent.
4. `PRD.md` định nghĩa product behavior.
5. `SPEC.md` định nghĩa technical semantics.
6. `ARCHITECTURE.md` định nghĩa module boundaries.
7. Nếu code thực tế khác docs, divergence phải được review và docs phải cập nhật.

Bộ Markdown này độc lập với Jira; Jira chỉ nên dùng để track execution, không phải là điều kiện để đọc hiểu sản phẩm.
