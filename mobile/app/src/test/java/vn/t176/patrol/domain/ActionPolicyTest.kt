package vn.t176.patrol.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import vn.t176.patrol.domain.model.EventState
import vn.t176.patrol.domain.model.EventType
import vn.t176.patrol.domain.model.Role
import vn.t176.patrol.domain.model.SecurityEvent
import vn.t176.patrol.domain.model.Severity

/**
 * Phủ toàn bộ tổ hợp role × severity × state — Definition of Done mục 11 của
 * plan yêu cầu `ActionPolicy` có unit test đầy đủ.
 */
class ActionPolicyTest {

    private fun event(
        severity: Severity,
        state: EventState,
    ) = SecurityEvent(
        eventId = "evt_test",
        eventType = EventType.ZONE_INTRUSION,
        severity = severity,
        state = state,
        cameraName = "Cổng B2",
        siteId = "site_01",
        detectedAt = "2026-08-05T02:14:33Z",
        description = "test",
        version = 1,
    )

    /* ------------------------- Quản lý: không có nút nào ------------------------- */

    @Test
    fun `quan ly khong co hanh dong nao trong moi to hop`() {
        for (severity in Severity.entries) {
            for (state in EventState.entries) {
                val actions = ActionPolicy.allowedActions(Role.MANAGER, event(severity, state))
                assertTrue(
                    "Quản lý không được có nút nào ở $severity/$state nhưng nhận được $actions",
                    actions.isEmpty(),
                )
            }
        }
    }

    @Test
    fun `quan ly luon co cau giai thich vi sao khong thao tac duoc`() {
        val reason = ActionPolicy.emptyReason(Role.MANAGER, event(Severity.CRITICAL, EventState.PENDING_REVIEW))
        assertNotNull(reason)
        assertTrue(reason!!.contains("web"))
    }

    /* ------------------------- Bảo vệ: tiếp nhận việc --------------------------- */

    @Test
    fun `bao ve tiep nhan duoc su co dang mo o moi muc do`() {
        for (severity in Severity.entries) {
            val actions = ActionPolicy.allowedActions(Role.FIELD_GUARD, event(severity, EventState.OPEN))
            assertEquals(listOf(PatrolAction.ACKNOWLEDGE), actions)
        }
    }

    @Test
    fun `bao ve tiep nhan duoc su co dang cho quan ly duyet`() {
        val actions = ActionPolicy.allowedActions(
            Role.FIELD_GUARD,
            event(Severity.CRITICAL, EventState.PENDING_REVIEW),
        )
        assertEquals(listOf(PatrolAction.ACKNOWLEDGE), actions)
    }

    /* --------------------- Bảo vệ: sau khi đã tiếp nhận ------------------------- */

    @Test
    fun `su co nhe thi bao ve dong duoc`() {
        for (severity in listOf(Severity.INFO, Severity.WARNING)) {
            val actions = ActionPolicy.allowedActions(
                Role.FIELD_GUARD,
                event(severity, EventState.ACKNOWLEDGED),
            )
            assertEquals(listOf(PatrolAction.RESOLVE), actions)
        }
    }

    @Test
    fun `su co nghiem trong thi bao ve chi bao cao, khong dong duoc`() {
        for (severity in listOf(Severity.HIGH, Severity.CRITICAL)) {
            val actions = ActionPolicy.allowedActions(
                Role.FIELD_GUARD,
                event(severity, EventState.ACKNOWLEDGED),
            )
            assertEquals(listOf(PatrolAction.FIELD_REPORT), actions)
            assertFalse(actions.contains(PatrolAction.RESOLVE))
        }
    }

    /* ------------------------------ Trạng thái cuối ----------------------------- */

    @Test
    fun `su co da dong thi khong con nut nao`() {
        val closed = listOf(EventState.RESOLVED, EventState.DISMISSED, EventState.EXPIRED)
        for (state in closed) {
            for (severity in Severity.entries) {
                assertTrue(
                    ActionPolicy.allowedActions(Role.FIELD_GUARD, event(severity, state)).isEmpty(),
                )
            }
        }
    }

    @Test
    fun `su co da xac nhan thi cho quan ly dong tren web`() {
        val actions = ActionPolicy.allowedActions(
            Role.FIELD_GUARD,
            event(Severity.CRITICAL, EventState.CONFIRMED),
        )
        assertTrue(actions.isEmpty())
        assertNotNull(ActionPolicy.emptyReason(Role.FIELD_GUARD, event(Severity.CRITICAL, EventState.CONFIRMED)))
    }

    /* ------------------------------- Bất biến ----------------------------------- */

    @Test
    fun `khong ton tai hanh dong confirm dismiss hay approve trong app`() {
        val names = PatrolAction.entries.map { it.name }
        for (forbidden in listOf("CONFIRM", "DISMISS", "APPROVE", "DECLINE", "ESCALATION")) {
            assertFalse(
                "App không được có hành động $forbidden — xem mục 4.5 của plan",
                names.any { it.contains(forbidden) },
            )
        }
    }

    @Test
    fun `bao cao ket qua va dong su co deu bat buoc nhap ly do`() {
        assertTrue(PatrolAction.FIELD_REPORT.requiresReason)
        assertTrue(PatrolAction.RESOLVE.requiresReason)
        assertFalse(PatrolAction.ACKNOWLEDGE.requiresReason)
    }

    @Test
    fun `nguong push la HIGH va CRITICAL, giong nhau cho hai role`() {
        assertFalse(Severity.INFO.isPushWorthy)
        assertFalse(Severity.WARNING.isPushWorthy)
        assertTrue(Severity.HIGH.isPushWorthy)
        assertTrue(Severity.CRITICAL.isPushWorthy)
    }
}
