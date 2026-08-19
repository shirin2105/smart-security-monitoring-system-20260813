package vn.t176.patrol.ui.detail

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role as SemanticsRole
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.DialogProperties
import vn.t176.patrol.domain.PatrolAction
import vn.t176.patrol.ui.common.MinTouchTarget
import vn.t176.patrol.ui.theme.MonoLabelSmall
import vn.t176.patrol.ui.theme.StateAcknowledged

/** Đủ dài để có giá trị khi tra cứu lại, đủ ngắn để không cản người đang trực. */
private const val MIN_REASON_LENGTH = 10

/**
 * Lý do mẫu.
 *
 * Người trực thường gõ khi một tay cầm đèn pin. Nút bấm sẵn giúp họ xong việc
 * trong hai chạm, và quan trọng hơn là làm cho nhật ký **nhất quán** — mười
 * người mô tả cùng một tình huống theo mười cách khác nhau thì tra cứu về sau
 * rất khó. Vẫn luôn cho sửa lại, vì tình huống thật hiếm khi khớp hoàn toàn.
 */
private val RESOLVE_PRESETS = listOf(
    "Đã kiểm tra, không phát hiện bất thường",
    "Báo động giả do động vật đi qua",
    "Báo động giả do thay đổi ánh sáng",
    "Nhân viên ra vào đúng quy định",
)

private val FIELD_REPORT_PRESETS = listOf(
    "Đã tới hiện trường, khu vực đã an toàn",
    "Đã tới nơi, cần Quản lý xem thêm camera",
    "Phát hiện người lạ, đã mời ra khỏi khu vực",
    "Vật thể đã được chủ sở hữu nhận lại",
)

/**
 * Nhập lý do trước khi gửi — bắt buộc với "Đã xử lý xong" và "Báo cáo kết quả"
 * theo ràng buộc ghi ở mục 3 của plan. Tối thiểu 10 ký tự.
 */
@Composable
fun ReasonDialog(
    action: PatrolAction,
    submitting: Boolean,
    onDismiss: () -> Unit,
    onConfirm: (String) -> Unit,
) {
    var reason by remember { mutableStateOf("") }
    var touched by remember { mutableStateOf(false) }

    val trimmed = reason.trim()
    val tooShort = trimmed.length < MIN_REASON_LENGTH

    val presets = when (action) {
        PatrolAction.FIELD_REPORT -> FIELD_REPORT_PRESETS
        else -> RESOLVE_PRESETS
    }

    AlertDialog(
        onDismissRequest = { if (!submitting) onDismiss() },
        // Không cho đóng bằng chạm ra ngoài khi đang gửi — dễ mất thao tác giữa chừng.
        properties = DialogProperties(
            dismissOnBackPress = !submitting,
            dismissOnClickOutside = !submitting,
        ),
        shape = MaterialTheme.shapes.large,
        containerColor = MaterialTheme.colorScheme.surfaceContainerHigh,
        title = { Text(action.label, style = MaterialTheme.typography.titleMedium) },
        text = {
            Column {
                Text(
                    text = when (action) {
                        PatrolAction.FIELD_REPORT ->
                            "Ghi lại bạn đã kiểm tra được gì tại hiện trường. " +
                                "Quản lý dựa vào đây để quyết định trên web."

                        else ->
                            "Ghi rõ căn cứ để người đọc lại sau hiểu được quyết định này."
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )

                Text(
                    text = "CHỌN NHANH",
                    style = MonoLabelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 14.dp),
                )

                Column(
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                    modifier = Modifier.padding(top = 8.dp),
                ) {
                    presets.forEach { preset ->
                        PresetRow(
                            text = preset,
                            selected = trimmed == preset,
                            enabled = !submitting,
                            onClick = {
                                reason = preset
                                touched = true
                            },
                        )
                    }
                }

                OutlinedTextField(
                    value = reason,
                    onValueChange = {
                        reason = it
                        touched = true
                    },
                    enabled = !submitting,
                    isError = touched && tooShort,
                    minLines = 2,
                    label = { Text("Lý do (có thể sửa lại)") },
                    supportingText = {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                text = if (touched && tooShort) {
                                    "Cần tối thiểu $MIN_REASON_LENGTH ký tự."
                                } else {
                                    "Ghi vào nhật ký, không sửa hay xóa được."
                                },
                                style = MaterialTheme.typography.labelSmall,
                                // weight để chữ dài co lại, nhường chỗ cho bộ đếm.
                                // Thiếu dòng này thì "38/10" bị bẻ thành ba dòng.
                                modifier = Modifier.weight(1f, fill = false),
                            )
                            Text(
                                text = "${trimmed.length}/$MIN_REASON_LENGTH",
                                style = MonoLabelSmall,
                                maxLines = 1,
                                softWrap = false,
                                color = if (tooShort) {
                                    MaterialTheme.colorScheme.error
                                } else {
                                    StateAcknowledged
                                },
                                modifier = Modifier.padding(start = 10.dp),
                            )
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 12.dp),
                )
            }
        },
        confirmButton = {
            TextButton(
                enabled = !submitting && !tooShort,
                onClick = {
                    touched = true
                    if (!tooShort) onConfirm(trimmed)
                },
                modifier = Modifier.heightIn(min = MinTouchTarget),
            ) {
                Text(if (submitting) "Đang gửi…" else "Gửi")
            }
        },
        dismissButton = {
            TextButton(
                enabled = !submitting,
                onClick = onDismiss,
                modifier = Modifier.heightIn(min = MinTouchTarget),
            ) {
                Text("Hủy")
            }
        },
    )
}

@Composable
private fun PresetRow(
    text: String,
    selected: Boolean,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    val accent = MaterialTheme.colorScheme.primary

    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = MinTouchTarget)
            .clip(RoundedCornerShape(10.dp))
            .background(
                if (selected) accent.copy(alpha = 0.14f) else MaterialTheme.colorScheme.surfaceVariant,
            )
            .border(
                width = if (selected) 1.5.dp else 1.dp,
                color = if (selected) accent.copy(alpha = 0.6f) else MaterialTheme.colorScheme.outline,
                shape = RoundedCornerShape(10.dp),
            )
            .clickable(enabled = enabled, role = SemanticsRole.RadioButton, onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 8.dp),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodySmall,
            textAlign = TextAlign.Start,
            color = if (selected) accent else MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.weight(1f),
        )
        if (selected) {
            Icon(
                imageVector = Icons.Default.Check,
                contentDescription = null,
                tint = accent,
                modifier = Modifier.size(18.dp).padding(start = 6.dp),
            )
        }
    }
}
