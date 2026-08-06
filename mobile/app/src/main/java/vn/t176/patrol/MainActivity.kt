package vn.t176.patrol

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import vn.t176.patrol.data.AppContainer
import vn.t176.patrol.domain.model.UserSession
import vn.t176.patrol.navigation.PatrolNavGraph
import vn.t176.patrol.push.PushTokenRegistrar
import vn.t176.patrol.ui.theme.PatrolTheme

class MainActivity : ComponentActivity() {

    private lateinit var container: AppContainer

    /**
     * Android 13+ bắt buộc xin quyền thông báo lúc chạy. Đây là bẫy số một ở
     * mục 9 của plan: thiếu quyền thì FCM vẫn tới, code vẫn chạy đúng, nhưng
     * không có gì hiện lên và cũng không có lỗi nào để lần ra.
     */
    private val notificationPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { /* no-op */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        container = (application as PatrolApp).container

        setContent {
            PatrolTheme {
                var session by remember { mutableStateOf(container.sessionStore.load()) }

                LaunchedEffect(session) {
                    // Chỉ xin quyền sau khi đã đăng nhập — xin ngay lúc mở app
                    // khi người dùng chưa hiểu app làm gì thì tỉ lệ từ chối cao.
                    if (session != null) {
                        requestNotificationPermissionIfNeeded()
                        // Token phải gắn với người dùng cụ thể thì backend mới
                        // biết gửi cảnh báo cho ai.
                        PushTokenRegistrar.fetchAndLog()
                    }
                }

                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    PatrolNavGraph(
                        container = container,
                        session = session,
                        onSignedIn = { newSession: UserSession ->
                            container.sessionStore.save(newSession)
                            session = newSession
                        },
                        onSignedOut = {
                            // Bất biến mục 4.4: gỡ token trước, nếu không máy
                            // này vẫn nhận cảnh báo của người dùng cũ.
                            PushTokenRegistrar.unregister()
                            container.sessionStore.clear()
                            session = null
                        },
                    )
                }
            }
        }
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return

        val granted = ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.POST_NOTIFICATIONS,
        ) == PackageManager.PERMISSION_GRANTED

        if (!granted) {
            notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
}
