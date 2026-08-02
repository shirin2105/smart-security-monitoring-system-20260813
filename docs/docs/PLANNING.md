# Kế hoạch triển khai 5 tuần

> **Team:** T176 · Jira `BAC`
> **Thời gian:** 28/07/2026–01/09/2026
> **Mục tiêu:** Bàn giao MVP AI Agent giám sát camera có 3 sự kiện core, cảnh báo realtime, HITL, incident log và deploy được.
> **Trạng thái tài liệu:** Baseline thực thi v1.0 — cập nhật khi Gate thay đổi scope.

---

## 1. Tóm tắt chiến lược

Team triển khai theo **vertical slice trước, mở rộng sau**:

1. Tuần 1 chốt bài toán, dataset, kiến trúc, API contract và tiêu chí nghiệm thu.
2. Tuần 2 chạy xuyên suốt một sự kiện **xâm nhập vùng cấm** từ video tới dashboard.
3. Tuần 3 mở rộng cùng pipeline sang **tụ tập** và **vật thể bỏ quên**, hoàn thiện HITL và Gate 2.
4. Tuần 4 hardening, đo hiệu năng, deploy production và chuẩn bị hồ sơ.
5. Tuần 5 regression, seed demo, diễn tập và release freeze trước Demo Day.

**Nguyên tắc bảo vệ timeline:**

- 3 sự kiện core là cam kết: xâm nhập, tụ tập, vật thể bỏ quên.
- Té ngã là stretch, không được chặn Gate 2.
- LLM hỗ trợ đánh giá/mô tả/kế hoạch; lỗi LLM không được chặn cảnh báo CV và HITL.
- Mọi escalation nghiêm trọng bắt buộc người trực xác nhận.
- Không mở feature mới sau Gate 2 nếu không thay thế một hạng mục P1/stretch tương đương.

---

## 2. Đội hình và ownership

| Thành viên                  | Vai trò          | Workstream chính                                               | Jira                                                          |
| ----------------------------- | ----------------- | --------------------------------------------------------------- | ------------------------------------------------------------- |
| **Phạm Văn Tâm**     | PM / AI Engineer  | Scope, Gate, risk, LangGraph/LLM, HITL logic, eval, integration | BAC-1, BAC-2, BAC-4; milestone BAC-59, BAC-60, BAC-64, BAC-65 |
| **Trần Đăng Bách**  | CV Engineer       | Dataset, YOLO, tracking, rule engine, evidence, CV eval         | BAC-3, BAC-17, BAC-18, BAC-23→32                             |
| **Ngô Tuấn Hưng**    | Backend / DevOps  | FastAPI, Postgres, WebSocket, RBAC, HITL API, Docker, deploy    | BAC-5, BAC-7, BAC-41→48, BAC-57, BAC-58, BAC-61, BAC-63      |
| **Nguyễn Ngọc Hiệp** | Frontend Engineer | React dashboard, camera grid, realtime alert, HITL UI, timeline | BAC-6, BAC-49→56                                             |

### Quy tắc cân bằng tải

- Mỗi người tối đa một implementation ticket chính đang `In Progress`; bug P0 là ngoại lệ.
- Tâm timebox ceremony tối đa 45 phút/ngày để tránh PM làm nghẽn Agent workstream.
- Hiệp phát triển bằng fixture bám API contract, không đợi WebSocket thật.
- Bách phát triển Event fixture/producer, không đợi Backend hoàn thiện.
- Hưng tập trung event API, HITL, DB, deploy; không nhận feature ngoài critical path.
- Dành khoảng 10–15% công suất cho integration, calibration và lỗi deploy.
- Tuần 2 bảo vệ ít nhất hai integration window (giữa tuần và cuối tuần); ticket P0 không đủ acceptance evidence trước window đầu phải dùng fixture/fallback thay vì dồn toàn bộ tích hợp tới 10/08.

---

## 3. Scope theo ưu tiên

### P0 — bắt buộc Demo Day

- Video/RTSP giả lập có `camera_id` và timestamp.
- 3 detector core: intrusion, crowd, abandoned object.
- Event kèm ảnh bằng chứng/bounding box.
- Agent đánh giá severity, sinh mô tả và action plan có cấu trúc.
- Backend lưu event/incident, push WebSocket.
- 2 vai trò: Bảo vệ trực và Quản lý an ninh.
- HITL confirm/dismiss với actor, timestamp, reason và append-only audit trail.
- Incident timeline/filter cơ bản.
- Docker Compose, deployment, healthcheck, logs và backup/rollback tối thiểu.
- Regression, demo data và video backup.

### P1 — làm khi P0 xanh

- Face blur tự động.
- Agent memory theo khu vực/giờ.
- Heatmap điểm nóng.
- Tối ưu LLM/cache/fallback nâng cao.
- Theo dõi nhiều camera tốt hơn.

### Stretch

- Té ngã.
- Cross-camera tracking/re-identification ở mức đối tượng không định danh.
- Báo cáo/analytics nâng cao.

### Không làm trong MVP

- Nhận diện danh tính/khuôn mặt cư dân.
- Tự khóa cổng, gọi lực lượng bên ngoài hoặc tự escalation không có HITL.
- Fine-tune model mới nếu baseline pretrained + rules đủ cho demo.
- Kafka/RabbitMQ, microservice platform, autoscaling, multi-region.
- SSO/enterprise IAM, mobile app native.
- Cam kết accuracy cho camera/thực địa ngoài tập test công bố.

---

## 4. Critical path

```text
BAC-17, BAC-18 — Dataset audit + YOLO spike
BAC-19, BAC-20 — Agent spike + architecture
BAC-21 — API contract
BAC-22 — Metric/acceptance baseline
        │
        ├─ CV: BAC-23, BAC-24, BAC-25, BAC-28
        ├─ Agent: BAC-33, BAC-34, BAC-35
        ├─ Backend: BAC-41, BAC-42, BAC-43, BAC-44
        └─ Frontend: BAC-49, BAC-50, BAC-51
                      │
                      ▼
              BAC-59 — Intrusion vertical slice
                      │
    BAC-26, BAC-27 + BAC-32 + BAC-36, BAC-39
    BAC-45, BAC-46, BAC-47 + BAC-52, BAC-53, BAC-54
                      │
                      ▼
              BAC-60 — Gate 2 E2E
                      │
    BAC-58 + BAC-61 + BAC-62
                      │
                      ▼
              BAC-63 — Production deploy
                      │
    BAC-56 + BAC-64
                      │
                      ▼
              BAC-65 — Release freeze
```

---

## 5. Timeline chi tiết

## Tuần 1 — Gate 1: Discovery và chốt baseline

**Ngày:** 28/07–03/08/2026
**Weekly outcome:** Scope, users, dataset readiness, architecture, contracts và metric plan đủ rõ để 4 workstream làm song song.

| Ngày     | PM / AI — Tâm                             | CV — Bách                      | Backend/DevOps — Hưng                     | Frontend — Hiệp                      | Deliverable                      |
| --------- | ------------------------------------------- | -------------------------------- | ------------------------------------------- | -------------------------------------- | -------------------------------- |
| 28–29/07 | Problem statement, RACI, scope core/stretch | Kiểm kê dataset/video/hardware | Kiểm tra Docker host, DB, ports, secrets   | User journey và operator flow         | BAC-15, BAC-16, BAC-17 baseline  |
| 30–31/07 | LangGraph/LLM spike, severity/HITL policy   | YOLO/tracker/ROI benchmark       | FastAPI/Postgres/WebSocket skeleton concept | Wireframe + fixture-driven React shell | BAC-18, BAC-19, BAC-49 artifacts |
| 01–02/08 | Architecture, risk register, Gate deck      | Benchmark + data gap report      | Review boundaries/data model                | Review API/UI payload                  | BAC-20 và review notes          |
| 03/08     | Chốt API contract và metric acceptance    | Sign-off CV Event schema         | Khóa repository/branch/bootstrap local     | Sign-off payload/UI states             | BAC-21, BAC-22, BAC-57; Gate 1   |

### Gate 1 — điều kiện PASS

- [ ] Problem statement và 2 personas được thống nhất.
- [ ] 3 event core được định nghĩa bằng rule và ngưỡng cấu hình được.
- [ ] Dataset inventory/gap analysis có owner và kế hoạch xử lý.
- [ ] Event/Alert/Incident/WebSocket contract được version hóa.
- [ ] Metric protocol và baseline target được ghi rõ là `Proposed` nếu chưa benchmark.
- [ ] Hardware/deploy target có fallback.
- [ ] Không còn blocker môi trường không có owner và deadline.

**Không PASS:** không mở rộng detector; chỉ xử lý blocker của contract/vertical slice.

---

## Tuần 2 — MVP đầu tiên: intrusion vertical slice

**Ngày:** 04/08–10/08/2026
**Weekly outcome:** Một clip xâm nhập tạo Event, Alert và Incident end-to-end; dashboard nhận realtime và lưu được evidence.

| Workstream  | Jira   | Deliverable                                                                                          | Due   |
| ----------- | ------ | ---------------------------------------------------------------------------------------------------- | ----- |
| CV          | BAC-23 | Đọc ≥4 video/RTSP giả lập, metadata ổn định                                                  | 06/08 |
| CV          | BAC-24 | YOLO phát hiện người/vật thể, output đúng contract                                           | 07/08 |
| CV          | BAC-25 | Xâm nhập vùng cấm theo ROI/dwell rule                                                            | 09/08 |
| CV          | BAC-28 | Event kèm frame, bbox, confidence; redaction tối thiểu hoặc drop artifact khi chưa privacy-safe | 10/08 |
| Agent       | BAC-33 | LangGraph detect→assess→plan→enrich; không emit/mutate alert/state                               | 06/08 |
| Agent       | BAC-34 | Severity structured output + validation                                                              | 08/08 |
| Agent       | BAC-35 | Mô tả/báo cáo sự cố; fallback rule-based                                                       | 10/08 |
| Backend     | BAC-41 | FastAPI health/config/logging                                                                        | 05/08 |
| Backend     | BAC-42 | Postgres schema + migration                                                                          | 06/08 |
| Backend     | BAC-43 | Event/Incident ingest idempotent                                                                     | 08/08 |
| Backend     | BAC-44 | WebSocket realtime/reconnect support                                                                 | 10/08 |
| Frontend    | BAC-49 | React scaffold/routing/API client                                                                    | 04/08 |
| Frontend    | BAC-50 | Grid ≥4 camera                                                                                      | 09/08 |
| Frontend    | BAC-51 | Alert ảnh+mô tả+severity qua WS                                                                   | 10/08 |
| Integration | BAC-58 | Docker Compose local                                                                                 | 10/08 |
| Integration | BAC-59 | Intrusion vertical slice không mock                                                                 | 10/08 |

### Vertical Slice review — điều kiện PASS

- [ ] Video thật trong tập demo tạo intrusion candidate.
- [ ] Event được persist trước khi push WebSocket.
- [ ] Dashboard hiển thị ảnh, camera, thời gian, severity, description.
- [ ] Incident truy vấn lại được.
- [ ] Duplicate/reconnect không tạo incident trùng ở kịch bản test.
- [ ] LLM lỗi hoặc malformed output dùng fallback và không chặn alert.
- [ ] Latency p50/p95 được đo; target chỉ được coi là Accepted sau baseline.

**Scope cut nếu trễ:** dừng crowd/abandoned object, heatmap, memory, fall; giữ intrusion + DB + WS + evidence.

---

## Tuần 3 — Gate 2: 3 core events + HITL

**Ngày:** 11/08–17/08/2026
**Weekly outcome:** Ba sự kiện core chạy cùng pipeline; 2 vai trò, HITL và incident log hoạt động; eval có số liệu.

| Workstream  | Jira   | Deliverable                                                           | Due                 |
| ----------- | ------ | --------------------------------------------------------------------- | ------------------- |
| CV          | BAC-26 | Crowd theo count + ROI + dwell                                        | 10/08–13/08 harden |
| CV          | BAC-27 | Abandoned object theo stationary/proximity rule                       | 10/08–13/08 harden |
| CV          | BAC-32 | Eval và tune false positive                                          | 15/08               |
| Agent       | BAC-36 | Interrupt/wait cho HITL                                               | 13/08               |
| Agent       | BAC-39 | Rule mapping severity→action plan                                    | 13/08               |
| Backend     | BAC-45 | JWT/RBAC 2 vai trò                                                   | 12/08               |
| Backend     | BAC-46 | Full state/role/scope action matrix + transactional append-only audit | 13/08               |
| Backend     | BAC-47 | Incident log/filter/pagination                                        | 14/08               |
| Frontend    | BAC-52 | Login và role routing                                                | 12/08               |
| Frontend    | BAC-53 | HITL UI đủ Guard/Manager action matrix, chống double-submit        | 14/08               |
| Frontend    | BAC-54 | Timeline/filter/detail                                                | 15/08               |
| Integration | BAC-60 | E2E 3 events + HITL + incident log                                    | 16/08               |
| PM          | BAC-11 | Gate 2 review + feedback backlog                                      | 17/08               |

### Gate 2 — điều kiện PASS

- [ ] Intrusion, crowd và abandoned object đều đang bật và chạy end-to-end trên test clips; abandoned object không được feature-flag off để né Gate.
- [ ] Critical event không thể tự chuyển `CONFIRMED` hoặc thực hiện escalation.
- [ ] Full state/role/scope action matrix PASS: Guard acknowledge/resolve/dismiss INFO/WARNING + request; Manager thêm confirm/dismiss HIGH/CRITICAL, resolve event đã confirm và approve/decline escalation trong app.
- [ ] Mọi action matrix transition có actor, timestamp và reason theo policy; `EventAction` và `AuditLog` append-only ghi cùng transaction.
- [ ] Hai role và site/camera scope bị giới hạn đúng quyền trên REST, artifact và WebSocket; cross-scope negative tests PASS.
- [ ] Incident log/filter hoạt động.
- [ ] Eval set được tách khỏi tuning set.
- [ ] Precision/recall/false-alert/latency được báo cáo kèm sample size và hardware.
- [ ] Không có lỗi Critical/High chưa có disposition.

### Điều kiện mở stretch té ngã BAC-30

Chỉ bắt đầu nếu:

- BAC-59 PASS.
- Ba core detector không có blocker P0.
- HITL chain đã hoạt động.
- Dataset fall đủ để eval tối thiểu và Mentor/PM đồng ý dùng contingency.

---

## Tuần 4 — Hardening, deploy và hồ sơ

**Ngày:** 18/08–24/08/2026
**Weekly outcome:** Release candidate chạy trên môi trường target, có monitoring, privacy/security baseline, backup/rollback và hồ sơ.

| Jira           | Owner             | Deliverable                                                                                                        | Due       |
| -------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------ | --------- |
| BAC-29         | Bách             | Productionize face blur: tăng độ phủ/hiệu năng và kiểm thử privacy gate đã áp dụng từ vertical slice | 19/08     |
| BAC-61         | Hưng + Tâm      | Security/privacy hardening                                                                                         | 22/08     |
| BAC-62         | Tâm điều phối | Đo/tối ưu latency end-to-end                                                                                    | 22/08     |
| BAC-63         | Hưng             | Deploy + healthcheck + monitoring + backup                                                                         | 24/08     |
| BAC-40         | Tâm              | LLM timeout/cache/fallback nếu cần                                                                               | 22/08     |
| BAC-48, BAC-55 | Hưng + Hiệp     | Heatmap chỉ khi P0 xanh                                                                                           | 20–21/08 |
| BAC-13         | Tâm              | Hồ sơ doanh nghiệp/tài liệu Demo                                                                              | 24/08     |

### Deploy Gate — điều kiện PASS

- [ ] Fresh deploy lặp lại được từ tài liệu.
- [ ] Migration, health/readiness và logs hoạt động.
- [ ] Backup/restore hoặc rollback tối thiểu được diễn tập.
- [ ] Secrets không nằm trong source/image/log.
- [ ] RBAC/HITL negative tests PASS, gồm cross-site/cross-camera REST, artifact và WebSocket denial.
- [ ] Mọi evidence persist/serve đã redaction `COMPLETE`; redaction fail luôn drop artifact. Access control/no-store/audit là lớp bắt buộc bổ sung, không thay thế redaction.
- [ ] Retention được owner phê duyệt trước pilot và scheduled-deletion test PASS.
- [ ] `EventAction`/`AuditLog` append-only; human security decision ghi cùng transaction với state transition.
- [ ] Known limitations, model/eval report và operator SOP được hoàn tất.

**Scope cut nếu deploy trễ:** bỏ public/cloud exposure, heatmap, multi-camera nâng cao; giữ một Docker host ổn định.

---

## Tuần 5 — Demo readiness và release freeze

**Ngày:** 25/08–01/09/2026
**Weekly outcome:** Hai rehearsal xanh; release candidate được freeze; live demo và video fallback sẵn sàng.

| Jira   | Owner       | Deliverable                                 | Due   |
| ------ | ----------- | ------------------------------------------- | ----- |
| BAC-56 | Hiệp       | UI polish + empty/loading/error states      | 28/08 |
| BAC-64 | Tâm + team | Seed deterministic demo data + backup video | 28/08 |
| BAC-65 | Tâm + team | Final E2E regression + freeze               | 31/08 |
| BAC-14 | Tâm        | Demo script, phân vai, rehearsal           | 01/09 |

### Lịch rehearsal

- **26/08:** Rehearsal #1 — full flow, ghi lỗi P0/P1.
- **27/08:** Resilience — LLM timeout, WS reconnect, video/evidence unavailable.
- **28/08:** Rehearsal #2 — stakeholder/proxy; khóa UI/config/image/data.
- **31/08:** UAT cuối, snapshot, credentials/network checklist.
- **01/09:** Demo Day.

### Demo Day PASS

- [ ] 3 core event clips deterministic.
- [ ] Operator nhận alert, xem evidence và thực hiện các action đại diện được phép theo full state/role/scope matrix.
- [ ] Audit/incident history hiển thị được.
- [ ] LLM assistance được mô tả đúng là hỗ trợ, không tự quyết định.
- [ ] Local Docker fallback và video backup đã thử.
- [ ] Team công bố rõ scope, dataset, hardware và giới hạn accuracy.

---

## 6. Trạng thái và state machine

### Event/Incident lifecycle

```text
DETECTED → ASSESSED → ALERTED

INFO/WARNING:
OPEN → ACKNOWLEDGED → RESOLVED | DISMISSED

HIGH/CRITICAL:
PENDING_REVIEW → CONFIRMED → RESOLVED
               → DISMISSED
               → EXPIRED
```

### Escalation lifecycle — chỉ trong ứng dụng

```text
NONE → REQUESTED → APPROVED | DECLINED
```

`APPROVED` chỉ ghi nhận quyết định có audit trong ; MVP không gửi notification ra ngoài hoặc điều khiển thiết bị vật lý.

**Quy tắc:**

- CV chỉ tạo candidate; Agent chỉ đánh giá/đề xuất.
- Guard được acknowledge/resolve/dismiss INFO/WARNING và request escalation trong site/camera scope; Manager có các quyền đó, đồng thời mới confirm/dismiss HIGH/CRITICAL, resolve event đã confirm và approve/decline escalation.
- Mọi action phải PASS state, role và site/camera scope; allow/deny matrix được unit/E2E test.
- Không CV worker, Agent, service account hoặc scheduler nào được tự confirm/approve hoặc thực hiện hành động ngoài hệ thống.
- Review quá hạn chỉ chuyển overdue/expired và cảnh báo người trực; không auto-escalate.
- Mọi state transition phải có timestamp; human security decision phải có actor/reason và append-only `EventAction`/`AuditLog` trong cùng transaction.
- Duplicate Event phải idempotent.
- LLM timeout/schema error không làm mất Event; dùng fallback.
- Evidence chỉ được persist/serve sau khi redaction/face blur thành công; nếu thất bại phải drop artifact và giữ metadata được phép.

---

## 7. Test và evaluation strategy

| Tầng       | Nội dung                                                                                            | Owner                | Gate           |
| ----------- | ---------------------------------------------------------------------------------------------------- | -------------------- | -------------- |
| Unit        | ROI, dwell, count, stationary/proximity rules; state transition; idempotency; validation; UI reducer | Bách/Hưng/Hiệp    | Gate 2         |
| Contract    | CV Event ↔ FastAPI ↔ WS ↔ React                                                                   | Cả team, Hưng lead | Vertical slice |
| Integration | API+DB migration, evidence, WS reconnect, transactional HITL, audit                                  | Hưng                | Gate 2         |
| Agent eval  | Severity consistency, structured-output validity, fallback, no autonomous action                     | Tâm                 | Gate 2         |
| E2E         | 3 core events; Guard/Manager action matrix; role/scope deny; LLM outage                              | Hiệp + Tâm         | Gate 2         |
| CV eval     | Positive/negative clips, event-level precision/recall/FPR                                            | Bách + Tâm         | Gate 2         |
| Deploy/ops  | Fresh start, config validation, health, backup/restore/rollback                                      | Hưng                | Deploy Gate    |
| UX/a11y     | Keyboard, focus, error states, responsive                                                            | Hiệp                | Release freeze |

### Proposed evaluation floor — chưa phải cam kết cho tới BAC-22

- Recall mỗi core event: đề xuất ≥5/6 positive scenarios.
- Candidate precision toàn hold-out: đề xuất ≥75%.
- False-alert rate: đề xuất ≤2 candidate/camera-hour trên nominal clips.
- Event-eligible → browser p95: đề xuất <5 giây trên cấu hình demo.
- Soak: 45 phút không crash, không mất Event đã accepted bởi backend.

### Non-negotiable release invariants

- Zero auto-confirm/auto-approve; 100% human security decisions có append-only action/audit.
- Zero persisted/served evidence khi redaction chưa `COMPLETE` hoặc thất bại.
- Zero unauthorized cross-site/cross-camera REST, artifact hoặc WebSocket access trong negative tests.
- HITL state transition và audit commit trong cùng transaction.

Các invariant này không phụ thuộc BAC-22/BAC-62. Mọi performance/evaluation số liệu phải kèm dataset version, sample size, video properties và hardware; không suy rộng ra thực địa.

---

## 8. Nhịp quản trị

| Nhịp                   |              Thời lượng | Nội dung                                          |
| ----------------------- | -------------------------: | -------------------------------------------------- |
| Daily stand-up          |                   15 phút | Outcome hôm qua, blocker, critical path hôm nay  |
| Daily integration slot  |               20–30 phút | Smoke test artifact mới; contract mismatch        |
| Build Hours từ Tuần 3 | Theo lịch chương trình | Pair xử lý integration/bug P0                    |
| Risk review             |       Thứ Tư + Thứ Sáu | RAG, scope creep, data/privacy, contingency        |
| Weekly review           |                Cuối tuần | Demo evidence, metrics, carry-over, plan tuần sau |
| Gate review             |                  Mốc Gate | PASS / Conditional / FAIL với decision log        |

### Jira policy

- `To Do` → chỉ khi Definition of Ready đạt.
- `In Progress` → owner đang thực hiện, tối đa một implementation item/người.
- `In Review` → có artifact/PR/test evidence và người review.
- `Done` → acceptance criteria PASS; không Done chỉ vì “đã làm”.
- Blocker tồn tại >1 ngày phải có escalation/mitigation.

---

## 9. Risk register

| Risk                                     | Xác suất | Ảnh hưởng | Mitigation                                            | Trigger cắt scope               | Owner         |
| ---------------------------------------- | ---------: | -----------: | ----------------------------------------------------- | -------------------------------- | ------------- |
| Dataset không đủ/không được phép |          M |            H | Audit, version manifest, clip mô phỏng              | Không có clip core tới Gate 1 | Bách + Tâm  |
| Tracking làm crowd/abandoned sai        |          H |            H | Rule đơn giản, ROI/dwell/proximity, hard negatives | Pilot không đạt trước 14/08 | Bách         |
| Backend/DevOps bottleneck                |          M |            H | Contract-first, fixture/mock adapter                  | CV/FE chờ API >1 ngày          | Hưng + Tâm  |
| Tâm quá tải PM+AI                     |          M |            H | Timebox PM, LLM ngoài critical path                  | Agent block integration          | Tâm          |
| LLM timeout/hallucination                |          M |            H | Schema, timeout, fallback, metadata-only              | Lỗi chặn alert                 | Tâm          |
| Latency không đạt hardware            |          M |            H | Benchmark sớm, hạ FPS/resolution                    | p95 vượt target                | Bách + Hưng |
| HITL bypass/audit thiếu                 |          L |     Critical | Backend enforce state, negative tests                 | Bất kỳ auto-confirm            | Tâm + Hưng  |
| PII/secret bị lộ                       |          L |     Critical | Face blur, RBAC, env secrets, redact logs             | Bất kỳ exposure                | Bách + Hưng |
| Deploy không reproducible               |          M |            H | Docker, health, runbook, rollback drill               | Fresh deploy fail Tuần 4        | Hưng         |
| Scope creep từ backlog                  |          H |            H | P0 cap, change budget, scope-cut ladder               | Gate at risk                     | Tâm          |

---

## 10. Scope-cut ladder

| Trigger                           | Cắt trước                                       | Không được cắt                                   |
| --------------------------------- | -------------------------------------------------- | ----------------------------------------------------- |
| Gate 1 chưa khóa data/contract  | RTSP live, multi-camera                            | MP4, API contract, intrusion POC                      |
| BAC-59 chưa PASS 10/08           | Crowd/abandoned tạm dừng, LLM nâng cao, heatmap | Intrusion end-to-end, DB, WS, evidence                |
| Abandoned object không ổn 14/08 | Owner association phức tạp                       | Conservative “stationary object cần review” + HITL |
| Gate 2 lỗi P0                    | Fall, memory, heatmap, tracking nâng cao          | 3 core, HITL, audit, deploy hardening                 |
| Deploy chưa ổn 20/08            | Public exposure, nhiều camera                     | Một Docker host, health, backup/rollback             |
| Sau 24/08                         | Mọi feature mới/redesign                         | Security/data-loss/demo-blocker fixes                 |

---

## 11. Deliverables cuối cùng

- [ ] Source repository và hướng dẫn Quick Start.
- [ ] Architecture diagram + API contract/OpenAPI.
- [ ] Dataset manifest/audit + evaluation report.
- [ ] CV/Agent/Backend/Frontend MVP.
- [ ] Docker Compose và production runbook.
- [ ] Security/privacy checklist; HITL SOP.
- [ ] Test report và known limitations.
- [ ] Business/competition dossier.
- [ ] Demo script, seed data và backup video.
- [ ] Release tag/image và rollback procedure.

---

## 12. Open decisions cần khóa

| Quyết định                    |                               Deadline | Owner         | Fallback                                  |
| -------------------------------- | -------------------------------------: | ------------- | ----------------------------------------- |
| Hardware target/GPU availability |                                 Gate 1 | Hưng + Bách | 1 stream 720p, sampled FPS                |
| LLM provider/model/budget        |                                 Gate 1 | Tâm          | Rule-based summary                        |
| Vector DB                        | Sau Gate 2 hoặc khi memory được GO | Tâm          | Postgres/pgvector hoặc bỏ memory        |
| Evidence storage/retention       |                        Gate 1–Tuần 2 | Hưng + PM    | Local protected path, demo-only retention |
| Severity thresholds/policy       |                                 BAC-22 | Tâm + Mentor | Conservative default + HITL               |
| Cloud/public deploy target       |                        Trước Tuần 4 | Hưng         | Một Docker host/local LAN                |

---

_Last updated: 28/07/2026 · Owner: Phạm Văn Tâm_
