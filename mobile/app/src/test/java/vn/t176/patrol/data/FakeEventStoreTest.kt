package vn.t176.patrol.data

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import vn.t176.patrol.data.fake.FakeEventStore
import vn.t176.patrol.data.repository.ActionRejectedException
import vn.t176.patrol.data.repository.StaleVersionException
import vn.t176.patrol.domain.PatrolAction
import vn.t176.patrol.domain.model.EventState
import vn.t176.patrol.domain.model.EventType
import vn.t176.patrol.domain.model.SecurityEvent
import vn.t176.patrol.domain.model.Severity

/**
 * Kiểm chứng ba ràng buộc ghi ở mục 3 của plan, và luật chuyển trạng thái ở
 * mục 3 — những thứ mà thao tác tay trên máy rất khó dựng lại.
 */
class FakeEventStoreTest {

    private val guard = "Bảo Vệ Nguyễn Văn A"

    private fun event(
        id: String = "evt_1",
        severity: Severity = Severity.WARNING,
        state: EventState = EventState.OPEN,
        version: Int = 1,
    ) = SecurityEvent(
        eventId = id,
        eventType = EventType.ZONE_INTRUSION,
        severity = severity,
        state = state,
        cameraName = "Cổng B2",
        siteId = "site_01",
        detectedAt = "2026-08-05T02:14:33Z",
        description = "test",
        version = version,
    )

    private fun store(vararg events: SecurityEvent) =
        FakeEventStore(initialEvents = events.toList(), initialAudit = emptyList())

    /* ------------------------------ chuyển trạng thái --------------------------- */

    @Test
    fun `tiep nhan chuyen su co sang dang xu ly va tang phien ban`(): Unit = runBlocking {
        val store = store(event())

        val updated = store.perform(
            eventId = "evt_1",
            action = PatrolAction.ACKNOWLEDGE,
            actorName = guard,
            reason = null,
            expectedVersion = 1,
            idempotencyKey = "key-1",
        )

        assertEquals(EventState.ACKNOWLEDGED, updated.state)
        assertEquals(2, updated.version)
    }

    @Test
    fun `dong su co nhe chuyen sang da xu ly xong`(): Unit = runBlocking {
        val store = store(event(state = EventState.ACKNOWLEDGED))

        val updated = store.perform(
            "evt_1", PatrolAction.RESOLVE, guard,
            reason = "Đã kiểm tra, khu vực an toàn.",
            expectedVersion = 1, idempotencyKey = "key-1",
        )

        assertEquals(EventState.RESOLVED, updated.state)
    }

    @Test
    fun `bao cao ket qua KHONG doi trang thai - quan ly dong tren web`(): Unit = runBlocking {
        val store = store(event(severity = Severity.CRITICAL, state = EventState.ACKNOWLEDGED))

        val updated = store.perform(
            "evt_1", PatrolAction.FIELD_REPORT, guard,
            reason = "Đã tới nơi, cửa đã khóa lại, không có dấu hiệu cạy phá.",
            expectedVersion = 1, idempotencyKey = "key-1",
        )

        // Đây là điểm dễ làm sai nhất: báo cáo chỉ ghi nhận, không đóng sự cố.
        assertEquals(EventState.ACKNOWLEDGED, updated.state)
        assertEquals(2, updated.version)
    }

    /* -------------------------------- idempotency ------------------------------- */

    @Test
    fun `bam lai cung mot key khong tao ban ghi doi`(): Unit = runBlocking {
        val store = store(event())

        val first = store.perform(
            "evt_1", PatrolAction.ACKNOWLEDGE, guard, null,
            expectedVersion = 1, idempotencyKey = "same-key",
        )
        val second = store.perform(
            "evt_1", PatrolAction.ACKNOWLEDGE, guard, null,
            expectedVersion = 1, idempotencyKey = "same-key",
        )

        assertEquals(first.version, second.version)
        assertEquals(1, store.snapshotAudit().size)
    }

    @Test
    fun `key khac nhau thi la hai thao tac khac nhau`(): Unit = runBlocking {
        val store = store(event())

        store.perform("evt_1", PatrolAction.ACKNOWLEDGE, guard, null, 1, "key-1")
        store.perform(
            "evt_1", PatrolAction.RESOLVE, guard,
            "Đã xử lý xong tại hiện trường.", 2, "key-2",
        )

        assertEquals(2, store.snapshotAudit().size)
    }

    /* ------------------------------ xung đột phiên bản -------------------------- */

    @Test
    fun `gui phien ban cu thi bi tu choi nhu HTTP 409`(): Unit = runBlocking {
        val store = store(event())
        store.perform("evt_1", PatrolAction.ACKNOWLEDGE, guard, null, 1, "key-1")

        // Người khác đã xử lý trên web: version giờ là 2, app vẫn giữ 1.
        assertThrows(StaleVersionException::class.java) {
            runBlocking {
                store.perform("evt_1", PatrolAction.RESOLVE, guard, "lý do đủ dài", 1, "key-2")
            }
        }
    }

    /* --------------------------------- lý do ------------------------------------ */

    @Test
    fun `dong su co ma thieu ly do thi bi tu choi`(): Unit = runBlocking {
        val store = store(event(state = EventState.ACKNOWLEDGED))

        assertThrows(ActionRejectedException::class.java) {
            runBlocking {
                store.perform("evt_1", PatrolAction.RESOLVE, guard, "   ", 1, "key-1")
            }
        }
    }

    @Test
    fun `bao cao ket qua ma thieu ly do thi bi tu choi`(): Unit = runBlocking {
        val store = store(event(severity = Severity.HIGH, state = EventState.ACKNOWLEDGED))

        assertThrows(ActionRejectedException::class.java) {
            runBlocking {
                store.perform("evt_1", PatrolAction.FIELD_REPORT, guard, null, 1, "key-1")
            }
        }
    }

    /* ------------------------- server kiểm tra lại matrix ----------------------- */

    @Test
    fun `hanh dong khong hop le voi trang thai hien tai thi bi tu choi`(): Unit = runBlocking {
        // Sự cố mới mở thì chưa thể "đã xử lý xong".
        val store = store(event(state = EventState.OPEN))

        assertThrows(ActionRejectedException::class.java) {
            runBlocking {
                store.perform("evt_1", PatrolAction.RESOLVE, guard, "lý do đủ dài", 1, "key-1")
            }
        }
    }

    @Test
    fun `khong the dong su co nghiem trong tu hien truong`(): Unit = runBlocking {
        val store = store(event(severity = Severity.CRITICAL, state = EventState.ACKNOWLEDGED))

        // Chỉ FIELD_REPORT hợp lệ; RESOLVE là đặc quyền của Quản lý trên web.
        assertThrows(ActionRejectedException::class.java) {
            runBlocking {
                store.perform("evt_1", PatrolAction.RESOLVE, guard, "lý do đủ dài", 1, "key-1")
            }
        }
    }

    /* ---------------------------------- audit ----------------------------------- */

    @Test
    fun `moi thao tac deu ghi audit kem ly do`(): Unit = runBlocking {
        val store = store(event(severity = Severity.HIGH, state = EventState.ACKNOWLEDGED))
        val lyDo = "Đã tới hiện trường, xác minh là nhân viên kỹ thuật có phiếu."

        store.perform("evt_1", PatrolAction.FIELD_REPORT, guard, lyDo, 1, "key-1")

        val entry = store.snapshotAudit().first()
        assertEquals(guard, entry.actorName)
        assertEquals("evt_1", entry.eventId)
        assertEquals(lyDo, entry.reason)
        assertTrue(entry.action.contains("Báo cáo"))
    }

    @Test
    fun `tiep nhan khong co ly do thi audit khong ghi ly do rong`(): Unit = runBlocking {
        val store = store(event())
        store.perform("evt_1", PatrolAction.ACKNOWLEDGE, guard, null, 1, "key-1")

        assertNull(store.snapshotAudit().first().reason)
    }

    @Test
    fun `su co khong ton tai thi bao loi ro rang`(): Unit = runBlocking {
        val store = store(event())

        assertThrows(ActionRejectedException::class.java) {
            runBlocking {
                store.perform("evt_khong_co", PatrolAction.ACKNOWLEDGE, guard, null, 1, "key-1")
            }
        }
        assertNotNull(store.findEvent("evt_1"))
    }
}
