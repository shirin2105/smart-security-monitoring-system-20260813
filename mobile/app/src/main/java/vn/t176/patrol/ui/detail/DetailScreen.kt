package vn.t176.patrol.ui.detail

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.HideImage
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import vn.t176.patrol.domain.ActionPolicy
import vn.t176.patrol.domain.PatrolAction
import vn.t176.patrol.domain.model.Role
import vn.t176.patrol.domain.model.SecurityEvent
import vn.t176.patrol.ui.common.ErrorState
import vn.t176.patrol.ui.common.LoadingState
import vn.t176.patrol.ui.common.NeutralBadge
import vn.t176.patrol.ui.common.SeverityBadge
import vn.t176.patrol.ui.common.StateBadge
import vn.t176.patrol.ui.common.TimeFormat
import vn.t176.patrol.ui.common.UiState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DetailScreen(
    viewModel: DetailViewModel,
    role: Role,
    onBack: () -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val submitting by viewModel.submitting.collectAsStateWithLifecycle()
    val message by viewModel.message.collectAsStateWithLifecycle()

    val snackbarHost = remember { SnackbarHostState() }

    LaunchedEffect(message) {
        message?.let {
            snackbarHost.showSnackbar(it)
            viewModel.dismissMessage()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHost) },
        topBar = {
            TopAppBar(
                title = { Text("Chi tiết sự cố") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Quay lại")
                    }
                },
            )
        },
    ) { padding ->
        when (val current = state) {
            is UiState.Loading -> LoadingState(modifier = Modifier.padding(padding))

            is UiState.Error -> ErrorState(
                message = current.message,
                onRetry = viewModel::load,
                modifier = Modifier.padding(padding),
            )

            is UiState.Content -> DetailContent(
                event = current.data,
                role = role,
                submitting = submitting,
                onPerform = viewModel::perform,
                modifier = Modifier.padding(padding),
            )
        }
    }
}

@Composable
private fun DetailContent(
    event: SecurityEvent,
    role: Role,
    submitting: PatrolAction?,
    onPerform: (PatrolAction, String?) -> Unit,
    modifier: Modifier = Modifier,
) {
    val actions = ActionPolicy.allowedActions(role, event)
    val emptyReason = ActionPolicy.emptyReason(role, event)

    // Hành động cần lý do thì mở hộp thoại trước khi gửi.
    var reasonFor by remember { mutableStateOf<PatrolAction?>(null) }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            SeverityBadge(event.severity)
            StateBadge(event.state)
        }

        Text(
            text = event.cameraName,
            style = MaterialTheme.typography.titleLarge,
            modifier = Modifier.padding(top = 12.dp),
        )
        Text(
            text = "${TimeFormat.full(event.detectedAt)} · ${TimeFormat.relative(event.detectedAt)}",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(top = 2.dp),
        )

        EvidenceBlock(event, modifier = Modifier.padding(top = 16.dp))

        Text(
            text = "Mô tả",
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(top = 20.dp),
        )
        Text(
            text = event.description,
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(top = 4.dp),
        )

        Row(
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            modifier = Modifier.padding(top = 12.dp),
        ) {
            NeutralBadge(event.eventType.label)
            NeutralBadge("Phiên bản ${event.version}")
        }

        if (actions.isNotEmpty()) {
            Text(
                text = "Hành động",
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 24.dp),
            )

            actions.forEach { action ->
                ActionButton(
                    action = action,
                    // Khóa toàn bộ nút khi có thao tác đang gửi, không riêng nút vừa bấm.
                    enabled = submitting == null,
                    inFlight = submitting == action,
                    onClick = {
                        if (action.requiresReason) {
                            reasonFor = action
                        } else {
                            onPerform(action, null)
                        }
                    },
                    modifier = Modifier.padding(top = 8.dp),
                )
            }
        }

        if (emptyReason != null) {
            Row(
                verticalAlignment = Alignment.Top,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 24.dp)
                    .background(
                        MaterialTheme.colorScheme.surfaceVariant,
                        RoundedCornerShape(10.dp),
                    )
                    .padding(12.dp),
            ) {
                Icon(
                    imageVector = Icons.Default.Info,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(18.dp),
                )
                Text(
                    text = emptyReason,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(start = 8.dp),
                )
            }
        }
    }

    reasonFor?.let { action ->
        ReasonDialog(
            action = action,
            submitting = submitting == action,
            onDismiss = { reasonFor = null },
            onConfirm = { reason ->
                onPerform(action, reason)
                reasonFor = null
            },
        )
    }
}

@Composable
private fun ActionButton(
    action: PatrolAction,
    enabled: Boolean,
    inFlight: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val content: @Composable () -> Unit = {
        if (inFlight) {
            CircularProgressIndicator(
                strokeWidth = 2.dp,
                modifier = Modifier.size(16.dp),
                color = MaterialTheme.colorScheme.onPrimary,
            )
            Text(text = "Đang gửi…", modifier = Modifier.padding(start = 8.dp))
        } else {
            Text(action.label)
        }
    }

    // "Tôi đang xử lý" là việc cần làm trước tiên nên để nổi bật nhất.
    if (action == PatrolAction.ACKNOWLEDGE) {
        Button(onClick = onClick, enabled = enabled, modifier = modifier.fillMaxWidth()) {
            content()
        }
    } else {
        OutlinedButton(onClick = onClick, enabled = enabled, modifier = modifier.fillMaxWidth()) {
            content()
        }
    }
}

/**
 * Bất biến mục 4.1–4.2 của plan: chỉ hiển thị ảnh đã che mặt xong, và không lưu
 * ảnh xuống bộ nhớ máy. Phase 1 chưa tải ảnh thật nên để chỗ trống có chú thích.
 */
@Composable
private fun EvidenceBlock(event: SecurityEvent, modifier: Modifier = Modifier) {
    val viewable = event.hasViewableEvidence

    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(180.dp)
            .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(12.dp))
            .border(
                1.dp,
                MaterialTheme.colorScheme.outline,
                RoundedCornerShape(12.dp),
            ),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(
                imageVector = Icons.Default.HideImage,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(32.dp),
            )
            Text(
                text = if (viewable) {
                    "Ảnh bằng chứng đã che mặt"
                } else {
                    "Ảnh không khả dụng"
                },
                style = MaterialTheme.typography.bodySmall,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.padding(top = 8.dp),
            )
            Text(
                text = if (viewable) {
                    "Sẽ tải từ máy chủ ở Phase 2, không lưu xuống bộ nhớ máy."
                } else {
                    "Che mặt chưa hoàn tất nên hệ thống không hiển thị ảnh."
                },
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 2.dp, start = 16.dp, end = 16.dp),
            )
        }
    }
}
