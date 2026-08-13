package vn.t176.patrol.ui.detail

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import vn.t176.patrol.domain.PatrolAction

/** Đủ dài để có giá trị khi tra cứu lại, đủ ngắn để không cản người đang trực. */
private const val MIN_REASON_LENGTH = 10

/**
 * Nhập lý do trước khi gửi — bắt buộc với "Đã xử lý xong" và "Báo cáo kết quả"
 * theo ràng buộc ghi ở mục 3 của plan.
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

    AlertDialog(
        onDismissRequest = { if (!submitting) onDismiss() },
        title = { Text(action.label) },
        text = {
            androidx.compose.foundation.layout.Column {
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

                OutlinedTextField(
                    value = reason,
                    onValueChange = { reason = it },
                    enabled = !submitting,
                    isError = touched && tooShort,
                    minLines = 3,
                    label = { Text("Lý do") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 12.dp),
                )

                Text(
                    text = if (touched && tooShort) {
                        "Vui lòng nhập tối thiểu $MIN_REASON_LENGTH ký tự."
                    } else {
                        "Nội dung này được ghi vào nhật ký và không sửa hay xóa được."
                    },
                    style = MaterialTheme.typography.labelSmall,
                    color = if (touched && tooShort) {
                        MaterialTheme.colorScheme.error
                    } else {
                        MaterialTheme.colorScheme.onSurfaceVariant
                    },
                    modifier = Modifier.padding(top = 6.dp),
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
            ) {
                Text(if (submitting) "Đang gửi…" else "Gửi")
            }
        },
        dismissButton = {
            TextButton(enabled = !submitting, onClick = onDismiss) {
                Text("Hủy")
            }
        },
    )
}
