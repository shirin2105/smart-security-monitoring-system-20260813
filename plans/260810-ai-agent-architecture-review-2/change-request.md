# Change Request — Architecture Review 2: Agent Scope

**CR ID:** CR-AI-20260810-03
**Ngày:** 2026-08-10
**Người đề xuất:** AI Agent Engineer
**Trạng thái:** DRAFT — chờ PM/TL approve
**Nguồn:** `architecture-review-20260810-143703.html`
**Kết quả:** `reports/ai-agent-architecture-review-2.md`

---

## 1. Tóm tắt thay đổi (5 candidates, đều agent scope)

| # | Thay đổi | Commit | Ảnh hưởng |
|---|---|---|---|
| C1 | `AgentAssessment` là canonical result (SPEC §3.6) thay `EnrichmentOutput` | `dbc37dd` | severity cap + action mapping giờ bảo vệ path thật; policy/HITL đọc 1 shape |
| C2 | Canonical identity (header thắng) qua assessment handoff | `dbc37dd` | `enrichment_<canonical>.json` khớp `candidate_<canonical>.json` |
| C3 | Record module: `outputValid` thật, persist error không flip `fallbackUsed` | `a458cc3` | eval `schema_valid_rate` không bị thổi phồng |
| C4 | LLM call async qua `asyncio.to_thread` | `711ff68` | event loop không block (p95 18.7s provider) |
| C5 | Composition root `create_enrichment_service()` | `4c8d095` | `llm_enabled` tới production; route+CLI cùng factory |
| — | Fix eval projection đọc `assessment` key | `6f76190` | eval đúng record mới |

## 2. Tại sao cần

- **C1**: AgentAssessment orphan — domain result không chạm production path.
- **C3**: hard-code `outputValid=True` → provider-invalid đọc thành valid 100%.
- **C4**: sync provider call trên event loop — 300ms fake delay heartbeat 50ms→304ms.

## 3. Ảnh hưởng / rủi ro

| Ảnh hưởng | Đánh giá |
|---|---|
| Record JSON đổi `enrichment` → `assessment` key | **Breaking** cho ai đọc file cũ; client duy nhất là eval (đã sửa) + tooling. Cần note migration nếu có consumer khác. |
| `EnrichmentResult.output` → `.assessment` | Breaking Python API — chỉ code agent scope dùng. |
| `enrich_async` giữ sync `enrich` cho mock | OK MVP; chưa có async provider client thật. |
| Concurrency dedupe chưa test | Giữ từ review 1. |

## 4. Acceptance criteria

- [x] 113/113 test pass (thêm 2: async event loop, header identity).
- [x] Coverage agent scope 93%; ruff clean.
- [x] CLI smoke LLM thật: record 13 field, `outputValid=True`, action đúng.
- [x] Eval projection đọc assessment (fix kèm).

## 5. Quyết định cần PM/TL

1. **Approve** CR (không P0/P1 open).
2. **File format change**: `enrichment` → `assessment` trong record JSON — có consumer ngoài eval không (dashboard/tooling)? Nếu có, cần migration hoặc dual-write ngắn hạn.
3. **Async provider client** thật (`ChatOpenAI` async) — cần trước release không, hay `to_thread` đủ?
4. **Concurrency dedupe** test — chốt trước release.
