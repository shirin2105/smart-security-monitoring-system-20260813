package vn.t176.patrol.data.repository

import kotlinx.coroutines.delay
import vn.t176.patrol.data.fake.FakeEventStore
import vn.t176.patrol.domain.PatrolAction
import vn.t176.patrol.domain.model.SecurityEvent

class FakeActionRepository(
    private val store: FakeEventStore,
) : ActionRepository {

    override suspend fun perform(
        eventId: String,
        action: PatrolAction,
        actorName: String,
        reason: String?,
        expectedVersion: Int,
        idempotencyKey: String,
    ): SecurityEvent {
        delay(FAKE_LATENCY_MS)
        return store.perform(eventId, action, actorName, reason, expectedVersion, idempotencyKey)
    }

    private companion object {
        // Đủ lâu để nhìn thấy trạng thái "đang gửi" và kiểm chống double-submit.
        const val FAKE_LATENCY_MS = 500L
    }
}
