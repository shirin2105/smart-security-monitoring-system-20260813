package vn.t176.patrol.ui.login

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import vn.t176.patrol.domain.model.Role
import vn.t176.patrol.domain.model.UserSession

/**
 * Đăng nhập giả cho Phase 1 — chọn vai trò để kiểm chứng điều hướng và
 * `ActionPolicy`. Phase 2 thay bằng `POST /api/v1/auth/login` thật, giữ nguyên
 * callback nên màn hình không phải viết lại.
 */
@Composable
fun LoginScreen(onSignedIn: (UserSession) -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Icon(
            imageVector = Icons.Default.Shield,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(56.dp),
        )

        Text(
            text = "T176 An ninh",
            style = MaterialTheme.typography.headlineSmall,
            modifier = Modifier.padding(top = 16.dp),
        )
        Text(
            text = "Kênh cảnh báo cho người không ngồi trước màn hình",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 6.dp),
        )

        Card(modifier = Modifier.fillMaxWidth().padding(top = 32.dp)) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Chọn vai trò để tiếp tục",
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )

                Button(
                    onClick = { onSignedIn(managerSession()) },
                    modifier = Modifier.fillMaxWidth().padding(top = 16.dp),
                ) {
                    Text("Quản lý an ninh")
                }

                OutlinedButton(
                    onClick = { onSignedIn(guardSession()) },
                    modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                ) {
                    Text("Bảo vệ vật lý")
                }

                Text(
                    text = "Dữ liệu đang lấy từ fixture trong máy, chưa nối backend.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 16.dp),
                )
            }
        }
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
