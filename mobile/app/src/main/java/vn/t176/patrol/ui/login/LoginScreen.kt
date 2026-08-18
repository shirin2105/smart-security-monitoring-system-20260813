package vn.t176.patrol.ui.login

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.MonitorHeart
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role as SemanticsRole
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import vn.t176.patrol.domain.model.Role
import vn.t176.patrol.domain.model.UserSession
import vn.t176.patrol.ui.common.MinTouchTarget
import vn.t176.patrol.ui.theme.MonoLabelSmall
import vn.t176.patrol.ui.theme.StateAcknowledged
import vn.t176.patrol.ui.theme.TacticalSurface
import vn.t176.patrol.ui.theme.TacticalSurfaceElevated

/**
 * Đăng nhập giả cho Phase 1 — chọn vai trò để kiểm chứng điều hướng và
 * `ActionPolicy`. Phase 2 thay bằng `POST /api/v1/auth/login` thật, giữ nguyên
 * callback nên màn hình không phải viết lại.
 *
 * Vì sao thẻ vai trò lại ghi rõ quyền hạn: hai vai trò trong app này có quyền
 * **rất khác nhau** — Quản lý không thao tác được gì cả. Nói trước ở đây tránh
 * việc người dùng chọn nhầm rồi vào trong mới thấy không có nút nào và tưởng
 * app hỏng.
 */
@Composable
fun LoginScreen(onSignedIn: (UserSession) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    listOf(
                        MaterialTheme.colorScheme.background,
                        TacticalSurface,
                        MaterialTheme.colorScheme.background,
                    ),
                ),
            )
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp, vertical = 32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        TacticalShield()

        Text(
            text = "T176 PATROL",
            style = MaterialTheme.typography.headlineSmall,
            modifier = Modifier.padding(top = 20.dp),
        )
        Text(
            text = "Hệ thống tuần tra & phản ứng an ninh",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 6.dp),
        )

        SystemStatusLight(modifier = Modifier.padding(top = 16.dp))

        Text(
            text = "CHỌN VAI TRÒ TRỰC CA",
            style = MonoLabelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 36.dp, bottom = 12.dp),
        )

        RoleCard(
            icon = Icons.Default.Security,
            title = Role.FIELD_GUARD.label,
            summary = "Nhận cảnh báo tại hiện trường, tiếp nhận và báo cáo kết quả kiểm tra.",
            capabilities = listOf("Tiếp nhận sự cố", "Đóng sự cố nhẹ", "Báo cáo hiện trường"),
            accent = MaterialTheme.colorScheme.primary,
            onClick = { onSignedIn(guardSession()) },
        )

        Spacer(Modifier.height(12.dp))

        RoleCard(
            icon = Icons.Default.Shield,
            title = Role.MANAGER.label,
            summary = "Theo dõi toàn cảnh và tra cứu nhật ký. Thao tác xử lý thực hiện trên web.",
            capabilities = listOf("Xem mọi cảnh báo", "Tra nhật ký thao tác", "Chỉ đọc trong app"),
            accent = StateAcknowledged,
            onClick = { onSignedIn(managerSession()) },
        )

        Text(
            text = "Dữ liệu đang lấy từ fixture trong máy, chưa nối backend.",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 24.dp),
        )
    }
}

/** Khiên phù hiệu — vòng sáng bao quanh để tạo cảm giác thiết bị nghiệp vụ. */
@Composable
private fun TacticalShield() {
    val primary = MaterialTheme.colorScheme.primary
    Box(contentAlignment = Alignment.Center) {
        Box(
            modifier = Modifier
                .size(112.dp)
                .clip(CircleShape)
                .background(
                    Brush.radialGradient(
                        listOf(primary.copy(alpha = 0.22f), Color.Transparent),
                    ),
                ),
        )
        Box(
            modifier = Modifier
                .size(80.dp)
                .clip(CircleShape)
                .background(TacticalSurfaceElevated)
                .border(1.5.dp, primary.copy(alpha = 0.55f), CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = Icons.Default.Shield,
                contentDescription = null,
                tint = primary,
                modifier = Modifier.size(40.dp),
            )
        }
    }
}

/** Đèn tín hiệu hệ thống — cho biết phía sau vẫn đang giám sát. */
@Composable
private fun SystemStatusLight(modifier: Modifier = Modifier) {
    val transition = rememberInfiniteTransition(label = "system-status")
    val pulse by transition.animateFloat(
        initialValue = 1f,
        targetValue = 0.3f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1400),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "system-status-alpha",
    )

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        modifier = modifier
            .clip(RoundedCornerShape(20.dp))
            .background(StateAcknowledged.copy(alpha = 0.10f))
            .border(1.dp, StateAcknowledged.copy(alpha = 0.35f), RoundedCornerShape(20.dp))
            .padding(horizontal = 14.dp, vertical = 8.dp),
    ) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .alpha(pulse)
                .clip(CircleShape)
                .background(StateAcknowledged),
        )
        Icon(
            imageVector = Icons.Default.MonitorHeart,
            contentDescription = null,
            tint = StateAcknowledged,
            modifier = Modifier.size(15.dp),
        )
        Text(
            text = "Hệ thống AI giám sát đang hoạt động",
            style = MaterialTheme.typography.labelSmall,
            color = StateAcknowledged,
        )
    }
}

@Composable
private fun RoleCard(
    icon: ImageVector,
    title: String,
    summary: String,
    capabilities: List<String>,
    accent: Color,
    onClick: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = MinTouchTarget)
            .clip(MaterialTheme.shapes.large)
            .background(TacticalSurface)
            .border(1.dp, MaterialTheme.colorScheme.outline, MaterialTheme.shapes.large)
            // role = Button để trình đọc màn hình đọc là nút chứ không phải khối chữ.
            .clickable(role = SemanticsRole.Button, onClick = onClick)
            .padding(16.dp),
        verticalAlignment = Alignment.Top,
    ) {
        Box(
            modifier = Modifier
                .size(44.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(accent.copy(alpha = 0.14f))
                .border(1.dp, accent.copy(alpha = 0.35f), RoundedCornerShape(12.dp)),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = accent,
                modifier = Modifier.size(24.dp),
            )
        }

        Column(modifier = Modifier.weight(1f).padding(start = 14.dp)) {
            Text(text = title, style = MaterialTheme.typography.titleSmall)
            Text(
                text = summary,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 4.dp),
            )
            Column(modifier = Modifier.padding(top = 10.dp)) {
                capabilities.forEach { item ->
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(vertical = 2.dp),
                    ) {
                        Box(
                            modifier = Modifier
                                .size(4.dp)
                                .clip(CircleShape)
                                .background(accent),
                        )
                        Text(
                            text = item,
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(start = 8.dp),
                        )
                    }
                }
            }
        }

        Icon(
            imageVector = Icons.AutoMirrored.Filled.ArrowForward,
            contentDescription = null,
            tint = accent,
            modifier = Modifier.padding(start = 8.dp, top = 12.dp).size(20.dp),
        )
    }
}

private fun managerSession() = UserSession(
    userId = "usr_manager",
    displayName = "Quản Lý Trần Văn B",
    role = Role.MANAGER,
    siteIds = listOf("site_01"),
)

private fun guardSession() = UserSession(
    userId = "usr_guard",
    displayName = "Bảo Vệ Nguyễn Văn A",
    role = Role.FIELD_GUARD,
    siteIds = listOf("site_01"),
)
