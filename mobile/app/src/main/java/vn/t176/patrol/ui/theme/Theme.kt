package vn.t176.patrol.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

/**
 * Bảng màu giữ đúng ngữ nghĩa mức độ nghiêm trọng giống bản web, để người dùng
 * chuyển giữa hai màn hình không phải học lại ý nghĩa màu.
 */
private val SurfaceDark = Color(0xFF0B0F19)
private val SurfaceElevated = Color(0xFF141B2D)
private val BrandBlue = Color(0xFF3B82F6)

internal val SeverityInfo = Color(0xFF38BDF8)
internal val SeverityWarning = Color(0xFFF59E0B)
internal val SeverityHigh = Color(0xFFFB923C)
internal val SeverityCritical = Color(0xFFEF4444)
internal val StateOk = Color(0xFF10B981)

private val DarkColors = darkColorScheme(
    primary = BrandBlue,
    onPrimary = Color.White,
    background = SurfaceDark,
    onBackground = Color(0xFFE5E7EB),
    surface = SurfaceDark,
    onSurface = Color(0xFFE5E7EB),
    surfaceVariant = SurfaceElevated,
    onSurfaceVariant = Color(0xFF9CA3AF),
    error = SeverityCritical,
    outline = Color(0xFF374151),
)

private val LightColors = lightColorScheme(
    primary = BrandBlue,
    error = SeverityCritical,
)

@Composable
fun PatrolTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    // App dùng cho ca trực đêm là chính, nên mặc định nghiêng về nền tối.
    val colors = if (darkTheme) DarkColors else LightColors
    val view = LocalView.current

    if (!view.isInEditMode) {
        SideEffect {
            // Màu nền thanh trạng thái đã đặt trong themes.xml. Ở đây chỉ chỉnh
            // màu icon cho tương phản, vì nó phụ thuộc theme sáng/tối lúc chạy.
            val window = (view.context as Activity).window
            WindowCompat.getInsetsController(window, view)
                .isAppearanceLightStatusBars = !darkTheme
        }
    }

    MaterialTheme(colorScheme = colors, content = content)
}
