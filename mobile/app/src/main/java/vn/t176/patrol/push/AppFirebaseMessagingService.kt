package vn.t176.patrol.push

import android.util.Log
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

/**
 * Nhận message FCM — kênh duy nhất đánh thức được app đã đóng trên Android.
 *
 * Backend phải gửi **data-only** (không có field `notification`), theo plan mục
 * 6.2. Nếu payload có `notification`, Android tự dựng thông báo khi app ở nền và
 * hàm [onMessageReceived] sẽ không được gọi — mất luôn phần điều hướng và phần
 * tự gỡ thông báo.
 */
class AppFirebaseMessagingService : FirebaseMessagingService() {

    override fun onNewToken(token: String) {
        // Token đổi khi cài lại app, xóa dữ liệu, hoặc khôi phục sang máy khác.
        Log.i(TOKEN_TAG, token)

        // Phase 3: POST /api/v1/devices để backend biết gửi cho ai.
        // Chỉ gửi được khi đã đăng nhập; nếu chưa, `PushTokenRegistrar` sẽ gửi
        // lại ngay sau lần đăng nhập kế tiếp.
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val data = message.data
        when (data["type"]) {
            TYPE_EVENT_ALERT -> handleEventAlert(data)
            TYPE_DISPATCH -> handleDispatch(data)
            else -> Log.w(TAG, "Bỏ qua message không rõ loại: ${data["type"]}")
        }
    }

    private fun handleEventAlert(data: Map<String, String>) {
        val eventId = data["eventId"] ?: return

        // `RESOLVED` nghĩa là sự cố đã được xử lý ở nơi khác — gỡ thông báo khỏi
        // khay để người trực không chạy tới một việc đã xong.
        if (data["action"] == ACTION_RESOLVED) {
            NotificationBuilder.cancelEventAlert(this, eventId)
            return
        }

        val severity = data["severity"].orEmpty()
        val cameraName = data["cameraName"] ?: "Camera không rõ"
        val eventType = data["eventType"].orEmpty()

        NotificationBuilder.showEventAlert(
            context = this,
            eventId = eventId,
            title = "${severityLabel(severity)} · $cameraName",
            body = eventTypeLabel(eventType),
            isCritical = severity == "CRITICAL",
        )
    }

    private fun handleDispatch(data: Map<String, String>) {
        // DISPATCH là đường duy nhất để sự cố INFO/WARNING tới được người đi
        // tuần, vì push tự động chỉ gửi HIGH/CRITICAL (plan mục 6.2).
        NotificationBuilder.showDispatch(
            context = this,
            dispatchId = data["dispatchId"] ?: return,
            eventId = data["eventId"],
            fromUser = data["fromUser"] ?: "Trực ca",
            message = data["message"].orEmpty(),
        )
    }

    /**
     * Nhãn hiển thị suy ra từ mã, không lấy chữ sẵn trong payload.
     *
     * Bất biến mục 4.1: thông báo hiện cả trên màn hình khóa nên không được
     * chứa PII. Payload chỉ mang mã và tên camera.
     */
    private fun severityLabel(severity: String) = when (severity) {
        "CRITICAL" -> "Khẩn cấp"
        "HIGH" -> "Nghiêm trọng"
        "WARNING" -> "Cảnh báo"
        else -> "Thông tin"
    }

    private fun eventTypeLabel(eventType: String) = when (eventType) {
        "ZONE_INTRUSION" -> "Phát hiện xâm nhập vùng cấm"
        "CROWD_THRESHOLD" -> "Phát hiện tụ tập đông người"
        "ABANDONED_OBJECT" -> "Phát hiện vật thể bỏ quên"
        "SUSPECTED_FALL" -> "Nghi ngờ có người té ngã"
        else -> "Sự cố an ninh cần kiểm tra"
    }

    companion object {
        private const val TAG = "PatrolFCM"

        /** Lọc bằng `adb logcat -s FCM_TOKEN` để lấy token đem đi test. */
        const val TOKEN_TAG = "FCM_TOKEN"

        private const val TYPE_EVENT_ALERT = "EVENT_ALERT"
        private const val TYPE_DISPATCH = "DISPATCH"
        private const val ACTION_RESOLVED = "RESOLVED"
    }
}
