# Report — AI Agent Enrichment Runtime

**Ngày:** 2026-08-09
**Vai trò:** AI Agent Engineer
**Branch:** `agents` (đã merge `model-CV-v1`)
**Phạm vi:** chỉ agent layer — `app/agents`, `app/llm`, `app/services` + integration với ingest boundary. Không đụng CV (detector/tracker/event engine), không đụng UI/fullstack.

---

## 1. Tóm tắt

Trước phiên này, agent enrichment đã có core (graph + adapter + fallback, 18 test, commit `147c2dc`) nhưng **chưa nối vào runtime**: chỉ chạy tay qua `scripts/run_enrichment.py`, endpoint ingest `POST /internal/api/v1/event-candidates` chỉ persist candidate. Phiên này bổ sung runtime glue cho agent layer:

| Thành phần | Vai trò |
|---|---|
| `app/services/enrichment.py` | `EnrichmentService` — gọi enrichment graph trên EventCandidate đã persist, lưu kết quả JSON, không bao giờ raise (FR-AI-06/07) |
| `app/services/enrichment_eval.py` | `EvaluationReporter` — AI evaluation metrics: schema-valid rate, fallback rate, severity distribution, latency p50/p95 (SPEC §15) |
| `app/api/events.py` | ingest endpoint tự chạy enrichment sau persist (advisory, best-effort, không block ingest) |

## 2. Kết quả verify

### 2.1 Test suite

```text
94 passed, 1 warning in ~6s
```

- 16 test mới của phiên này (10 unit service, 2 integration API, 4 evaluation).
- Toàn bộ 78 test có sẵn vẫn pass — không regress.

### 2.2 Coverage (agent scope)

```text
app/agents/fallback.py          70%
app/agents/graph.py            100%
app/llm/adapter.py              95%
app/services/enrichment.py      96%
app/services/enrichment_eval.py 92%
TOTAL                          278 stmts, 96%
```

Vượt ngưỡng 80% requirement. Line chưa phủ: `fallback.py` branch `SUSPECTED_FALL`/default, `adapter.py` line parse rìa, `enrichment_eval.py` line lỗi file — đã phủ bằng test bổ sung cho fallback các event type.

### 2.3 Lint

```text
ruff check app/services/ tests/unit/test_enrichment_service.py
tests/unit/test_enrichment_evaluation.py tests/integration/test_enrichment_runtime_api.py
→ All checks passed!
```

Repo có sẵn 268 lỗi ruff pre-existing ở `app/cv`, `app/events`, `app/common` (UP0xx modernization chưa làm) — ngoài scope; Makefile cũng chỉ lint `src/ tests/`.

### 2.4 Smoke test thật

**Endpoint ingest (TestClient trên app thật):**
```text
POST 1: 201 {"status":"ACCEPTED", "enrichment":{"recommendedSeverity":"HIGH","fallback_used":true,"error":"llm_unavailable"}}
POST 2 (dup): 201 DUPLICATE_IGNORED
enrichment files: 1  → duplicate không tạo enrichment lần 2
```

- LLM key rỗng → graph route fallback, ingest vẫn 201 — đúng FR-AI-07.
- Severity `HIGH`, summary tiếng Việt, checklist allow-list.

**CLI `scripts/run_enrichment.py` (candidate thật `test-cand-http-*`):**
```text
test-cand-http-3c2fa1d9... -> fallback -> artifacts\enrichment\enrichment_test-cand-http-3c2fa1d9....json
```
Output đúng schema `EnrichmentOutput`, telemetry `fallbackUsed:true`, `model:google/gemma-3-4b-it`.

## 3. Tuân thủ docs

| Ràng buộc | Trạng thái |
|---|---|
| SPEC §9: agent output structured schema only, enum validated | ✅ `EnrichmentOutput` Pydantic + Literal severity |
| SPEC §9: timeout/invalid schema → fallback | ✅ adapter trả None → graph route fallback |
| SPEC §1-4: agent không mutate event/severity | ✅ test `test_graph_never_mutates_input_event` + service |
| BRD RULE-03: persist trước notify | ✅ enrichment chạy sau khi candidate write + idempotency mark |
| PRD F7: enrichment sau baseline, advisory | ✅ runtime gate `llm_enabled` config; endpoint trả `fallback_used` |
| SPEC §10: action checklist allow-list | ✅ fallback checklist từ allow-list |
| Không gửi raw video/frame tới LLM | ✅ chỉ metadata; `FrameData.image` excluded |

## 4. Kết quả LLM thật (bổ sung 2026-08-09)

Sau khi cấu hình key, chạy enrichment thật trên **9 candidate persisted** qua OpenRouter (`z-ai/glm-5.2`, temperature 0):

```text
total:                      9
schema_valid_rate:          1.0
fallback_rate:              0.111  (1/9 fail transient, retry pass)
schema_invalid_but_no_fallback: 0
severity_counts:            {HIGH: 9}   (đều ZONE_INTRUSION — hợp lý)
latency_ms:                 p50 3738.57 | p95 18705.27 | mean 7101.25
models:                     {z-ai/glm-5.2: 9}
```

Output mẫu (candidate `test-cand-http-3c2fa1d9`):

```text
fallback_used: False
severity: HIGH
rationale: Phát hiện xâm nhập vào khu vực hạn chế (restricted_gate) với độ tin cậy cao (0.95)...
summary: Sự kiện xâm nhập vùng (ZONE_INTRUSION) tại restricted_gate bởi 1 người...
checklist: 5 items
latency_ms: 17767.34
```

**Cấu hình dùng:** `.env` có sẵn `OPENROUTER_API_KEY/MODEL/BASE_URL`; đã map sang `LLM_BASE_URL/LLM_API_KEY/LLM_MODEL` (đọc bởi `AppConfig`). Key không in ra, `.env` trong gitignore.

## 5. Giới hạn (đã disclose)

- **Latency p95 18.7s vượt timeout mặc định 15s** — nguy cơ timeout thật với provider chậm. Đề xuất nâng `LLM_TIMEOUT_SECONDS` (AppConfig giới hạn 30s) hoặc dùng model nhanh hơn. Cần PM/TL chốt.
- 1/9 lần gọi fail transient (retry pass) — thiết kế fail-safe hoạt động đúng.
- `scripts/run_enrichment.py` mặc định ghi `artifacts/enrichment/`, `EnrichmentService` ghi `artifacts/backend_events/` — hai đường output khác nhau, có chủ đích (CLI tách biệt), nhưng nên thống nhất nếu muốn 1 pipeline.
- Enrichment chạy đồng bộ trong request handler — với candidate volume cao cần chuyển background task/queue (không phải yêu cầu MVP).

## 6. Files thay đổi

```
M  app/api/events.py                              # ingest chạy enrichment sau persist
A  app/services/__init__.py
A  app/services/enrichment.py                     # EnrichmentService
A  app/services/enrichment_eval.py                # EvaluationReporter
A  tests/unit/test_enrichment_service.py          # 10 test
A  tests/unit/test_enrichment_evaluation.py       # 4 test
A  tests/integration/test_enrichment_runtime_api.py # 2 test
```

## 7. Next steps (đề xuất)

1. Chốt `LLM_TIMEOUT_SECONDS` theo latency đo được (p95 18.7s).
2. Benchmark latency end-to-end với nhiều event type (crowd, abandoned) — hiện chỉ ZONE_INTRUSION.
3. Chuyển enrichment sang background task nếu volume tăng.
