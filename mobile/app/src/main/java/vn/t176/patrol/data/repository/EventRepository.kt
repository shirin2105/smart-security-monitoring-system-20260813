package vn.t176.patrol.data.repository

import kotlinx.coroutines.delay
import vn.t176.patrol.data.fake.FakeEventStore
import vn.t176.patrol.domain.model.SecurityEvent

interface EventRepository {
    suspend fun list(): List<SecurityEvent>
    suspend fun byId(eventId: String): SecurityEvent?
}

/**
 * Đọc từ [FakeEventStore] dùng chung — nhờ vậy hành động vừa thực hiện ở màn
 * chi tiết hiện ngay khi quay lại danh sách, giống hành vi backend thật.
 *
 * Độ trễ giả để màn hình phải xử lý trạng thái loading thật sự.
 */
class FakeEventRepository(
    private val store: FakeEventStore,
) : EventRepository {

    override suspend fun list(): List<SecurityEvent> {
        delay(FAKE_LATENCY_MS)
        return store.snapshotEvents()
    }

    override suspend fun byId(eventId: String): SecurityEvent? {
        delay(FAKE_LATENCY_MS)
        return store.findEvent(eventId)
    }

    private companion object {
        const val FAKE_LATENCY_MS = 350L
    }
}
