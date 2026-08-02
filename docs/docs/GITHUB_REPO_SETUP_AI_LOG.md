# GitHub Repo Setup & AI Usage Log

> **Gate 1 deliverable** · Team Backpropagation · Jira `BAC` · 29/07/2026

---

## 1. Repository Plan

```text
P-176/
├── apps/
│   ├── api/            # FastAPI + RBAC + HITL + WebSocket + LangGraph enrichment
│   └── web/            # React dashboard
├── workers/
│   └── cv/             # OpenCV + YOLO + tracking + rules + redaction
├── packages/
│   └── contracts/      # EventCandidate/API/WS schemas + fixtures (versioned)
├── infra/
│   ├── docker/         # compose, proxy, health config
│   └── migrations/     # Postgres migrations
├── tests/
│   ├── contract/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
├── docs/
│   ├── PRD.md
│   ├── SPEC.md
│   ├── IMPLEMENTATION_PLAN_5_WEEKS.md
│   ├── 1_PAGE_BRIEF.md
│   ├── WIREFRAME_UI_FLOW.md
│   └── GITHUB_REPO_SETUP_AI_LOG.md
├── .env.example        # placeholder only, no secrets
├── compose.yaml
└── README.md
```

## 2. Setup Checklist

- [x] Cấu trúc monorepo chốt theo SPEC.md §3 (modular monolith + 1 CV worker).
- [x] `.gitignore` chuẩn bị: Python, Node, `dist/`, `.env`, model weights, evidence artifacts, `__pycache__`.
- [x] `.env.example`: chỉ tên biến + placeholder (DB URL, JWT secret, LLM endpoint, camera credentials ref) — không secret thật.
- [x] README: quick start sau khi scaffold (target `make bootstrap` → `make dev`).
- [x] Branch convention: `main` (protected), `feat/<scope>-<ticket>` ví dụ `feat/cv-bac-25`, PR review bắt buộc.
- [x] Jira mapping: mỗi PR link ticket `BAC-xx`; Done chỉ khi acceptance evidence PASS.
- [ ] Repo GitHub tạo + push đầu (owner: Hưng thực hiện, BAC-57, due 03/08).
- [ ] CI skeleton (lint/typecheck/test placeholder) sau scaffold Tuần 2.

**Kỳ vọng trung thực:** repo hiện mới ở mức conventions + docs; source code scaffold sau khi SPEC được approve (SPEC.md đang `Proposed — approval required before scaffolding`). Không claim make/test chạy được trước khi code tồn tại.

## 3. AI Usage Log

Cách dùng AI trong Gate 1, ghi đủ để mentor kiểm chứng được.

| Ngày | Mục đích | Tóm tắt prompt | Output AI | Người kiểm chứng |
|---|---|---|---|---|
| 28/07 | Soạn PRD | "Soạn PRD production-grade bằng tiếng Việt" (đầy đủ bối cảnh/quyết định đã chốt, yêu cầu FR IDs + acceptance + traceability, cấm ghi khống metric/demo) | Draft PRD ~700 dòng, đủ section problem/persona/MoSCoW/NFR/privacy/traceability | Tâm rà từng section, chỉnh wording scope |
| 28/07 | Kế hoạch 5 tuần | "Lập implementation plan 5 tuần vertical-slice trước, map Jira BAC, gate criteria" | IMPLEMENTATION_PLAN_5_WEEKS.md, timeline + risk + scope-cut ladder | Tâm + team review trong gate deck |
| 28/07 | SPEC | "Tạo SPEC.md objective/commands/structure/style/testing/boundaries, hướng dẫn scaffold" | SPEC.md (Proposed baseline) | Tâm |
| 29/07 | Review chéo | "Review semantic consistency PRD ↔ plan ↔ SPEC" | Phát hiện 2 Critical + 6 High: escalation state `SENT/FAILED` mâu thuẫn in-app-only; metric Proposed trùm cả invariant privacy/HITL; thiếu BAC-31/57 traceability; append-only audit chưa testable; site/camera scope vắng; Gate 2 có thể bị né bằng feature flag; retention chưa gate | Tâm fix toàn bộ, reviewer verify — kết quả **APPROVE** |
| 29/07 | Brief/Wireframe/Repo log | "Viết file còn thiếu cho deliverable Gate 1" | 1_PAGE_BRIEF.md, WIREFRAME_UI_FLOW.md, file log này | Tâm |

### Nguyên tắc khi dùng AI (team cam kết)

1. AI viết nháp → **con người rà sóat, quyết định cuối**. Không merge output AI mà chưa đọc.
2. Metric/model accuracy chỉ ghi `Proposed` tới khi benchmark thật (BAC-22/62); không để AI tự sinh số liệu thành "cam kết".
3. Security/privacy/HITL invariant không nhờ AI quyết định — nguồn chân lý là PRD §11.2.
4. Prompt có dữ liệu nhạy cảm (credential, PII, raw footage) **cấm đưa vào LLM** — chỉ metadata kiểm soát (SPEC §6).
5. Mọi artifact AI-generated trong repo gắn nhãn khi hiển thị của người dùng (đặc biệt mô tả sự cố trên dashboard).
