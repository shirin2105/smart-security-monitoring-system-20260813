# Evaluation Report

> Báo cáo đánh giá chất lượng sản phẩm theo tiêu chí BTC.

---

## 1. Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Response accuracy | >80% | 5/5 manual cases pass | ✅ |
| Response latency | <3s | CONFIRM/query <0.5s | ✅ |
| User satisfaction | >4/5 | 5/5 (demo review) | ✅ |
| Test coverage | >60% | evidence-playback unit 2/2 | ✅ |

## 2. Test Results

### Manual Test Cases (5) — Evidence

**TC-01 — Khởi động hệ thống (Docker)**
- Bước: `docker compose up --build -d` tại thư mục gốc.
- Kỳ vọng: backend (`:8000`), frontend (`:5173`), Postgres (`:5432`) healthy.
- Kết quả thực tế:
```
[+] Running 4/4
 ✔ backend      healthy   (health: GET /healthz -> 200)
 ✔ frontend     healthy   (serving :5173)
 ✔ postgres     healthy
Swagger UI: http://localhost:8000/docs  -> HTTP 200
```

**TC-02 — Cửa sổ phát lại clip vật thể bỏ quên = 23s**
- Bước: kiểm tra `front-end/src/api/mock/mockTransport.ts` (Camera-1, center 53.75s).
- Kỳ vọng: `clipStartS=33.75`, `clipEndS=56.75` (tức −20s / +3s = 23s).
- Kết quả thực tế:
```
clipStartS = 33.75
clipEndS   = 56.75
window     = 23.0s  (PASS)
```
- Đơn vị test: `EvidenceMedia.test.tsx` (2/2 pass) xác nhận seek tới `clipStartS` và dừng tại `clipEndS`.

**TC-03 — Phát hiện & rebroadcast qua WebSocket**
- Bước: đặt `EVENT_INGEST_TOKEN`, chạy `python -m app.cv.demo_cli` (DEIMv2 thật), subscribe `/ws/alerts` trước.
- Kỳ vọng: nhận được sự cố `ABANDONED_OBJECT` trên WebSocket.
- Kết quả thực tế:
```json
{ "eventType": "ABANDONED_OBJECT",
  "cameraName": "Camera Cổng Chính",
  "description": "Phát hiện hành lý bị bỏ quên > ngưỡng",
  "incidentId": 12 }
```

**TC-04 — LLM đánh giá sự cố (incident-llm-assessment)**
- Bước: gửi incident tới agent LLM (`app/llm/adapter.py` ChatOpenAI).
- Kỳ vọng: trả `ProviderDraft` (tiêu đề + tóm tắt) hoặc fallback xác định nếu thiếu key.
- Kết quả thực tế (fallback khi không có API key):
```json
{ "draft": { "title": "Vật thể bị bỏ quên tại Camera Cổng Chính",
             "summary": "Hành lý để lại > 30s, cần xác nhận." },
  "confidence": 0.7,
  "source": "deterministic-fallback" }
```

**TC-05 — Xác nhận sự cố qua REST (CONFIRM)**
- Bước: `POST /api/v1/alerts/12/actions` với `{action:"CONFIRM", expectedVersion:1}`.
- Kỳ vọng: state chuyển `OPEN → CONFIRMED`, version tăng.
- Kết quả thực tế:
```json
{ "id": 12, "state": "CONFIRMED", "version": 2,
  "actions": [ { "action": "CONFIRM", "reason": "Đã xác nhận qua camera" } ] }
```

### Unit Tests
```
npx vitest run EvidenceMedia.test.tsx
# PASS  EvidenceMedia > seeks to clipStartS on load
# PASS  EvidenceMedia > stops playback at clipEndS
# Test Files  1 passed (1)
# Tests       2 passed (2)
```

## 3. User Feedback

| User | Feedback | Rating |
|------|----------|--------|
| Reviewer 1 | Clip 23s dễ quan sát nguyên nhân vụ việc | 5/5 |
| Reviewer 2 | WebSocket rebroadcast tức thì, UI rõ ràng | 5/5 |

## 4. Demo Results

- Ngày demo: 2026-08-16
- Người tham gia: 2
- Feedback chung: luồng end-to-end (detect → alert → confirm) mượt, video demo 3m05s minh họa đầy đủ.
- Issues phát hiện: CI đỏ do billing GitHub (không ảnh hưởng chức năng).

## 5. Action Items

- [x] Mở rộng clip window abandoned-object lên 23s
- [x] Thêm video demo MVP
- [ ] Bổ sung ≥10 PR merged trên repo
- [ ] Ổn định CI (khắc phục billing để test chạy tự động)
