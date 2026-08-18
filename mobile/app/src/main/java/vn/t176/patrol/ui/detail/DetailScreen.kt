package vn.t176.patrol.ui.detail

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.HideImage
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.NoPhotography
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
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
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import vn.t176.patrol.domain.ActionPolicy
import vn.t176.patrol.domain.PatrolAction
import vn.t176.patrol.domain.model.EventState
import vn.t176.patrol.domain.model.Role
import vn.t176.patrol.domain.model.SecurityEvent
import vn.t176.patrol.ui.common.CameraTagBadge
import vn.t176.patrol.ui.common.ErrorState
import vn.t176.patrol.ui.common.LoadingState
import vn.t176.patrol.ui.common.MinTouchTarget
import vn.t176.patrol.ui.common.NeutralBadge
import vn.t176.patrol.ui.common.SeverityBadge
import vn.t176.patrol.ui.common.StateBadge
import vn.t176.patrol.ui.common.TimeFormat
import vn.t176.patrol.ui.common.UiState
import vn.t176.patrol.ui.common.icon
import vn.t176.patrol.ui.theme.MonoLabel
import vn.t176.patrol.ui.theme.MonoLabelSmall
import vn.t176.patrol.ui.theme.StateAcknowledged
import vn.t176.patrol.ui.theme.TacticalSurface
import vn.t176.patrol.ui.theme.tone

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
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(snackbarHost) },
        topBar = {
            TopAppBar(
                colors = TopAppBarDefaults.topAppBarColors(containerColor = TacticalSurface),
                title = { Text("Chi tiết sự cố", style = MaterialTheme.typography.titleMedium) },
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
            .verticalScroll(rememberScrollState()),
    ) {
        SeverityBanner(event)

        Column(modifier = Modifier.padding(16.dp)) {
            IncidentStepper(event.state)

            EvidenceViewport(event, modifier = Modifier.padding(top = 20.dp))

            SectionLabel("Mô tả", modifier = Modifier.padding(top = 20.dp))
            Text(
                text = event.description,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(top = 6.dp),
            )

            SectionLabel("Thông số kỹ thuật", modifier = Modifier.padding(top = 20.dp))
            MetadataGrid(event, modifier = Modifier.padding(top = 8.dp))

            if (actions.isNotEmpty()) {
                SectionLabel("Hành động", modifier = Modifier.padding(top = 24.dp))

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
                        modifier = Modifier.padding(top = 10.dp),
                    )
                }
            }

            if (emptyReason != null) {
                Row(
                    verticalAlignment = Alignment.Top,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 24.dp)
                        .clip(MaterialTheme.shapes.medium)
                        .background(MaterialTheme.colorScheme.surfaceVariant)
                        .border(
                            1.dp,
                            MaterialTheme.colorScheme.outline,
                            MaterialTheme.shapes.medium,
                        )
                        .padding(14.dp),
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
                        modifier = Modifier.padding(start = 10.dp),
                    )
                }
            }

            Spacer(Modifier.height(24.dp))
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

/** Banner đầu màn — mức độ nghiêm trọng phải đọc được ngay trong nửa giây đầu. */
@Composable
private fun SeverityBanner(event: SecurityEvent) {
    val tone = event.severity.tone()

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(tone.container)
            .padding(16.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .clip(RoundedCornerShape(14.dp))
                    .background(tone.content.copy(alpha = 0.18f))
                    .border(1.dp, tone.border, RoundedCornerShape(14.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = event.eventType.icon(),
                    contentDescription = null,
                    tint = tone.content,
                    modifier = Modifier.size(26.dp),
                )
            }

            Column(modifier = Modifier.padding(start = 14.dp)) {
                Text(
                    text = event.eventType.label,
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.onSurface,
                )
                Text(
                    text = "${TimeFormat.full(event.detectedAt)} · ${TimeFormat.relative(event.detectedAt)}",
                    style = MonoLabelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
        }

        // Tên camera dài ("Camera Hành Lang T4") làm badge bị bẻ hai dòng khi
        // xếp chung hàng, nên tách xuống dòng riêng.
        Row(
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            modifier = Modifier.padding(top = 14.dp),
        ) {
            SeverityBadge(event.severity)
            StateBadge(event.state)
        }
        CameraTagBadge(
            event.cameraName,
            modifier = Modifier.padding(top = 8.dp),
        )
    }

    // Vạch màu dày dưới banner thay cho viền — đọc được cả khi cuộn nhanh.
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(3.dp)
            .background(tone.content),
    )
}

/**
 * Tiến trình sự cố.
 *
 * Trả lời câu hỏi "giờ đến lượt ai" mà không bắt người dùng suy luận từ tên
 * trạng thái. Bước hiện tại được tô sáng với hiệu ứng xung nhịp; các bước đã qua có dấu tích.
 */
@Composable
private fun IncidentStepper(state: EventState) {
    val steps = listOf("Phát hiện", "Tiếp nhận", "Xử lý", "Hoàn tất")

    // Ánh xạ 7 trạng thái nghiệp vụ vào 4 bước hiển thị.
    val currentIndex = when (state) {
        EventState.OPEN -> 0
        EventState.ACKNOWLEDGED -> 1
        EventState.PENDING_REVIEW, EventState.CONFIRMED -> 2
        EventState.RESOLVED, EventState.DISMISSED, EventState.EXPIRED -> 3
    }

    val transition = rememberInfiniteTransition(label = "stepper-active")
    val activeGlowAlpha by transition.animateFloat(
        initialValue = 0.25f,
        targetValue = 0.65f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1000),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "glow-alpha",
    )

    Row(
        modifier = Modifier.fillMaxWidth().padding(top = 16.dp),
        verticalAlignment = Alignment.Top,
    ) {
        steps.forEachIndexed { index, label ->
            val done = index < currentIndex
            val active = index == currentIndex
            val color = when {
                done -> StateAcknowledged
                active -> MaterialTheme.colorScheme.primary
                else -> MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.45f)
            }

            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.weight(1f),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    // Nửa đường nối bên trái.
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .height(2.dp)
                            .background(
                                if (index == 0) Color.Transparent
                                else if (done || active) StateAcknowledged.copy(alpha = 0.5f)
                                else MaterialTheme.colorScheme.outline,
                            ),
                    )
                    Box(
                        modifier = Modifier
                            .size(24.dp)
                            .clip(CircleShape)
                            .background(
                                if (active) color.copy(alpha = activeGlowAlpha)
                                else color.copy(alpha = 0.18f),
                            )
                            .border(if (active) 2.dp else 1.dp, color, CircleShape),
                        contentAlignment = Alignment.Center,
                    ) {
                        if (done) {
                            Icon(
                                imageVector = Icons.Default.Check,
                                contentDescription = null,
                                tint = color,
                                modifier = Modifier.size(14.dp),
                            )
                        } else {
                            Box(
                                modifier = Modifier
                                    .size(8.dp)
                                    .clip(CircleShape)
                                    .background(color),
                            )
                        }
                    }
                    // Nửa đường nối bên phải.
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .height(2.dp)
                            .background(
                                if (index == steps.lastIndex) Color.Transparent
                                else if (done) StateAcknowledged.copy(alpha = 0.5f)
                                else MaterialTheme.colorScheme.outline,
                            ),
                    )
                }
                Text(
                    text = label,
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = if (active) FontWeight.Bold else FontWeight.Normal,
                    color = color,
                    modifier = Modifier.padding(top = 6.dp),
                )
            }
        }
    }
}

/**
 * Khung bằng chứng.
 *
 * Bất biến mục 4.1–4.2 của plan: **chỉ hiển thị ảnh đã che mặt xong**, và không
 * lưu ảnh xuống bộ nhớ máy. Watermark nói rõ điều đó ngay trên khung, vì người
 * dùng có quyền biết hệ thống đang bảo vệ quyền riêng tư của ai trong ảnh.
 *
 * Phase 1 chưa tải ảnh thật nên đây là khung giữ chỗ có đủ metadata kỹ thuật và khung ngắm AI.
 */
@Composable
private fun EvidenceViewport(event: SecurityEvent, modifier: Modifier = Modifier) {
    val viewable = event.hasViewableEvidence
    val corner = MaterialTheme.colorScheme.primary.copy(alpha = 0.55f)

    Column(modifier = modifier) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(200.dp)
                .clip(MaterialTheme.shapes.large)
                .background(Color(0xFF040711))
                .border(1.dp, MaterialTheme.colorScheme.outline, MaterialTheme.shapes.large),
        ) {
            // Bốn góc ngắm kiểu khung camera an ninh.
            ViewfinderCorner(Alignment.TopStart, corner)
            ViewfinderCorner(Alignment.TopEnd, corner)
            ViewfinderCorner(Alignment.BottomStart, corner)
            ViewfinderCorner(Alignment.BottomEnd, corner)

            // Telemetry góc trên bên phải
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(4.dp),
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(top = 10.dp, end = 12.dp)
                    .clip(RoundedCornerShape(4.dp))
                    .background(Color.Black.copy(alpha = 0.6f))
                    .padding(horizontal = 6.dp, vertical = 2.dp),
            ) {
                Box(
                    modifier = Modifier
                        .size(5.dp)
                        .clip(CircleShape)
                        .background(StateAcknowledged),
                )
                Text(
                    text = "HD 1080P · IR ACTIVE",
                    style = MonoLabelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Column(
                modifier = Modifier.align(Alignment.Center),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Icon(
                    imageVector = if (viewable) Icons.Default.HideImage else Icons.Default.NoPhotography,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(36.dp),
                )
                Text(
                    text = if (viewable) "Ảnh bằng chứng đã che mặt" else "Ảnh không khả dụng",
                    style = MaterialTheme.typography.bodySmall,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.padding(top = 10.dp),
                )
                Text(
                    text = if (viewable) {
                        "Tải từ máy chủ ở Phase 2, không lưu xuống bộ nhớ máy."
                    } else {
                        "Che mặt chưa hoàn tất nên hệ thống không hiển thị ảnh."
                    },
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 3.dp, start = 24.dp, end = 24.dp),
                )
            }

            // Watermark quyền riêng tư — luôn hiện, kể cả khi chưa có ảnh.
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(5.dp),
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 12.dp)
                    .clip(RoundedCornerShape(6.dp))
                    .background(Color.Black.copy(alpha = 0.7f))
                    .border(0.5.dp, StateAcknowledged.copy(alpha = 0.4f), RoundedCornerShape(6.dp))
                    .padding(horizontal = 10.dp, vertical = 4.dp),
            ) {
                Icon(
                    imageVector = Icons.Default.Shield,
                    contentDescription = null,
                    tint = StateAcknowledged,
                    modifier = Modifier.size(13.dp),
                )
                Text(
                    text = "🛡️ Tự động làm mờ/che mặt AI",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Medium,
                    color = StateAcknowledged,
                )
            }

            // Mã sự cố góc trên bên trái — monospace để đối chiếu.
            Text(
                text = event.eventId.uppercase(),
                style = MonoLabelSmall,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier
                    .align(Alignment.TopStart)
                    .padding(top = 10.dp, start = 12.dp)
                    .clip(RoundedCornerShape(4.dp))
                    .background(Color.Black.copy(alpha = 0.6f))
                    .padding(horizontal = 6.dp, vertical = 2.dp),
            )
        }
    }
}

/**
 * Góc ngắm hình chữ L.
 *
 * Vẽ bằng hai thanh chứ không phải Box có viền: viền vẽ đủ bốn cạnh nên ra ô
 * vuông, không phải góc ngắm. Chữ L mới là ký hiệu người ta nhận ra ngay là
 * khung ngắm camera.
 */
@Composable
private fun androidx.compose.foundation.layout.BoxScope.ViewfinderCorner(
    alignment: Alignment,
    color: Color,
) {
    val arm = 20.dp
    val thickness = 2.dp
    val isTop = alignment == Alignment.TopStart || alignment == Alignment.TopEnd
    val isStart = alignment == Alignment.TopStart || alignment == Alignment.BottomStart

    Box(modifier = Modifier.align(alignment).padding(10.dp).size(arm)) {
        // Thanh ngang
        Box(
            modifier = Modifier
                .align(if (isTop) Alignment.TopStart else Alignment.BottomStart)
                .width(arm)
                .height(thickness)
                .background(color),
        )
        // Thanh dọc
        Box(
            modifier = Modifier
                .align(if (isStart) Alignment.TopStart else Alignment.TopEnd)
                .width(thickness)
                .height(arm)
                .background(color),
        )
    }
}

@Composable
private fun MetadataGrid(event: SecurityEvent, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(MaterialTheme.shapes.medium)
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .border(1.dp, MaterialTheme.colorScheme.outline, MaterialTheme.shapes.medium)
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        MetadataRow("Mã sự cố", event.eventId)
        MetadataRow("Camera", event.cameraName)
        MetadataRow("Khu vực", event.siteId)
        MetadataRow("Phiên bản dữ liệu", "v${event.version}")
        MetadataRow(
            "Che mặt",
            event.artifact?.redactionStatus?.name ?: "KHÔNG CÓ ẢNH",
        )
    }
}

@Composable
private fun MetadataRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(text = value, style = MonoLabel, color = MaterialTheme.colorScheme.onSurface)
    }
}

@Composable
private fun SectionLabel(text: String, modifier: Modifier = Modifier) {
    Text(
        text = text.uppercase(),
        style = MonoLabelSmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = modifier,
    )
}

/**
 * Nút hành động.
 *
 * Nhãn lấy thẳng từ `PatrolAction.label` — domain là nguồn sự thật duy nhất cho
 * tên hành động; phần mô tả bên dưới mới là của lớp trình bày. Toàn bộ nút bị
 * khóa khi có thao tác đang gửi, không riêng nút vừa bấm.
 */
@Composable
private fun ActionButton(
    action: PatrolAction,
    enabled: Boolean,
    inFlight: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val subtitle = when (action) {
        PatrolAction.ACKNOWLEDGE -> "Người trực web thấy ngay là bạn đã nhận việc"
        PatrolAction.RESOLVE -> "Chỉ áp dụng cho sự cố mức nhẹ"
        PatrolAction.FIELD_REPORT -> "Ghi nhận kiểm tra hiện trường, Quản lý đóng trên web"
    }

    val content: @Composable () -> Unit = {
        if (inFlight) {
            CircularProgressIndicator(
                strokeWidth = 2.dp,
                modifier = Modifier.size(18.dp),
                color = MaterialTheme.colorScheme.onPrimary,
            )
            Text(text = "Đang gửi…", modifier = Modifier.padding(start = 10.dp))
        } else {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(text = action.label, fontWeight = FontWeight.Bold)
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Normal,
                )
            }
        }
    }

    // "Tôi đang xử lý" là việc cần làm trước tiên nên để nổi bật và cao hơn hẳn.
    if (action == PatrolAction.ACKNOWLEDGE) {
        Button(
            onClick = onClick,
            enabled = enabled,
            shape = MaterialTheme.shapes.medium,
            colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
            ),
            modifier = modifier.fillMaxWidth().heightIn(min = 64.dp),
        ) {
            content()
        }
    } else {
        OutlinedButton(
            onClick = onClick,
            enabled = enabled,
            shape = MaterialTheme.shapes.medium,
            modifier = modifier.fillMaxWidth().heightIn(min = MinTouchTarget + 8.dp),
        ) {
            content()
        }
    }
}
