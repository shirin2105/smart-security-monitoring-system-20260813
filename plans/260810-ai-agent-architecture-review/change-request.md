# Change Request — Architecture Review Agent Candidates

**CR ID:** CR-AI-20260810-02
**Ngày:** 2026-08-10
**Người đề xuất:** AI Agent Engineer
**Trạng thái:** DRAFT — chờ PM/TL approve
**Nguồn:** `architecture-review-20260810-115623.html` (5 candidates)
**Kết quả:** `reports/ai-agent-architecture-review.md`

---

## 1. Tóm tắt thay đổi

5 candidates từ architecture review, tất cả thuộc agent scope, đã thực hiện đủ:

| CR | Thay đổi | Ảnh hưởng |
|---|---|---|
| CR-1 | Xóa `src/` template (chat boilerplate), Docker/Makefile → `app.main` | Deployment giờ chạy implementation thật |
| CR-2 | Thêm `AgentAssessment` (SPEC §3.6) tại seam Incident | Đúng contract docs; action allow-list; severity cap |
| CR-3 | CLI thành thin adapter; graph private trong service | Interface shrink; tests không phụ thuộc graph keys |
| CR-4 | Enrichment chạy background task, response không block LLM | Ingest 201 ngay; p95 18.7s không ảnh hưởng visibility |
| CR-5 | `PersistedIntake` module: identity + dedupe + durable write | Route thin; header ID canonical |

## 2. Tại sao cần

- **CR-1**: deployment + tests đi qua template không phải implementation — mọi cải thiện sau không có leverage.
- **CR-2**: docs khóa `Incident → AgentAssessment`; implementation lệch (taxonomy nở ngoài 3 event MVP).
- **CR-4**: latency LLM thật p95 18.7s gắn vào request — incident visibility phụ thuộc provider.

## 3. Ảnh hưởng / rủi ro

| Ảnh hưởng | Đánh giá |
|---|---|
| Xóa `src/` — có gì dùng? | Chỉ template; không module nào import `src.*` còn lại. `git history` giữ nguyên. |
| Response ingest bỏ field `enrichment` | Breaking với client cũ đọc field này — nhưng field mới thêm 1 ngày, client duy nhất là CV worker (không đọc response body sâu). |
| Enrichment giờ chạy async | Assessment không có trong response; client đọc file enrichment riêng. |
| Concurrency dedupe chưa test | Chỉ sequential test; review ghi rõ cần evidence trước khi tăng strength. |
| Không đụng CV/fullstack | ✅ chỉ `app/agents`, `app/services`, `app/api/events.py`, scripts, Dockerfile/Makefile |

## 4. Acceptance criteria

- [x] 110/110 test pass (6 mới: AgentAssessment 4 + PersistedIntake 6; −5 template).
- [x] Coverage agent scope 96%.
- [x] ruff clean agent scope.
- [x] Deployment trỏ `app.main`; smoke CLI chạy LLM thật.
- [x] Ingest response không block LLM; assessment persist background.
- [x] Deletion test C1: template xóa, domain không mất.

## 5. Quyết định cần PM/TL

1. **Approve** CR này (không P0/P1 open).
2. **Client contract**: bỏ field `enrichment` khỏi ingest response — CV worker/UI có cần không? Nếu cần, thêm endpoint GET assessment riêng (đề xuất).
3. **AgentAssessment persist**: nối vào Incident service/DB (fullstack scope) — xác nhận ai làm, khi nào.
4. **Concurrency dedupe**: có cần test trước release không (hiện chỉ sequential)?
