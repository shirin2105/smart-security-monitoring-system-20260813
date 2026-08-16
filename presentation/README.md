# Pitch Deck & Demo Materials — Smart Security Monitoring System MVP

**Project:** P-176 — Smart Security Monitoring System  
**Milestone:** Gate G2 — MVP  

---

## 📁 Demo & Pitch Files

- `mvp-demo-2026-08-16.mp4` / `video_demo.mp4` — Video demo luồng sản phẩm end-to-end (3 phút).
- `pitch_deck.pptx` — Slide thuyết trình tổng quan dự án.

---

## 🎬 3-Minute Video Demo Structure & Checklist

| Mốc thời gian | Phân cảnh | Nội dung thuyết minh & Demo | Trạng thái |
|:---:|---|---|:---:|
| **0:00 – 0:30** | **1. Problem & Context** | Giới thiệu bài toán giám sát an ninh: camera truyền thống quá tải cảnh báo giả, thiếu khả năng phân tích rủi ro thời gian thực. | [x] Hoàn thành |
| **0:30 – 1:30** | **2. Live CV & Ingest** | Demo Computer Vision (DEIMv2 + ByteTrack): phát hiện đối tượng, nhận diện xâm nhập vùng cấm (`ZONE_INTRUSION`), gửi `EventCandidate` qua API. | [x] Hoàn thành |
| **1:30 – 2:30** | **3. AI Agent Reasoning** | Demo LangGraph Agent gọi LLM thực tế (`upstage/solar-pro4`): phân tích metadata, đánh giá mức độ nghiêm trọng (`recommendedSeverity`) và đề xuất hành động. | [x] Hoàn thành |
| **2:30 – 3:00** | **4. Web UI & Guard Action** | Cảnh báo đẩy tức thời lên Web Dashboard qua WebSockets, hiển thị bounding box và thao tác xử lý của nhân viên an ninh (HITL). | [x] Hoàn thành |

---

## 🛠️ Hướng Dẫn Chạy & Tái Hiện Demo Live

```powershell
# 1. Chạy toàn bộ hệ thống (Backend + Frontend)
.\scripts\run_mvp.ps1

# 2. Chạy kịch bản phát hiện sự cố mẫu & kết nối WebSockets
$env:EVENT_INGEST_TOKEN = 'your-secret-token'
python -m app.cv.demo_cli
```

---

## 📊 Cấu Trúc Pitch Deck (10 Slides Chuẩn)

1. **Title** — Smart Security Monitoring System (P-176) & Team.
2. **Problem** — Cảnh báo giả trong giám sát an ninh và độ trễ phản ứng của con người.
3. **Solution** — Hệ thống AI đa tầng: DEIMv2 Object Detection + LangGraph Advisory Agent + Realtime Web UI.
4. **Live Demo** — Video 3 phút luồng end-to-end với dữ liệu thật.
5. **Architecture** — Sơ đồ kiến trúc hệ thống và chuỗi dữ liệu (Data Flow).
6. **Tech Stack** — DEIMv2, ByteTrack, LangGraph, FastAPI, PostgreSQL, WebSockets, React 18, Tailwind.
7. **Traction & Metrics** — 308 tests passing, độ trễ LLM 2.5s, 100% duplicate suppression.
8. **Market** — Thị trường camera AI và hệ thống giám sát tòa nhà/khu công nghiệp.
9. **Team** — Phân công vai trò kỹ thuật.
10. **Ask** — Kế hoạch phát triển cho Gate G3.
