package vn.t176.patrol.data.repository

import vn.t176.patrol.domain.PatrolAction
import vn.t176.patrol.domain.model.SecurityEvent

/**
 * Ghi hành động của người ở hiện trường — tương ứng
 * `POST /api/v1/events/{id}/actions` trong contract mục 6.1.
 *
 * Ba ràng buộc ghi của plan mục 3 thể hiện ngay trên chữ ký hàm:
 *   - `idempotencyKey` — mạng chập chờn, người dùng bấm lại: không tạo bản ghi đôi.
 *   - `expectedVersion` — ai đó đã xử lý trên web trước: ném [StaleVersionException].
 *   - `reason` — bắt buộc với RESOLVE và FIELD_REPORT.
 */
interface ActionRepository {
    suspend fun perform(
        eventId: String,
        action: PatrolAction,
        actorName: String,
        reason: String?,
        expectedVersion: Int,
        idempotencyKey: String,
    ): SecurityEvent
}

/** Bản ghi đã bị người khác thay đổi — tương đương HTTP 409. */
class StaleVersionException :
    Exception("Sự cố đã được người khác xử lý. Đang tải lại trạng thái mới nhất.")

/** Yêu cầu không hợp lệ — tương đương HTTP 400/403. */
class ActionRejectedException(message: String) : Exception(message)
