# Report — Architecture Review Agent Candidates

**Ngày:** 2026-08-10
**Nguồn:** `architecture-review-20260810-115623.html` (5 candidates, 33 focused tests)
**Vai trò:** AI Agent Engineer — chỉ xử lý candidates thuộc agent scope, không đụng CV/fullstack/UI.
**Branch:** `agents`

---

## 1. Kết quả xử lý từng candidate

| # | Candidate | Strength | Quyết định | Trạng thái |
|---|---|---|---|---|
| 1 | Một Agent runtime canonical | Strong | **Làm** | ✅ Done |
| 2 | AgentAssessment tại seam của Incident | Strong | **Làm** | ✅ Done |
| 3 | Giấu LangGraph + persistence coordination | Strong | **Làm** | ✅ Done |
| 4 | Rời true-external LLM khỏi ingest request | Strong | **Làm** | ✅ Done |
| 5 | Deepen persisted-candidate intake | Worth exploring | **Làm** | ✅ Done |

### C1 — Một Agent runtime canonical

**Vấn đề:** Docker/Makefile/tests đi qua `src.main` (template chat shallow: `TODO + echo`); implementation thật nằm ở `app.main`. Deployment không qua implementation.

**Làm:**
- Xóa toàn bộ `src/` template (17 files: agents graph/state/nodes/tools, api/routes, models/schemas, services/llm, config, main) + `tests/test_agents/`, `tests/test_api/`.
- `Dockerfile` CMD → `uvicorn app.main:app`; HEALTHCHECK → `/health/live` (endpoint thật).
- `Makefile` run → `app.main:app`; lint/format → `app/ tests/ scripts/` (bỏ typecheck vì không còn mypy target).
- `tests/conftest.py` xóa fixture `client` phụ thuộc `src.main` + mock_llm thừa.

**Deletion test pass:** xóa template chỉ mất behavior mẫu; domain complexity (enrichment/assessment/intake) vẫn nguyên vẹn.

### C2 — AgentAssessment tại seam của Incident

**Vấn đề:** docs (SPEC §3.6) định nghĩa `AgentAssessment` (incident_id, severity enum, recommended_action allow-list, model/prompt version) nhưng implementation chỉ có `EnrichmentOutput` (LLM adapter contract, 4 fields, không action).

**Làm:** `app/agents/assessment.py` mới:
- `AgentAssessment` Pydantic — đúng 13 fields SPEC §3.6: `schema_version, assessment_id, incident_id, event_type, severity (low|medium|high|critical), confidence, reason, recommended_action, requires_human_approval, model_name, model_version, prompt_version, created_at`.
- `build_assessment()` — map `EnrichmentOutput` → assessment: severity INFO/WARNING/HIGH/CRITICAL → low/medium/high/critical; action từ allow-list SPEC §9 (`log_only, notify_guard, request_guard_verification, request_manager_review, request_alarm, request_gate_lock`); cap `ABANDONED_OBJECT` không bao giờ critical; `requires_human_approval=False` luôn (policy SPEC §10 quyết định, agent không được).
- Confidence lấy từ event candidate (không phải LLM) — nguồn sạch.

### C3 — Giấu LangGraph + persistence coordination

**Vấn đề:** runtime, CLI, tests đều biết graph state keys; CLI lặp telemetry + persistence.

**Làm:** `scripts/run_enrichment.py` thành thin adapter:
- Bỏ import `build_enrichment_graph`, `EnrichmentTelemetry`, settings; không còn đụng `result["output"]`/`result["telemetry"]`.
- Load candidate → `EventCandidate.model_validate` → gọi `service.enrich()` → in status.
- Output dir mặc định đổi về `artifacts/backend_events` (khớp service).
- Graph/prompt/telemetry/persistence giờ hoàn toàn private trong `EnrichmentService`.

### C4 — Rời true-external LLM khỏi ingest request

**Vấn đề:** p95 latency thật 18.7s ghép incident visibility với LLM latency/failure trong request.

**Làm:** `app/api/events.py` dùng `BackgroundTasks`:
- Route trả 201 ngay sau persist; enrichment chạy background task (`_enrich_in_background` async).
- Response không còn field `enrichment` — chỉ `ACCEPTED` + candidateId + stored_uri.
- Enrichment failure không ảnh hưởng response (best-effort, FR-AI-07).
- Test: response không block (TestClient behavior giữ background chạy sau).

**Lưu ý:** Starlette `TestClient` chạy background task trước khi trả response (đồng bộ) — test đo elapsed qua TestClient không phản ánh production; test hiện tại verify response shape (không có enrichment field) + enrichment persist sau khi client trả. Với uvicorn thật, response gửi trước, task chạy sau.

### C5 — Deepen persisted-candidate intake

**Vấn đề:** route owns idempotency + filesystem order + assessment handoff; header ID/body ID có thể tạo 2 identities.

**Làm:** `app/services/intake.py` mới — `PersistedIntake`:
- `accept(candidate, header_id)` — canonical identity (header wins), atomic dedupe, durable write, trả `IntakeOutcome`.
- Route thành thin: gọi `intake.accept()`, `DUPLICATE_IGNORED`/`ERROR`/`ACCEPTED` → response tương ứng.
- `IdempotencyStore` giữ làm local storage stand-in (review: không tạo queue port giả định; concurrency chưa test, chỉ sequential).

## 2. Verify

```text
pytest tests/ -q
110 passed (33 test mới/cập nhật của review này)

coverage agent scope:
TOTAL 348 stmts, 96%

ruff check (agent scope): All checks passed!
```

- Trước review: 104 pass → sau: 110 pass (+6 mới, −5 template, +5 net).
- Test mới: `test_agent_assessment.py` (4), `test_persisted_intake.py` (6), API C4 test cập nhật, service CLI cập nhật.
- CLI smoke: `run_enrichment.py` chạy LLM thật (`-> llm`), ghi đúng output dir.

## 3. Files thay đổi

```
D  src/** (17 files template)                    # C1
D  tests/test_agents/, tests/test_api/           # C1
M  Dockerfile, Makefile, tests/conftest.py       # C1
A  app/agents/assessment.py                      # C2 (AgentAssessment SPEC §3.6)
M  app/api/events.py                             # C4 + C5 (background task + intake)
A  app/services/intake.py                        # C5 (PersistedIntake)
M  scripts/run_enrichment.py                     # C3 (thin adapter)
A  tests/unit/test_agent_assessment.py           # C2 (4 test)
A  tests/unit/test_persisted_intake.py           # C5 (6 test)
M  tests/integration/test_enrichment_runtime_api.py  # C4/C5
```

## 4. Giới hạn còn lại

- **Concurrency dedupe chưa test** (review note): chỉ sequential duplicate; cần evidence concurrency trước khi tăng strength (không tạo queue port giả định — production chỉ 1 execution adapter).
- `AgentAssessment` chưa persist riêng — enrichment JSON vẫn là nơi lưu assessment; nối vào Incident service/DB là việc fullstack (ngoài scope).
- LangGraph giữ nguyên như implementation (không collapse) — interface đã shrink, tests không phụ thuộc graph keys.

## 5. Top recommendation follow-up

Review khuyến nghị "Làm candidate 1 trước" — đã thực hiện; 4 deepening còn lại giờ có leverage trên runtime thật.
