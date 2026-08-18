package vn.t176.patrol.ui.common

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Block
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Dangerous
import androidx.compose.material.icons.automirrored.filled.DirectionsRun
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.HourglassEmpty
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.PersonalInjury
import androidx.compose.material.icons.filled.Report
import androidx.compose.material.icons.filled.Task
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material.icons.filled.VideocamOff
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.filled.Work
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import vn.t176.patrol.domain.model.EventState
import vn.t176.patrol.domain.model.EventType
import vn.t176.patrol.domain.model.Severity
import vn.t176.patrol.ui.theme.MonoLabelSmall
import vn.t176.patrol.ui.theme.ToneColors
import vn.t176.patrol.ui.theme.tone

/**
 * Huy hiệu trạng thái.
 *
 * Mọi badge ở đây theo công thức **icon + chữ + màu**. Không bao giờ chỉ dùng
 * màu: người mù màu đỏ–lục chiếm khoảng 8% nam giới, và dưới nắng gắt thì cam
 * với đỏ bệt vào nhau ngay cả với mắt bình thường. Chữ và hình dáng icon mới là
 * thứ chịu được cả hai hoàn cảnh đó.
 */

@Composable
private fun Pill(
    text: String,
    icon: ImageVector?,
    tone: ToneColors,
    modifier: Modifier = Modifier,
    monospace: Boolean = false,
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(tone.container)
            .border(1.dp, tone.border, RoundedCornerShape(8.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp),
    ) {
        if (icon != null) {
            Icon(
                imageVector = icon,
                // Nhãn chữ ngay bên cạnh đã mô tả đủ; đọc thêm tên icon chỉ làm
                // trình đọc màn hình lặp thừa.
                contentDescription = null,
                tint = tone.content,
                modifier = Modifier.size(13.dp),
            )
        }
        if (monospace) {
            Text(text = text, style = MonoLabelSmall, color = tone.content)
        } else {
            Text(
                text = text,
                color = tone.content,
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
            )
        }
    }
}

@Composable
fun SeverityBadge(severity: Severity, modifier: Modifier = Modifier) {
    Pill(
        text = severity.label.uppercase(),
        icon = severity.icon(),
        tone = severity.tone(),
        modifier = modifier,
    )
}

@Composable
fun StateBadge(state: EventState, modifier: Modifier = Modifier) {
    Pill(text = state.label, icon = state.icon(), tone = state.tone(), modifier = modifier)
}

@Composable
fun NeutralBadge(text: String, icon: ImageVector? = null, modifier: Modifier = Modifier) {
    val scheme = MaterialTheme.colorScheme
    Pill(
        text = text,
        icon = icon,
        tone = ToneColors(
            content = scheme.onSurfaceVariant,
            container = scheme.onSurfaceVariant.copy(alpha = 0.10f),
            border = scheme.outline,
        ),
        modifier = modifier,
    )
}

/** Mã camera — luôn monospace để đối chiếu từng ký tự với bộ đàm hay sơ đồ. */
@Composable
fun CameraTagBadge(cameraName: String, online: Boolean = true, modifier: Modifier = Modifier) {
    val scheme = MaterialTheme.colorScheme
    val color = if (online) scheme.primary else scheme.onSurfaceVariant
    Pill(
        text = cameraName,
        icon = if (online) Icons.Default.Videocam else Icons.Default.VideocamOff,
        tone = ToneColors(
            content = color,
            container = color.copy(alpha = 0.12f),
            border = color.copy(alpha = 0.35f),
        ),
        modifier = modifier,
        monospace = true,
    )
}

/**
 * Chấm nhấp nháy cho sự cố chưa ai nhận.
 *
 * Chuyển động chỉ dành cho đúng một thứ trong app này. Nếu chỗ nào cũng động
 * thì mắt hết chỗ bấu víu và chẳng còn gì nổi bật nữa.
 */
@Composable
fun LivePulseBadge(text: String = "CHỜ TIẾP NHẬN", modifier: Modifier = Modifier) {
    val transition = rememberInfiniteTransition(label = "live-pulse")
    val pulse by transition.animateFloat(
        initialValue = 1f,
        targetValue = 0.25f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 900),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "live-pulse-alpha",
    )

    val tone = EventState.OPEN.tone()

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(tone.container)
            .border(1.dp, tone.border, RoundedCornerShape(8.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp)
            // Gộp thành một nhãn duy nhất cho trình đọc màn hình: chấm nhấp nháy
            // là hiệu ứng thị giác, không phải thông tin riêng.
            .clearAndSetSemantics { contentDescription = "Đang chờ tiếp nhận" },
    ) {
        Box(
            modifier = Modifier
                .size(7.dp)
                .alpha(pulse)
                .clip(CircleShape)
                .background(tone.content),
        )
        Text(
            text = text,
            color = tone.content,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}

// ---------------------------------------------------------------------------
// Icon theo ngữ nghĩa
// ---------------------------------------------------------------------------

fun Severity.icon(): ImageVector = when (this) {
    Severity.CRITICAL -> Icons.Default.Dangerous
    Severity.HIGH -> Icons.Default.Report
    Severity.WARNING -> Icons.Default.Warning
    Severity.INFO -> Icons.Default.Info
}

fun EventState.icon(): ImageVector = when (this) {
    EventState.OPEN -> Icons.Default.HourglassEmpty
    EventState.ACKNOWLEDGED -> Icons.AutoMirrored.Filled.DirectionsRun
    EventState.PENDING_REVIEW -> Icons.Default.Task
    EventState.CONFIRMED -> Icons.Default.Report
    EventState.RESOLVED -> Icons.Default.CheckCircle
    EventState.DISMISSED -> Icons.Default.Block
    EventState.EXPIRED -> Icons.Default.HourglassEmpty
}

fun EventType.icon(): ImageVector = when (this) {
    EventType.ZONE_INTRUSION -> Icons.AutoMirrored.Filled.DirectionsRun
    EventType.CROWD_THRESHOLD -> Icons.Default.Groups
    EventType.ABANDONED_OBJECT -> Icons.Default.Work
    EventType.SUSPECTED_FALL -> Icons.Default.PersonalInjury
    EventType.COVERAGE_DEGRADED -> Icons.Default.VideocamOff
}

/** Màu chữ đại diện cho mức độ — dùng khi chỉ cần một màu, không cần cả bộ. */
fun Severity.color(): Color = tone().content
