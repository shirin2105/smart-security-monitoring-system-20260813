package vn.t176.patrol.data.fake

import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import vn.t176.patrol.data.repository.ActionRejectedException
import vn.t176.patrol.data.repository.StaleVersionException
import vn.t176.patrol.domain.ActionPolicy
import vn.t176.patrol.domain.PatrolAction
import vn.t176.patrol.domain.model.AuditEntry
import vn.t176.patrol.domain.model.EventState
import vn.t176.patrol.domain.model.Role
import vn.t176.patrol.domain.model.SecurityEvent
import java.time.Instant

/**
 * Kho dữ liệu in-memory dùng chung cho mọi repository giả.
 *
 * Điểm khác biệt so với fixture tĩnh: nó **mô phỏng đúng luật ghi của server**
 * — kiểm tra version, bắt buộc lý do, nhớ Idempotency-Key và ghi audit trong
 * cùng một "transaction". Nhờ vậy các nhánh lỗi 409/400 của màn hình kiểm chứng
 * được ngay ở flavor `mock`, không phải chờ backend của Hưng.
 */
class FakeEventStore(
    initialEvents: List<SecurityEvent>,
    initialAudit: List<AuditEntry>,
) {

    private val mutex = Mutex()
    private val events = initialEvents.toMutableList()
    private val audit = initialAudit.toMutableList()

    /** Kết quả đã trả cho từng Idempotency-Key — bấm lại trả đúng bản cũ. */
    private val processedKeys = mutableMapOf<String, SecurityEvent>()

    private var nextAuditId = 100

    suspend fun snapshotEvents(): List<SecurityEvent> = mutex.withLock {
        events.sortedByDescending { it.detectedAt }
    }

    suspend fun findEvent(eventId: String): SecurityEvent? = mutex.withLock {
        events.firstOrNull { it.eventId == eventId }
    }

    suspend fun snapshotAudit(): List<AuditEntry> = mutex.withLock { audit.toList() }

    suspend fun perform(
        eventId: String,
        action: PatrolAction,
        actorName: String,
        reason: String?,
        expectedVersion: Int,
        idempotencyKey: String,
    ): SecurityEvent = mutex.withLock {
        // Retry cùng một key: trả lại kết quả cũ, không ghi thêm lần nữa.
        processedKeys[idempotencyKey]?.let { return it }

        val index = events.indexOfFirst { it.eventId == eventId }
        if (index < 0) throw ActionRejectedException("Không tìm thấy sự cố $eventId.")
        val current = events[index]

        if (current.version != expectedVersion) throw StaleVersionException()

        // Server không tin UI: kiểm tra lại matrix của plan mục 3.
        if (action !in ActionPolicy.allowedActions(Role.FIELD_GUARD, current)) {
            throw ActionRejectedException(
                "Hành động ${action.label} không hợp lệ với sự cố ở trạng thái ${current.state.label}.",
            )
        }

        if (action.requiresReason && reason.isNullOrBlank()) {
            throw ActionRejectedException("Thao tác này bắt buộc nhập lý do.")
        }

        val updated = current.copy(
            state = when (action) {
                PatrolAction.ACKNOWLEDGE -> EventState.ACKNOWLEDGED
                PatrolAction.RESOLVE -> EventState.RESOLVED
                // Báo cáo kết quả KHÔNG đổi state — Quản lý đóng trên web (§3).
                PatrolAction.FIELD_REPORT -> current.state
            },
            version = current.version + 1,
        )
        events[index] = updated

        // Audit ghi cùng lúc với state — mô phỏng cùng-transaction của backend.
        audit.add(
            0,
            AuditEntry(
                id = "aud_${nextAuditId++}",
                actorName = actorName,
                actorRole = Role.FIELD_GUARD,
                action = when (action) {
                    PatrolAction.ACKNOWLEDGE -> "Tiếp nhận xử lý sự cố"
                    PatrolAction.RESOLVE -> "Đóng sự cố sau khi xử lý tại hiện trường"
                    PatrolAction.FIELD_REPORT -> "Báo cáo kết quả kiểm tra hiện trường"
                },
                eventId = eventId,
                reason = reason?.takeIf { it.isNotBlank() },
                at = Instant.now().toString(),
            ),
        )

        processedKeys[idempotencyKey] = updated
        updated
    }
}
