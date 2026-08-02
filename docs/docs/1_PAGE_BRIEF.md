# 1-Page Executive Brief

**Gate:** Gate 1 — Chốt đề tài
**Team:** Backpropagation · Jira `BAC`
**Owner:** Phạm Văn Tâm — PM / AI Engineer
**Date:** 29/07/2026

## 1. Vision & Problem

Khu đô thị có nhiều camera nhưng số người trực hữu hạn. Việc quan sát thủ công nhiều màn hình 24/7 gây mệt mỏi, bỏ sót sự kiện; sự cố thường chỉ được phát hiện khi xem lại video. Cảnh báo rule-based đơn giản tạo nhiều false positive, làm mất niềm tin của người trực.

## 2. Solution

AI Agent giám sát camera đô thị, tập trung 3 sự kiện core: **Xâm nhập vùng cấm**, **Tụ tập đông**, **Vật thể bỏ quên**. Hệ thống phân tích video (OpenCV/YOLO), Agent (LangGraph/LLM) đánh giá severity và sinh mô tả, cảnh báo realtime tới Dashboard (FastAPI/WebSocket/React). Bắt buộc **Human-in-the-Loop**: mọi escalation nghiêm trọng phải do Manager xác nhận, có đầy đủ audit trail.

## 3. Scope MVP (5 tuần: 28/07–01/09/2026)

- **In scope:** CV detector 3 core events; evidence đã face-blur; FastAPI/Postgres source of truth; React dashboard realtime; RBAC 2 vai trò (Bảo vệ trực / Quản lý an ninh); HITL confirm/dismiss/approve/decline; Incident log; Docker Compose deploy.
- **Out of scope:** Nhận diện danh tính/khuôn mặt cư dân; tự động khóa cổng hoặc gọi lực lượng bên ngoài; escalation không có người xác nhận; fine-tune model mới; Kafka/microservice/multi-region.
- **Stretch:** Té ngã (shadow mode), heatmap, cross-camera tracking không định danh.

## 4. Success Criteria

- **Gate 2 (17/08):** 3 core events chạy end-to-end trên test clips; HITL và incident log hoạt động.
- **Demo Day (01/09):** Live demo ổn định; zero auto-escalation; audit log đầy đủ; có video fallback.
- Giá trị cốt lõi: giảm tải quan sát, rút ngắn thời gian phát hiện/xác minh — AI hỗ trợ, con người quyết định.

## 5. Risks chính

- **Dataset thiếu/không đủ độ phủ** → Audit sớm, dùng clip mô phỏng được phê duyệt.
- **LLM timeout/quota** → Schema validation + deterministic fallback, LLM ngoài critical path.
- **False positive cao** → Rule bảo thủ (ROI/dwell/proximity) + HITL review.
- **Privacy** → Face blur trước persist; redaction fail thì drop artifact, chỉ giữ metadata.
