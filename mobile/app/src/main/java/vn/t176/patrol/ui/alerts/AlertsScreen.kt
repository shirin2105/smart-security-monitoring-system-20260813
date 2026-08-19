package vn.t176.patrol.ui.alerts

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.NotificationsOff
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.VerifiedUser
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role as SemanticsRole
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import vn.t176.patrol.domain.model.EventState
import vn.t176.patrol.domain.model.Role
import vn.t176.patrol.domain.model.SecurityEvent
import vn.t176.patrol.ui.common.AlertListSkeleton
import vn.t176.patrol.ui.common.CameraTagBadge
import vn.t176.patrol.ui.common.EmptyState
import vn.t176.patrol.ui.common.ErrorState
import vn.t176.patrol.ui.common.LivePulseBadge
import vn.t176.patrol.ui.common.MinTouchTarget
import vn.t176.patrol.ui.common.SeverityBadge
import vn.t176.patrol.ui.common.StateBadge
import vn.t176.patrol.ui.common.TimeFormat
import vn.t176.patrol.ui.common.UiState
import vn.t176.patrol.ui.common.icon
import vn.t176.patrol.ui.theme.MonoLabelSmall
import vn.t176.patrol.ui.theme.StateAcknowledged
import vn.t176.patrol.ui.theme.TacticalSurface
import vn.t176.patrol.ui.theme.tone

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AlertsScreen(
    viewModel: AlertsViewModel,
    role: Role,
    onOpenEvent: (String) -> Unit,
    onOpenAudit: () -> Unit,
    onLogout: () -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val filter by viewModel.filter.collectAsStateWithLifecycle()
    val counts by viewModel.counts.collectAsStateWithLifecycle()
    val syncStatus by viewModel.syncStatus.collectAsStateWithLifecycle()

    // Tải lại mỗi lần màn hình trở lại foreground: sau khi Bảo vệ tiếp nhận hay
    // đóng một sự cố ở màn chi tiết, danh sách phải phản ánh ngay trạng thái mới.
    LifecycleResumeEffect(Unit) {
        viewModel.refresh()
        onPauseOrDispose { }
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            TopAppBar(
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = TacticalSurface,
                ),
                title = {
                    Column {
                        Text("Cảnh báo", style = MaterialTheme.typography.titleMedium)
                        SyncIndicator(status = syncStatus, role = role)
                    }
                },
                actions = {
                    IconButton(onClick = viewModel::refresh) {
                        Icon(Icons.Default.Refresh, contentDescription = "Tải lại")
                    }
                    // Nhật ký là màn dành riêng cho Quản lý (plan mục 2).
                    if (role == Role.MANAGER) {
                        IconButton(onClick = onOpenAudit) {
                            Icon(Icons.Default.History, contentDescription = "Nhật ký thao tác")
                        }
                    }
                    IconButton(onClick = onLogout) {
                        Icon(
                            Icons.AutoMirrored.Filled.Logout,
                            contentDescription = "Đăng xuất",
                        )
                    }
                },
            )
        },
    ) { padding ->
        Column(modifier = Modifier.padding(top = padding.calculateTopPadding())) {
            FilterChipRow(
                selected = filter,
                counts = counts,
                onSelect = viewModel::setFilter,
            )

            when (val current = state) {
                is UiState.Loading -> AlertListSkeleton()

                is UiState.Error -> ErrorState(
                    message = current.message,
                    onRetry = viewModel::refresh,
                )

                is UiState.Content -> if (current.data.isEmpty()) {
                    EmptyState(
                        title = when (filter) {
                            AlertFilter.URGENT -> "Hiện trường an toàn"
                            AlertFilter.UNHANDLED -> "Mọi sự cố đã có người nhận"
                            AlertFilter.ALL -> "Chưa có cảnh báo nào"
                        },
                        hint = when (filter) {
                            AlertFilter.URGENT ->
                                "Không có cảnh báo khẩn cấp nào đang mở. " +
                                    "Chạm \"Tất cả\" để xem các mức nhẹ hơn."

                            AlertFilter.UNHANDLED ->
                                "Không còn sự cố nào chờ tiếp nhận."

                            AlertFilter.ALL ->
                                "Hệ thống vẫn đang giám sát. Cảnh báo sẽ hiện ngay khi phát sinh."
                        },
                        icon = if (filter == AlertFilter.ALL) {
                            Icons.Default.NotificationsOff
                        } else {
                            Icons.Default.VerifiedUser
                        },
                    )
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(
                            start = 16.dp,
                            end = 16.dp,
                            top = 4.dp,
                            bottom = 24.dp,
                        ),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        items(current.data, key = { it.eventId }) { event ->
                            AlertCard(event = event, onClick = { onOpenEvent(event.eventId) })
                        }
                    }
                }
            }
        }
    }
}

/**
 * Trạng thái đồng bộ dưới tiêu đề.
 *
 * Suy ra từ lần tải gần nhất chứ không phải đèn trang trí — nếu app mất kết nối
 * thì người trực phải biết mình đang nhìn dữ liệu cũ, chứ không phải yên tâm là
 * hiện trường không có gì.
 */
@Composable
private fun SyncIndicator(status: SyncStatus, role: Role) {
    val (color, label) = when (status) {
        SyncStatus.SYNCING -> MaterialTheme.colorScheme.onSurfaceVariant to "Đang đồng bộ…"
        SyncStatus.ONLINE -> StateAcknowledged to "Trực tuyến"
        SyncStatus.OFFLINE -> MaterialTheme.colorScheme.error to "Mất kết nối"
    }

    val transition = rememberInfiniteTransition(label = "sync")
    val pulse by transition.animateFloat(
        initialValue = 1f,
        targetValue = 0.35f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1200),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "sync-alpha",
    )

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        modifier = Modifier.semantics {
            contentDescription = "$label. Vai trò ${role.label}"
        },
    ) {
        Box(
            modifier = Modifier
                .size(6.dp)
                .alpha(if (status == SyncStatus.ONLINE) 1f else pulse)
                .clip(CircleShape)
                .background(color),
        )
        Text(text = label, style = MaterialTheme.typography.labelSmall, color = color)
        Text(
            text = "·",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            text = role.label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun FilterChipRow(
    selected: AlertFilter,
    counts: AlertCounts,
    onSelect: (AlertFilter) -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 10.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        AlertFilter.entries.forEach { entry ->
            FilterChipItem(
                filter = entry,
                count = counts.of(entry),
                selected = entry == selected,
                onClick = { onSelect(entry) },
            )
        }
    }
}

@Composable
private fun FilterChipItem(
    filter: AlertFilter,
    count: Int,
    selected: Boolean,
    onClick: () -> Unit,
) {
    // Chip khẩn cấp mang màu cảnh báo khi được chọn, để lúc đang lọc ở đó người
    // dùng không quên rằng mình đang nhìn một lát cắt chứ không phải toàn bộ.
    val accent = when {
        !selected -> MaterialTheme.colorScheme.onSurfaceVariant
        filter == AlertFilter.URGENT -> MaterialTheme.colorScheme.error
        else -> MaterialTheme.colorScheme.primary
    }

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        modifier = Modifier
            .heightIn(min = MinTouchTarget)
            .clip(RoundedCornerShape(22.dp))
            .background(if (selected) accent.copy(alpha = 0.16f) else Color.Transparent)
            .border(
                width = if (selected) 1.5.dp else 1.dp,
                color = if (selected) accent.copy(alpha = 0.6f) else MaterialTheme.colorScheme.outline,
                shape = RoundedCornerShape(22.dp),
            )
            .clickable(role = SemanticsRole.Tab, onClick = onClick)
            .padding(horizontal = 14.dp),
    ) {
        Text(
            text = filter.label,
            style = MaterialTheme.typography.labelMedium,
            color = if (selected) accent else MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(8.dp))
                .background(accent.copy(alpha = if (selected) 0.28f else 0.14f))
                .padding(horizontal = 6.dp, vertical = 1.dp),
        ) {
            Text(
                text = count.toString(),
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.Bold,
                color = if (selected) accent else MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

/**
 * Thẻ cảnh báo.
 *
 * Dải màu dọc bên trái là thứ đọc được nhanh nhất khi lướt — mắt bắt được nhịp
 * màu ở mép danh sách trước cả khi đọc chữ.
 * Sử dụng IntrinsicSize.Min để dải màu luôn kéo dài đúng 100% chiều cao của thẻ.
 */
@Composable
private fun AlertCard(event: SecurityEvent, onClick: () -> Unit) {
    val tone = event.severity.tone()
    val isOpen = event.state == EventState.OPEN

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(androidx.compose.foundation.layout.IntrinsicSize.Min)
            .clip(MaterialTheme.shapes.medium)
            .background(
                if (isOpen) {
                    tone.container.copy(alpha = 0.35f)
                } else {
                    MaterialTheme.colorScheme.surfaceVariant
                },
            )
            .border(
                width = if (isOpen) 1.5.dp else 1.dp,
                color = if (isOpen) tone.border.copy(alpha = 0.8f) else MaterialTheme.colorScheme.outline,
                shape = MaterialTheme.shapes.medium,
            )
            // clickable đặt sau background/border nên ripple bám đúng bo góc.
            .clickable(role = SemanticsRole.Button, onClick = onClick),
    ) {
        // Dải chỉ thị mức độ kéo chuẩn 100% chiều cao thẻ.
        Box(
            modifier = Modifier
                .width(4.dp)
                .fillMaxHeight()
                .background(tone.content),
        )

        Column(modifier = Modifier.padding(14.dp).weight(1f)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    SeverityBadge(event.severity)
                    if (isOpen) LivePulseBadge() else StateBadge(event.state)
                }

                Text(
                    text = TimeFormat.relative(event.detectedAt),
                    style = MonoLabelSmall,
                    color = if (isOpen) tone.content else MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(top = 10.dp),
            ) {
                Icon(
                    imageVector = event.eventType.icon(),
                    contentDescription = null,
                    tint = tone.content,
                    modifier = Modifier.size(18.dp),
                )
                Text(
                    text = event.eventType.label,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(start = 8.dp),
                )
            }

            Text(
                text = event.description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.padding(top = 6.dp),
            )

            Row(
                modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                CameraTagBadge(event.cameraName)
                Text(
                    text = "Chi tiết →",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
        }
    }
}

