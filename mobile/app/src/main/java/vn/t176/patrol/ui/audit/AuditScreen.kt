package vn.t176.patrol.ui.audit

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
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ReceiptLong
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import vn.t176.patrol.domain.model.AuditEntry
import vn.t176.patrol.ui.common.EmptyState
import vn.t176.patrol.ui.common.ErrorState
import vn.t176.patrol.ui.common.LoadingState
import vn.t176.patrol.ui.common.NeutralBadge
import vn.t176.patrol.ui.common.TimeFormat
import vn.t176.patrol.ui.common.UiState

/**
 * Nhật ký thao tác — màn dành riêng cho Quản lý (bảng mục 2 của plan).
 *
 * Chỉ đọc, phân trang theo cursor để khớp `GET /api/v1/audit?cursor=`.
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
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Nhật ký thao tác", style = MaterialTheme.typography.titleMedium)
                        Text(
                            text = "Chỉ ghi thêm, không sửa hay xóa",
                            style = MaterialTheme.typography.bodySmall,
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
                        top = padding.calculateTopPadding() + 8.dp,
                        bottom = 24.dp,
                    ),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    items(current.data, key = { it.id }) { entry ->
                        AuditRow(entry)
                    }

                    if (hasMore) {
                        item {
                            if (loadingMore) {
                                Row(
                                    modifier = Modifier.fillMaxWidth().padding(12.dp),
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
                                    modifier = Modifier.fillMaxWidth(),
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

@Composable
private fun AuditRow(entry: AuditEntry) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = entry.actorName,
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.primary,
                )
                Text(
                    text = TimeFormat.short(entry.at),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Text(
                text = entry.action,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(top = 6.dp),
            )

            if (entry.reason != null) {
                Text(
                    text = "Lý do: ${entry.reason}",
                    style = MaterialTheme.typography.bodySmall,
                    fontStyle = FontStyle.Italic,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 6.dp),
                )
            }

            Row(
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                modifier = Modifier.padding(top = 10.dp),
            ) {
                NeutralBadge(entry.actorRole.label)
                if (entry.eventId != null) {
                    NeutralBadge("Sự cố ${entry.eventId}")
                }
            }
        }
    }
}
