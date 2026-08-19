package vn.t176.patrol.ui.audit

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ReceiptLong
import androidx.compose.material.icons.automirrored.filled.Assignment
import androidx.compose.material.icons.automirrored.filled.DirectionsRun
import androidx.compose.material.icons.automirrored.filled.FactCheck
import androidx.compose.material.icons.filled.TaskAlt
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import vn.t176.patrol.domain.model.AuditEntry
import vn.t176.patrol.domain.model.Role
import vn.t176.patrol.ui.common.EmptyState
import vn.t176.patrol.ui.common.ErrorState
import vn.t176.patrol.ui.common.LoadingState
import vn.t176.patrol.ui.common.MinTouchTarget
import vn.t176.patrol.ui.common.TimeFormat
import vn.t176.patrol.ui.common.UiState
import vn.t176.patrol.ui.theme.MonoLabelSmall
import vn.t176.patrol.ui.theme.StateAcknowledged
import vn.t176.patrol.ui.theme.TacticalSurface

/**
 * Nhật ký thao tác — màn dành riêng cho Quản lý (bảng mục 2 của plan).
 *
 * Chỉ đọc, phân trang theo cursor để khớp `GET /api/v1/audit?cursor=`.
 *
 * Trình bày dạng dòng thời gian chứ không phải danh sách thẻ rời: nhật ký được
 * đọc để dựng lại **chuỗi diễn biến** — ai làm gì, lúc nào, theo thứ tự nào —
 * nên đường nối dọc giữa các mục mang đúng thông tin đó.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AuditScreen(
    viewModel: AuditViewModel,
    onBack: () -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val hasMore by viewModel.hasMore.collectAsStateWithLifecycle()
    val loadingMore by viewModel.loadingMore.collectAsStateWithLifecycle()

    LifecycleResumeEffect(Unit) {
        viewModel.reload()
        onPauseOrDispose { }
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            TopAppBar(
                colors = TopAppBarDefaults.topAppBarColors(containerColor = TacticalSurface),
                title = {
                    Column {
                        Text("Nhật ký thao tác", style = MaterialTheme.typography.titleMedium)
                        Text(
                            text = "Chỉ ghi thêm, không sửa hay xóa",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Quay lại")
                    }
                },
            )
        },
    ) { padding ->
        when (val current = state) {
            is UiState.Loading -> LoadingState(
                label = "Đang tải nhật ký…",
                modifier = Modifier.padding(padding),
            )

            is UiState.Error -> ErrorState(
                message = current.message,
                onRetry = viewModel::reload,
                modifier = Modifier.padding(padding),
            )

            is UiState.Content -> if (current.data.isEmpty()) {
                EmptyState(
                    title = "Chưa có thao tác nào được ghi nhận",
                    hint = "Nhật ký xuất hiện ngay khi có người xử lý một sự cố.",
                    icon = Icons.AutoMirrored.Filled.ReceiptLong,
                    modifier = Modifier.padding(padding),
                )
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(
                        start = 16.dp,
                        end = 16.dp,
                        top = padding.calculateTopPadding() + 12.dp,
                        bottom = 24.dp,
                    ),
                ) {
                    itemsIndexed(current.data) { index, entry ->
                        TimelineRow(
                            entry = entry,
                            isFirst = index == 0,
                            isLast = index == current.data.lastIndex && !hasMore,
                        )
                    }

                    if (hasMore) {
                        item {
                            if (loadingMore) {
                                Row(
                                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                                    horizontalArrangement = Arrangement.Center,
                                ) {
                                    CircularProgressIndicator(
                                        strokeWidth = 2.dp,
                                        modifier = Modifier.size(20.dp),
                                    )
                                }
                            } else {
                                OutlinedButton(
                                    onClick = viewModel::loadMore,
                                    shape = MaterialTheme.shapes.medium,
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .heightIn(min = MinTouchTarget)
                                        .padding(top = 8.dp),
                                ) {
                                    Text("Tải thêm")
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

/** `items` có index — LazyColumn dựng sẵn nhưng tên khác nên gói lại cho gọn. */
private inline fun androidx.compose.foundation.lazy.LazyListScope.itemsIndexed(
    items: List<AuditEntry>,
    crossinline itemContent: @Composable (Int, AuditEntry) -> Unit,
) {
    items(count = items.size, key = { items[it].id }) { index ->
        itemContent(index, items[index])
    }
}

@Composable
private fun TimelineRow(entry: AuditEntry, isFirst: Boolean, isLast: Boolean) {
    val kind = ActionKind.of(entry.action)

    Row(modifier = Modifier.fillMaxWidth().height(IntrinsicSize.Min)) {
        // Cột dòng thời gian: đường dọc + nút tròn.
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.width(32.dp).fillMaxHeight(),
        ) {
            Box(
                modifier = Modifier
                    .width(2.dp)
                    .height(if (isFirst) 0.dp else 10.dp)
                    .background(MaterialTheme.colorScheme.outline),
            )
            Box(
                modifier = Modifier
                    .size(26.dp)
                    .clip(CircleShape)
                    .background(kind.color.copy(alpha = 0.16f))
                    .border(1.5.dp, kind.color.copy(alpha = 0.6f), CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = kind.icon,
                    contentDescription = null,
                    tint = kind.color,
                    modifier = Modifier.size(14.dp),
                )
            }
            if (!isLast) {
                Box(
                    modifier = Modifier
                        .width(2.dp)
                        .weight(1f)
                        .background(MaterialTheme.colorScheme.outline),
                )
            }
        }

        Column(
            modifier = Modifier
                .weight(1f)
                .padding(start = 10.dp, bottom = 14.dp)
                .clip(MaterialTheme.shapes.medium)
                .background(MaterialTheme.colorScheme.surfaceVariant)
                .border(1.dp, MaterialTheme.colorScheme.outline, MaterialTheme.shapes.medium)
                .padding(12.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    ActorAvatar(entry.actorName, entry.actorRole)
                    Column(modifier = Modifier.padding(start = 8.dp)) {
                        Text(
                            text = entry.actorName,
                            style = MaterialTheme.typography.labelLarge,
                        )
                        Text(
                            text = entry.actorRole.label,
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
                Text(
                    text = TimeFormat.short(entry.at),
                    style = MonoLabelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            // Chip phân loại hành động — đọc được kể cả khi tên hành động dài.
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(4.dp),
                modifier = Modifier
                    .padding(top = 10.dp)
                    .clip(RoundedCornerShape(6.dp))
                    .background(kind.color.copy(alpha = 0.14f))
                    .border(1.dp, kind.color.copy(alpha = 0.4f), RoundedCornerShape(6.dp))
                    .padding(horizontal = 8.dp, vertical = 3.dp),
            ) {
                Icon(
                    imageVector = kind.icon,
                    contentDescription = null,
                    tint = kind.color,
                    modifier = Modifier.size(12.dp),
                )
                Text(text = kind.label, style = MonoLabelSmall, color = kind.color)
            }

            Text(
                text = entry.action,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(top = 8.dp),
            )

            if (entry.reason != null) {
                // Hộp trích dẫn: vạch màu bên trái để tách lời người dùng khỏi
                // mô tả do hệ thống sinh ra.
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 10.dp)
                        .height(IntrinsicSize.Min),
                ) {
                    Box(
                        modifier = Modifier
                            .width(3.dp)
                            .fillMaxHeight()
                            .clip(RoundedCornerShape(2.dp))
                            .background(kind.color.copy(alpha = 0.6f)),
                    )
                    Text(
                        text = entry.reason,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(start = 10.dp),
                    )
                }
            }

            if (entry.eventId != null) {
                Text(
                    text = "Sự cố ${entry.eventId}",
                    style = MonoLabelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 10.dp),
                )
            }
        }
    }
}

/** Chữ cái đầu của tên — rẻ hơn tải ảnh và không rò dữ liệu cá nhân. */
@Composable
private fun ActorAvatar(name: String, role: Role) {
    val color = if (role == Role.MANAGER) StateAcknowledged else MaterialTheme.colorScheme.primary
    val initial = name.trim().split(" ").lastOrNull()?.firstOrNull()?.uppercase() ?: "?"

    Box(
        modifier = Modifier
            .size(30.dp)
            .clip(CircleShape)
            .background(color.copy(alpha = 0.16f))
            .border(1.dp, color.copy(alpha = 0.45f), CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = initial,
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Bold,
            color = color,
        )
    }
}

/**
 * Phân loại hành động từ chuỗi mô tả.
 *
 * Backend trả `action` dạng câu tiếng Việt chứ không phải mã, nên phải đoán từ
 * nội dung. Không khớp thì rơi về nhãn trung tính — thà hiện chip xám còn hơn
 * gán nhầm loại rồi người đọc tin theo.
 */
private enum class ActionKind(
    val label: String,
    val icon: ImageVector,
    val colorProvider: @Composable () -> Color,
) {
    ACKNOWLEDGE("ACKNOWLEDGE", Icons.AutoMirrored.Filled.DirectionsRun, { MaterialTheme.colorScheme.primary }),
    RESOLVE("RESOLVE", Icons.Default.TaskAlt, { StateAcknowledged }),
    FIELD_REPORT("FIELD_REPORT", Icons.AutoMirrored.Filled.FactCheck, { MaterialTheme.colorScheme.tertiary }),
    OTHER("HOẠT ĐỘNG", Icons.AutoMirrored.Filled.Assignment, { MaterialTheme.colorScheme.onSurfaceVariant }),
    ;

    val color: Color
        @Composable get() = colorProvider()

    companion object {
        fun of(action: String): ActionKind {
            val text = action.lowercase()
            return when {
                "tiếp nhận" in text || "đang xử lý" in text || "acknowledge" in text -> ACKNOWLEDGE
                "xử lý xong" in text || "đóng" in text || "resolve" in text -> RESOLVE
                "báo cáo" in text || "field" in text -> FIELD_REPORT
                else -> OTHER
            }
        }
    }
}
