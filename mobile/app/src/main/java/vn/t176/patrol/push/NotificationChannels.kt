package vn.t176.patrol.push

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import androidx.core.content.ContextCompat
import vn.t176.patrol.R

/**
 * Hai kênh thông báo riêng biệt (plan mục 6.3), để người dùng chỉnh âm thanh và
 * mức độ làm phiền cho từng loại mà không tắt nhầm loại kia.
 *
 * Cảnh báo quan trọng ở mục 9 của plan: **importance của channel chỉ có tác dụng
 * lúc tạo lần đầu.** Sửa importance rồi cài đè lên sẽ không đổi gì — muốn test
 * lại phải gỡ app cài lại.
 */
object NotificationChannels {

    const val SECURITY_ALERT = "SECURITY_ALERT"
    const val DISPATCH = "DISPATCH"

    fun createAll(context: Context) {
        val manager = ContextCompat.getSystemService(context, NotificationManager::class.java)
            ?: return

        // IMPORTANCE_HIGH là bắt buộc: thấp hơn thì không có heads-up, không âm thanh.
        val alert = NotificationChannel(
            SECURITY_ALERT,
            context.getString(R.string.channel_security_alert_name),
            NotificationManager.IMPORTANCE_HIGH,
        ).apply {
            description = context.getString(R.string.channel_security_alert_desc)
            enableVibration(true)
            setShowBadge(true)
        }

        val dispatch = NotificationChannel(
            DISPATCH,
            context.getString(R.string.channel_dispatch_name),
            NotificationManager.IMPORTANCE_HIGH,
        ).apply {
            description = context.getString(R.string.channel_dispatch_desc)
            enableVibration(true)
            setShowBadge(true)
        }

        manager.createNotificationChannels(listOf(alert, dispatch))
    }
}
