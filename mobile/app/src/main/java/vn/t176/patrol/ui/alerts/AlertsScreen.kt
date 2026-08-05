package vn.t176.patrol.ui.alerts

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.FilterAlt
import androidx.compose.material.icons.filled.FilterAltOff
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.NotificationsOff
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import vn.t176.patrol.domain.model.Role
import vn.t176.patrol.domain.model.SecurityEvent
import vn.t176.patrol.ui.common.EmptyState
import vn.t176.patrol.ui.common.ErrorState
import vn.t176.patrol.ui.common.LoadingState
import vn.t176.patrol.ui.common.NeutralBadge
import vn.t176.patrol.ui.common.SeverityBadge
import vn.t176.patrol.ui.common.StateBadge
import vn.t176.patrol.ui.common.TimeFormat
import vn.t176.patrol.ui.common.UiState
import vn.t176.patrol.ui.common.color

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
    val onlyImportant by viewModel.onlyImportant.collectAsStateWithLifecycle()

    // Tải lại mỗi lần màn hình trở lại foreground: sau khi Bảo vệ tiếp nhận hay
    // đóng một sự cố ở màn chi tiết, danh sách phải phản ánh ngay trạng thái mới.
    LifecycleResumeEffect(Unit) {
        viewModel.refresh()
        onPauseOrDispose { }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Cảnh báo", style = MaterialTheme.typography.titleMedium)
                        Text(
                            text = role.label,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                actions = {
                    IconButton(onClick = viewModel::toggleFilter) {
                        Icon(
                            imageVector = if (onlyImportant) {
                                Icons.Default.FilterAlt
                            } else {
                                Icons.Default.FilterAltOff
                            },
                            contentDescription = if (onlyImportant) {
                                "Đang lọc mức nghiêm trọng, chạm để xem tất cả"
                            } else {
                                "Đang xem tất cả, chạm để lọc mức nghiêm trọng"
                            },
                            tint = if (onlyImportant) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.onSurfaceVariant
                            },
                        )
                    }
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
        when (val current = state) {
            is UiState.Loading -> LoadingState(
                label = "Đang tải cảnh báo…",
                modifier = Modifier.padding(padding),
            )

            is UiState.Error -> ErrorState(
                message = current.message,
                onRetry = viewModel::refresh,
                modifier = Modifier.padding(padding),
            )

            is UiState.Content -> if (current.data.isEmpty()) {
                EmptyState(
                    title = if (onlyImportant) {
                        "Không có cảnh báo nghiêm trọng nào"
                    } else {
                        "Chưa có cảnh báo nào"
                    },
                    hint = if (onlyImportant) {
                        "Chạm biểu tượng lọc ở trên để xem cả mức thông tin và cảnh báo."
                    } else {
                        null
                    },
                    icon = Icons.Default.NotificationsOff,
                    modifier = Modifier.padding(padding),
                )
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(
                        start = 16.dp,
                        end = 16.dp,
                        top = padding.calculateTopPadding() + 8.dp,
                        bottom = 24.dp,
                    ),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    items(current.data, key = { it.eventId }) { event ->
                        AlertRow(event = event, onClick = { onOpenEvent(event.eventId) })
                    }
                }
            }
        }
    }
}

@Composable
private fun AlertRow(event: SecurityEvent, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                SeverityBadge(event.severity)
                StateBadge(event.state)
            }

            Text(
                text = event.cameraName,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.padding(top = 10.dp),
            )

            Text(
                text = event.description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.padding(top = 4.dp),
            )

            Row(
                modifier = Modifier.fillMaxWidth().padding(top = 10.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                NeutralBadge(event.eventType.label)
                Text(
                    text = TimeFormat.relative(event.detectedAt),
                    style = MaterialTheme.typography.labelSmall,
                    color = event.severity.color(),
                )
            }
        }
    }
}
