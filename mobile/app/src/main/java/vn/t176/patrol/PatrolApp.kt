package vn.t176.patrol

import android.app.Application
import vn.t176.patrol.data.AppContainer
import vn.t176.patrol.push.NotificationChannels
import vn.t176.patrol.push.PushTokenRegistrar

class PatrolApp : Application() {

    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)

        // Channel phải tồn tại trước khi có thông báo đầu tiên. Tạo lúc khởi
        // động là an toàn nhất — createNotificationChannels bỏ qua nếu đã có.
        NotificationChannels.createAll(this)

        // In token ra Logcat ngay khi mở app để lấy đi test từ Firebase Console
        // mà không cần đăng nhập trước:  adb logcat -s FCM_TOKEN
        // Việc đăng ký token với backend vẫn chờ tới sau khi đăng nhập, vì lúc
        // đó mới biết token thuộc về ai.
        PushTokenRegistrar.fetchAndLog()
    }
}
