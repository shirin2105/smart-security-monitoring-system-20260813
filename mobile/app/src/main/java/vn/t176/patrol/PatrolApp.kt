package vn.t176.patrol

import android.app.Application
import vn.t176.patrol.data.AppContainer
import vn.t176.patrol.push.NotificationChannels

class PatrolApp : Application() {

    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)

        // Channel phải tồn tại trước khi có thông báo đầu tiên. Tạo lúc khởi
        // động là an toàn nhất — createNotificationChannels bỏ qua nếu đã có.
        NotificationChannels.createAll(this)
    }
}
