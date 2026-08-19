package vn.t176.patrol.ui.theme

import androidx.compose.runtime.Immutable
import androidx.compose.ui.graphics.Color
import vn.t176.patrol.domain.model.EventState
import vn.t176.patrol.domain.model.Severity

/**
 * Bảng màu "Tactical Security & Operations Dark Mode".
 *
 * Vì sao tối sâu chứ không phải dark mode thông thường: app dùng chủ yếu trong
 * ca đêm và ngoài hiện trường. Nền càng tối thì mắt càng ít phải điều tiết khi
 * người trực liếc điện thoại rồi nhìn lại bóng đêm, và pin OLED cũng đỡ hao.
 *
 * Nguyên tắc bất di bất dịch: **màu không bao giờ là tín hiệu duy nhất**. Mỗi
 * mức độ nghiêm trọng đều đi kèm icon và nhãn chữ, vì khoảng 8% nam giới bị mù
 * màu đỏ–lục, và bảo vệ hay nhìn màn hình dưới nắng gắt nơi màu bệt lại.
 */

// ---------------------------------------------------------------------------
// Nền và bề mặt
// ---------------------------------------------------------------------------

/** Nền sâu nhất — dưới cùng của trục z. */
val TacticalBackground = Color(0xFF0A0F1D)

/** Card mặt phẳng nâng cấp 1 — hàng trong danh sách. */
val TacticalSurface = Color(0xFF121B2B)

/** Card nâng cấp 2 — khối nổi trên card, hộp thoại, ô nhập. */
val TacticalSurfaceElevated = Color(0xFF1E293B)

/** Viền phân tách. Đủ sáng để thấy trên nền tối, đủ mờ để không cắt vụn bố cục. */
val TacticalBorder = Color(0xFF334155)

/** Chữ chính. Không dùng trắng tinh — #FFFFFF trên nền rất tối gây chói và bóng mờ. */
val TacticalOnSurface = Color(0xFFE2E8F0)

/** Chữ phụ, nhãn, metadata. */
val TacticalOnSurfaceVariant = Color(0xFF94A3B8)

/** Chữ mờ nhất — chỉ dùng cho thông tin không quan trọng. */
val TacticalMuted = Color(0xFF64748B)

/** Màu nhấn chính của hệ thống — dùng cho hành động và điều hướng. */
val TacticalPrimary = Color(0xFF38BDF8)
val TacticalOnPrimary = Color(0xFF04141F)

/**
 * Màu nhấn phụ thứ ba — dùng cho "báo cáo hiện trường", loại hành động không
 * đổi trạng thái mà chỉ ghi nhận. Phải khác hẳn primary (xanh dương) và
 * secondary (xanh lục) để đọc nhật ký phân biệt được ngay ba nhóm hành động.
 *
 * Nếu không đặt, Material 3 rơi về tông hồng mặc định — lạc hoàn toàn khỏi
 * bảng màu tactical.
 */
val TacticalTertiary = Color(0xFFA78BFA)
val TacticalOnTertiary = Color(0xFF1E1233)

// ---------------------------------------------------------------------------
// Mức độ nghiêm trọng
// ---------------------------------------------------------------------------

val SeverityCritical = Color(0xFFEF4444)
val SeverityCriticalContainer = Color(0xFF450A0A)

val SeverityHigh = Color(0xFFF97316)
val SeverityHighContainer = Color(0xFF431407)

val SeverityWarning = Color(0xFFF59E0B)
val SeverityWarningContainer = Color(0xFF451A03)

val SeverityInfo = Color(0xFF38BDF8)
val SeverityInfoContainer = Color(0xFF082F49)

// ---------------------------------------------------------------------------
// Trạng thái sự cố
// ---------------------------------------------------------------------------

val StateOpen = Color(0xFF38BDF8)
val StateAcknowledged = Color(0xFF10B981)
val StatePendingReview = Color(0xFFF59E0B)
val StateConfirmed = Color(0xFFEF4444)
val StateResolved = Color(0xFF64748B)
val StateExpired = Color(0xFFF97316)

// ---------------------------------------------------------------------------
// Bộ ba màu cho mỗi mức độ / trạng thái
// ---------------------------------------------------------------------------

/**
 * Ba màu luôn đi cùng nhau: chữ/icon, nền chứa, và viền.
 *
 * Gom thành một bộ để chỗ dùng không thể lỡ tay ghép nền đỏ với chữ cam — lỗi
 * đó phá vỡ độ tương phản mà không ai nhận ra cho tới khi ra ngoài nắng.
 */
@Immutable
data class ToneColors(
    val content: Color,
    val container: Color,
    val border: Color,
)

/** Bộ màu của một mức độ nghiêm trọng. */
fun Severity.tone(): ToneColors = when (this) {
    Severity.CRITICAL -> ToneColors(
        content = SeverityCritical,
        container = SeverityCriticalContainer,
        // Viền sáng hơn hẳn: CRITICAL phải nhận ra được từ khoé mắt.
        border = SeverityCritical.copy(alpha = 0.85f),
    )

    Severity.HIGH -> ToneColors(
        content = SeverityHigh,
        container = SeverityHighContainer,
        border = SeverityHigh.copy(alpha = 0.55f),
    )

    Severity.WARNING -> ToneColors(
        content = SeverityWarning,
        container = SeverityWarningContainer,
        border = SeverityWarning.copy(alpha = 0.45f),
    )

    Severity.INFO -> ToneColors(
        content = SeverityInfo,
        container = SeverityInfoContainer,
        border = SeverityInfo.copy(alpha = 0.40f),
    )
}

/**
 * Bộ màu của một trạng thái sự cố.
 *
 * Bảy trạng thái chứ không phải bốn — `CONFIRMED`, `DISMISSED`, `EXPIRED` cũng
 * phải có màu riêng, nếu không chúng rơi vào nhánh mặc định và người dùng không
 * phân biệt được "đã xác nhận" với "đã bỏ qua".
 */
fun EventState.tone(): ToneColors {
    val base = when (this) {
        EventState.OPEN -> StateOpen
        EventState.ACKNOWLEDGED -> StateAcknowledged
        EventState.PENDING_REVIEW -> StatePendingReview
        EventState.CONFIRMED -> StateConfirmed
        EventState.RESOLVED, EventState.DISMISSED -> StateResolved
        EventState.EXPIRED -> StateExpired
    }
    return ToneColors(
        content = base,
        container = base.copy(alpha = 0.14f),
        border = base.copy(alpha = 0.45f),
    )
}
