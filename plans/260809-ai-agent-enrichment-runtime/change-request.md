# Change Request — AI Agent Enrichment Runtime Integration

**CR ID:** CR-AI-20260809-01
**Ngày:** 2026-08-09
**Người đề xuất:** AI Agent Engineer
**Trạng thái:** DRAFT — chờ PM/TL approve
**Liên quan:** `plans/260808-1501-phase7a-person-luggage-kaggle` (CV trước), `reports/ai-agent-enrichment-runtime.md` (kết quả verify)

---

## 1. Bối cảnh / vấn đề

- Agent enrichment core đã có (graph, adapter, fallback) nhưng **chỉ chạy tay qua CLI**.
- Endpoint `POST /internal/api/v1/event-candidates` persist candidate xong rồi dừng — không gọi agent, không có assessment lưu kèm.
- Hệ thống chưa có AI evaluation layer (schema-valid rate, fallback rate, latency) — SPEC §15 yêu cầu metric machine-readable.

## 2. Thay đổi đề xuất (scope: agent layer)

1. **`app/services/enrichment.py`** (mới) — `EnrichmentService.enrich(candidate)`:
   - nhận EventCandidate đã persist;
   - gọi enrichment graph (LLM nếu có key, ngược lại fallback);
   - persist kết quả `enrichment_{candidateId}.json` kèm telemetry;
   - không bao giờ raise — lỗi LLM/persist đều resolve về fallback (FR-AI-06/07).
2. **`app/api/events.py`** (sửa) — sau khi persist + mark idempotency, chạy enrichment:
   - advisory: lỗi enrichment không fail ingest (endpoint vẫn 201);
   - response bao gồm `enrichment: {recommendedSeverity, fallback_used, error}`;
   - duplicate ingest không chạy enrichment lần 2.
3. **`app/services/enrichment_eval.py`** (mới) — `EvaluationReporter` đọc thư mục enrichment records, tổng hợp:
   - `schema_valid_rate`, `fallback_rate`, `schema_invalid_but_no_fallback`;
   - `severity_counts` (đối chiếu severity cap: ABANDONED_OBJECT ≤ HIGH);
   - `latency_ms.p50/p95/mean`, `models` distribution.

## 3. Tại sao cần

- PRD F7 "Agent assessment" chỉ có ý nghĩa khi chạy trong pipeline thật, không phải CLI tay.
- SPEC §9: agent phải có "model/prompt/version logged" — telemetry persist mới có cái để log.
- SPEC §15: AI evaluation là gate cho release — cần dữ liệu, chưa cần threshold số.

## 4. Ảnh hưởng / rủi ro

| Ảnh hưởng | Đánh giá |
|---|---|
| Response ingest thêm field `enrichment` | additive, không breaking — client cũ bỏ qua field lạ |
| Latency ingest tăng ~1 LLM call (tối đa timeout 15s) | chấp nhận được MVP; khi cần scale chuyển background task (đã note) |
| Không có LLM key → mọi enrichment là fallback | đúng thiết kế fail-safe; không chặn ingest |
| Xung đột với CV/fullstack | không — không đụng `app/cv`, `app/events`, UI, DB schema |

## 5. Acceptance criteria

- [x] Ingest 201 kèm `enrichment` field; duplicate không enrich lần 2 (test + smoke).
- [x] LLM unavailable → fallback output hợp lệ, ingest không fail.
- [x] `EvaluationReporter.report()` trả metric machine-readable (test).
- [x] 94/94 test pass, coverage agent scope 96%, ruff sạch file mới.
- [x] Chạy LLM thật với key → telemetry thật (bổ sung 2026-08-09, xem §7).

## 6. Quyết định cần PM/TL

1. **Approve merge** CR này (không có P0/P1 open).
2. **Chốt `LLM_TIMEOUT_SECONDS`**: latency thật p95 18.7s vượt timeout mặc định 15s — cần nâng (giới hạn 30s) hoặc đổi model nhanh hơn trước release.
3. Chốt threshold AI evaluation sau khi benchmark nhiều event type (SPEC §15).
4. Có cần chuyển enrichment sang background task trước release không, hay giữ đồng bộ trong request (volume MVP).

## 7. Kết quả LLM thật (bổ sung 2026-08-09)

`.env` có `OPENROUTER_*`; đã map sang `LLM_BASE_URL/LLM_API_KEY/LLM_MODEL`. Chạy 9 candidate persisted qua `z-ai/glm-5.2`:

- schema_valid_rate **1.0**, fallback_rate **0.11** (1/9 fail transient, retry pass), không output invalid.
- severity 9/9 HIGH (đều ZONE_INTRUSION — hợp lý).
- latency p50 **3.7s**, p95 **18.7s**, mean **7.1s** — p95 vượt timeout 15s.

Cấu hình: `AppConfig.llm_timeout_seconds=15.0` (giới hạn 30s trong `LLMAdapter`). Fail transient 1/9 chứng minh thiết kế fail-safe hoạt động đúng trong production path.
