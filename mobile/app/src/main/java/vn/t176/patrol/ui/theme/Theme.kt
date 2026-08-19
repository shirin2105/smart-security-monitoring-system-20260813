package vn.t176.patrol.ui.theme

import android.app.Activity
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.view.WindowCompat

/**
 * Theme "Tactical Dark" — hệ thống chỉ có một chế độ.
 *
 * Không có light mode, và đó là quyết định có chủ đích chứ không phải thiếu sót:
 * app này dùng trong ca đêm và ngoài hiện trường, một màn hình trắng loá giữa
 * đêm vừa làm chói mắt người trực vừa biến họ thành mục tiêu dễ thấy. Giữ tham
 * số `darkTheme` chỉ để điều khiển màu icon thanh trạng thái.
 */

private val TacticalColorScheme = darkColorScheme(
    primary = TacticalPrimary,
    onPrimary = TacticalOnPrimary,
    primaryContainer = SeverityInfoContainer,
    onPrimaryContainer = SeverityInfo,

    secondary = StateAcknowledged,
    onSecondary = Color(0xFF04231A),

    tertiary = TacticalTertiary,
    onTertiary = TacticalOnTertiary,
    tertiaryContainer = TacticalTertiary.copy(alpha = 0.16f),
    onTertiaryContainer = TacticalTertiary,

    background = TacticalBackground,
    onBackground = TacticalOnSurface,

    surface = TacticalBackground,
    onSurface = TacticalOnSurface,

    // surfaceVariant là card cấp 1 — hàng danh sách, khối nội dung.
    surfaceVariant = TacticalSurface,
    onSurfaceVariant = TacticalOnSurfaceVariant,

    // surfaceContainerHigh là card cấp 2 — hộp thoại, ô nhập, khối nổi trên card.
    surfaceContainer = TacticalSurface,
    surfaceContainerHigh = TacticalSurfaceElevated,
    surfaceContainerHighest = TacticalSurfaceElevated,

    error = SeverityCritical,
    onError = Color.White,
    errorContainer = SeverityCriticalContainer,
    onErrorContainer = SeverityCritical,

    outline = TacticalBorder,
    outlineVariant = TacticalBorder.copy(alpha = 0.5f),
)

/**
 * Bo góc đồng bộ: 12dp cho phần tử nhỏ, 16dp cho khối lớn.
 *
 * Hai giá trị thôi. Nhiều bán kính khác nhau trên cùng màn hình làm bố cục
 * trông lộn xộn mà người xem không chỉ ra được vì sao.
 */
private val TacticalShapes = Shapes(
    extraSmall = RoundedCornerShape(8.dp),
    small = RoundedCornerShape(10.dp),
    medium = RoundedCornerShape(12.dp),
    large = RoundedCornerShape(16.dp),
    extraLarge = RoundedCornerShape(20.dp),
)

/**
 * Kiểu chữ cho mã định danh: camera, sự cố, mốc thời gian.
 *
 * Monospace vì các mã này được đọc để **đối chiếu**, không phải để đọc hiểu.
 * Chiều rộng ký tự cố định giúp mắt so từng ký tự giữa màn hình và bộ đàm,
 * và `0` với `O` không còn lẫn vào nhau.
 */
val MonoLabel = TextStyle(
    fontFamily = FontFamily.Monospace,
    fontWeight = FontWeight.Medium,
    fontSize = 12.sp,
    letterSpacing = 0.5.sp,
)

val MonoLabelSmall = TextStyle(
    fontFamily = FontFamily.Monospace,
    fontWeight = FontWeight.Medium,
    fontSize = 11.sp,
    letterSpacing = 0.4.sp,
)

private val TacticalTypography = Typography().run {
    copy(
        headlineSmall = headlineSmall.copy(fontWeight = FontWeight.Bold),
        titleLarge = titleLarge.copy(fontWeight = FontWeight.Bold),
        titleMedium = titleMedium.copy(fontWeight = FontWeight.SemiBold),
        titleSmall = titleSmall.copy(fontWeight = FontWeight.SemiBold),
        // Nhãn đọc lướt trong lúc di chuyển nên cần đậm hơn mặc định.
        labelLarge = labelLarge.copy(fontWeight = FontWeight.SemiBold),
        labelMedium = labelMedium.copy(fontWeight = FontWeight.SemiBold),
    )
}

@Composable
fun PatrolTheme(
    darkTheme: Boolean = true,
    content: @Composable () -> Unit,
) {
    val view = LocalView.current

    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            // Luôn dùng icon sáng: nền thanh trạng thái luôn tối.
            WindowCompat.getInsetsController(window, view)
                .isAppearanceLightStatusBars = false
        }
    }

    MaterialTheme(
        colorScheme = TacticalColorScheme,
        typography = TacticalTypography,
        shapes = TacticalShapes,
        content = content,
    )
}
