# GitHub Repo Setup & AI Usage Log — VigiCity AI

> **Gate 1 deliverable** · Team Backpropagation · Jira `BAC` · 02/08/2026
> **Repo:** https://github.com/AI20K-Build-Phase-Cohort-3/P-176
> AI Assistant: Claude Code · Owner log: Phạm Văn Tâm

---

## 1. Repo hiện trạng

Team dùng **AI20K Agent Template** chính thức của chương trình làm nền, fork về repo nhóm `P-176`.

```text
P-176/                                     (trạng thái sau commit 9432739)
├── src/
│   ├── agents/           # LangGraph: graph.py, state.py, nodes/, tools/
│   ├── api/              # FastAPI: routes.py
│   ├── models/           # Pydantic schemas
│   ├── services/         # LLM service
│   ├── config.py         # Pydantic Settings
│   └── main.py           # App entry point
├── tests/                # pytest suite
├── scripts/              # AI logging hooks (Claude/Cursor/Codex/Gemini/Antigravity/Copilot)
├── .ai-log/              # Auto AI usage logs (hook submit khi git push)
├── .github/workflows/ci.yml   # CI: ruff check + pytest trên Python 3.11
├── docs/
│   ├── guide/            # Technical guidebook 10 chương + anti-patterns + checklists
│   └── docs/             # Deliverables Gate 1: PRD, SPEC, PLANNING, 1_PAGE_BRIEF,
│                         #   WIREFRAME_UI_FLOW, GITHUB_REPO_SETUP_AI_LOG, TONG_QUAN_DU_AN.pdf
├── .env.example          # Placeholder: LLM key, DATABASE_URL, AI_LOG server/key
├── Dockerfile            # Multi-stage build
├── docker-compose.yml
├── Makefile              # run / test / lint / format / typecheck / check
├── requirements.txt
├── ruff.toml
├── README.md             # Template quick-start
├── ARCHITECTURE.md
├── JOURNAL.md            # Weekly journal (cần điền theo tuần)
└── WORKLOG.md            # Daily worklog (cần điền theo ngày)
```

## 2. Setup đã thực hiện

- [x] Clone template về repo nhóm `P-176` (org `AI20K-Build-Phase-Cohort-3`), remote `origin` đã trỏ đúng.
- [x] Commit `Initial commit` (template, 24/07) + commit `Add comprehensive project documentation for AI Security Surveillance System` (02/08) — thêm bộ docs Gate 1 vào `docs/docs/`.
- [x] `.gitignore` có sẵn: `.env`, `__pycache__`, model/data artifacts.
- [x] `.env.example` đầy đủ placeholder: `OPENAI_API_KEY`, `DATABASE_URL`, `AI_LOG_SERVER`/`AI_LOG_API_KEY` (giá trị trong file chỉ là placeholder theo template).
- [x] CI skeleton chạy được: GitHub Actions — ruff lint + pytest, triggers push `main/develop` và PR `main`.
- [x] Makefile: `run`, `test`, `lint`, `format`, `typecheck`, `check`.
- [x] AI logging hooks của chương trình: `.claude/`, `.cursor/`, `.codex/`, `.gemini/`, `.agents/`, `.github/hooks/` — auto-log prompt khi dùng AI tools, submit qua `scripts/submit_log.py`.
- [ ] `JOURNAL.md` / `WORKLOG.md`: điền theo tuần/ngày từ Tuần 2.
- [ ] Docs Gate 1 hiện đặt lồng ở `docs/docs/` — cân nhắc đưa lên `docs/` khi dọn cấu trúc Tuần 2.

**Ghi chú trung thực:** `src/` hiện là **code mẫu của template** (LangGraph + FastAPI skeleton), chưa phải implementation VigiCity AI. SPEC VigiCity AI (`docs/docs/SPEC.md`) chỉ đường cho thiết kế mục tiêu (`apps/api`, `apps/web`, `workers/cv`); team sẽ scaffold dần trên nền `src/` và template structure từ Tuần 2. Không claim commands VigiCity AI chạy được ngoài những gì template cung cấp (`make run`, `make test`, CI).

## 3. AI Usage Log

| Ngày | Mục đích | Tóm tắt prompt | Output AI | Người kiểm chứng |
|---|---|---|---|---|
| 28/07 | Soạn PRD | "Soạn PRD production-grade bằng tiếng Việt" (bối cảnh/quyết định đã chốt, yêu cầu FR IDs + acceptance + traceability, cấm ghi khống metric/demo) | Draft PRD ~770 dòng: problem/personas/MoSCoW/FR-NFR/privacy/traceability | Tâm rà từng section, chỉnh scope |
| 28/07 | Kế hoạch 5 tuần | "Lập implementation plan 5 tuần vertical-slice trước, map Jira BAC, gate criteria" | PLANNING.md: timeline + risk register + scope-cut ladder | Tâm + team trong gate deck |
| 28/07 | SPEC | "Tạo SPEC.md objective/commands/structure/style/testing/boundaries" | SPEC.md (Proposed baseline) | Tâm |
| 29/07 | Review chéo | "Review semantic consistency PRD ↔ plan ↔ SPEC" | Phát hiện 2 Critical + 6 High: escalation `SENT/FAILED` mâu thuẫn in-app-only; metric Proposed trùm invariant privacy/HITL; thiếu BAC-31/57 traceability; append-only audit chưa testable; thiếu site/camera scope; Gate 2 né được bằng feature flag; retention chưa gate | Tâm fix toàn bộ; reviewer verify — **APPROVE** |
| 29/07 | Deliverables Gate 1 | "Viết file còn thiếu cho Gate 1" | 1_PAGE_BRIEF.md, WIREFRAME_UI_FLOW.md, GITHUB_REPO_SETUP_AI_LOG.md | Tâm |
| 02/08 | Dịch SPEC | "Viết SPEC bằng tiếng Việt" | SPEC.md tiếng Việt đầy đủ, giữ nguyên invariants | Tâm |
| 02/08 | Đưa docs lên repo | "Đọc repo P-176 và viết lại AI log khớp thực tế" | Bản log này + commit docs vào `docs/docs/` | Tâm |

Ngoài bảng trên, hooks trong repo tự động log prompt vào `.ai-log/` khi team dùng Claude Code/Cursor/Copilot...; logs này được submit qua script của BTC.

### Nguyên tắc khi dùng AI (team cam kết)

1. AI viết nháp → **con người rà soát, quyết định cuối**. Không merge output AI mà chưa đọc.
2. Metric/model accuracy chỉ ghi `Proposed` tới khi benchmark thật (BAC-22/62); không để AI tự sinh số liệu thành "cam kết".
3. Security/privacy/HITL invariant không nhờ AI quyết định — nguồn chân lý là PRD.
4. Dữ liệu nhạy cảm (credential, PII, raw footage) **cấm đưa vào LLM** — chỉ metadata kiểm soát.
5. Artifact AI-generated hiển thị tới người dùng trên dashboard phải gắn nhãn.

## 4. Deliverable Map (nộp 1 link)

| Deliverable trong form | Đường dẫn trong repo |
|---|---|
| Brief | `docs/docs/1_PAGE_BRIEF.md` |
| PRD | `docs/docs/PRD.md` |
| Wireframe/UI Flow | `docs/docs/WIREFRAME_UI_FLOW.md` |
| Github Repo Setup + AI Log | `docs/docs/GITHUB_REPO_SETUP_AI_LOG.md` (file này) |
| Tổng quan bổ sung | `docs/docs/TONG_QUAN_DU_AN.pdf`, `PLANNING.md`, `SPEC.md` |

**Link nộp:** https://github.com/AI20K-Build-Phase-Cohort-3/P-176
