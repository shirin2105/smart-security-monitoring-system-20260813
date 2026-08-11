# Report — Architecture Review 2: Agent Scope

**Ngày:** 2026-08-10
**Nguồn:** `architecture-review-20260810-143703.html` (5 candidates, 49 focused tests pass, post-refactor `0ce3c3c`)
**Vai trò:** AI Agent Engineer — chỉ agent scope.
**Branch:** `agents`

---

## 1. Kết quả từng candidate

| # | Candidate | Strength | Quyết định | Commit |
|---|---|---|---|---|
| 1 | AgentAssessment canonical result | Strong | **Làm** | `dbc37dd` |
| 2 | Canonical identity qua assessment | Strong | **Làm** | `dbc37dd` |
| 3 | Deepen assessment record | Strong | **Làm** | `a458cc3` |
| 4 | Deepen remote execution (async LLM) | Strong | **Làm** | `711ff68` |
| 5 | Own runtime composition | Worth exploring | **Làm** | `4c8d095` |

### C1 — AgentAssessment là canonical result

**Vấn đề:** runtime consume `EventCandidate` → persist `EnrichmentOutput`; `AgentAssessment` orphan — xóa nó không đổi production behavior, severity cap/action mapping không bảo vệ path thật.

**Làm:**
- `EnrichmentResult.output` → `EnrichmentResult.assessment` (AgentAssessment).
- Record JSON giờ lưu `assessment` (13 fields SPEC §3.6) thay vì `enrichment`.
- `event_type` enum normalize sang `.value`.

### C2 — Canonical identity qua assessment

**Vấn đề:** intake chọn header ID nhưng route enrich candidate body ID → `candidate_header-id.json` cạnh `enrichment_body-id.json`.

**Làm:**
- `PersistedIntake.canonical_candidate()` — copy candidate mang canonical identity (header wins).
- Route enrich bản canonical → enrichment file + `incident_id` khớp canonical.
- Test: `test_header_identity_flows_to_enrichment_file`.

### C3 — Deepen assessment record

**Vấn đề:** persistence hard-code `outputValid=True`, write error flip `fallbackUsed` → provider-invalid có thể đọc thành `schema_valid_rate 1.0`.

**Làm:**
- `app/services/assessment_record.py`: `AssessmentRecordStore.save()` + `load()`; `ProviderOutcome` tách `output_valid`/`fallback_used`.
- Service persist qua record store; persist error riêng, không flip fallback.
- Test: `test_enrich_provider_invalid_reports_output_valid_false`, `test_enrich_persist_failure_does_not_raise` (giờ assert `fallback_used is False`).

### C4 — Deepen remote execution

**Vấn đề:** async BackgroundTask gọi sync `ChatOpenAI.invoke` trên event loop — 300ms fake call delay heartbeat 50ms→304ms; broad catch nuốt failure.

**Làm:**
- `LLMAdapter.enrich_async()` — `asyncio.to_thread` đẩy blocking invoke ra worker thread.
- Graph `llm_node` await `enrich_async`.
- Test: `test_enrich_async_does_not_block_event_loop` — ticker đếm 0.5s trong lúc provider sleep 0.3s, assert ≥5 ticks.

### C5 — Own runtime composition

**Vấn đề:** route + CLI dựng runtime khác nhau; tests monkeypatch globals; `settings.llm_enabled` không tới production service.

**Làm:**
- `create_enrichment_service()` — composition root: config (`llm_enabled`), adapter, storage assemble một nơi.
- Route + CLI dùng factory; tests inject adapter.
- Xóa `_persist`/`ENRICHMENT_SUFFIX` dead trong service.

## 2. Verify

```text
pytest tests/ -q
113 passed (trước review 110 → +3 net; thêm 2 test mới)

coverage agent scope: 93%
ruff check agent scope: All checks passed!

CLI smoke (LLM thật):
[run_enrichment] cam_01-ZONE_INTRUSION-restricted_gate-1 -> llm -> enrichment_cam_01-...json
assessment keys: 13 fields (schema_version..created_at)
severity: high | action: request_guard_verification
outputValid: True | fallbackUsed: False
```

## 3. Files thay đổi

```
M  app/services/enrichment.py          # C1: assessment canonical; C3: record store; C5: factory
A  app/services/assessment_record.py   # C3
M  app/agents/assessment.py            # C1 (severity/action)
M  app/agents/graph.py                 # C4: await enrich_async
M  app/llm/adapter.py                  # C4: enrich_async
M  app/services/intake.py              # C2: canonical_candidate
M  app/api/events.py                   # C2 + C5
M  scripts/run_enrichment.py           # C5
M  tests/unit/test_enrichment_service.py, test_llm_adapter.py
M  tests/integration/test_enrichment_runtime_api.py
```

## 4. Giới hạn còn lại

- `enrich_async` vẫn giữ sync `enrich` (test mock dùng sync); chưa có async provider client thật (OpenAI async `ChatOpenAI` chưa dùng) — `to_thread` là đủ cho MVP.
- Record eval projection (`enrichment_eval.py`) vẫn đọc `enrichment` key cũ — cần cập nhật song song (C3 nói "evaluation projection" nhưng file chưa đổi; kiểm tra: nó đọc `payload.get("enrichment")` → giờ `assessment`). **TODO: cập nhật `enrichment_eval.py` đọc `assessment` field.**
- Concurrency dedupe chưa test (giữ từ review 1).
- LangGraph giữ nguyên (không collapse).

## 5. Top recommendation follow-up

"C1 trước" — đã làm; 4 deepening còn lại leverage qua domain result `AgentAssessment`.
