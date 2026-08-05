package vn.t176.patrol.push

import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import vn.t176.patrol.MainActivity
import vn.t176.patrol.R

/**
 * Dựng và gỡ thông báo.
 *
 * Tách khỏi tầng FCM có chủ đích: Phase 1 gọi được ngay để kiểm chứng phần
 * hiển thị và quyền trên máy thật, trước khi Firebase sẵn sàng. Phase 3 chỉ cần
 * gọi đúng những hàm này từ `AppFirebaseMessagingService`.
 *
 * Bất biến mục 4.1 của plan: nội dung thông báo **không chứa ảnh và không chứa
 * PII** — nó hiện cả trên màn hình khóa. Chỉ camera, loại sự kiện, mức độ, giờ.
 */
object NotificationBuilder {

    /**
     * Dùng hash của eventId làm id thông báo để gỡ đúng cái khi sự cố được xử lý
     * nơi khác. Không dùng số tăng dần — sẽ không biết cancel cái nào (mục 9).
     */
    fun notificationIdFor(eventId: String): Int = eventId.hashCode()

    fun showEventAlert(
        context: Context,
        eventId: String,
        title: String,
        body: String,
        isCritical: Boolean,
    ) {
        val intent = Intent(
            Intent.ACTION_VIEW,
            Uri.parse("app://event/$eventId"),
            context,
            MainActivity::class.java,
        ).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        val pending = PendingIntent.getActivity(
            context,
            notificationIdFor(eventId),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val notification = NotificationCompat.Builder(context, NotificationChannels.SECURITY_ALERT)
            .setSmallIcon(R.drawable.ic_shield)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setAutoCancel(true)
            .setContentIntent(pending)
            // Sự cố khẩn cấp không tự biến mất — người trực phải chủ động gạt đi.
            .setOngoing(false)
            .apply { if (isCritical) setDefaults(NotificationCompat.DEFAULT_ALL) }
            .build()

        ContextCompat.getSystemService(context, NotificationManager::class.java)
            ?.notify(notificationIdFor(eventId), notification)
    }

    /**
     * Gỡ thông báo khi sự cố đã được xử lý ở nơi khác — tương ứng message FCM
     * `action=RESOLVED` ở mục 6.2 của plan.
     */
    fun cancelEventAlert(context: Context, eventId: String) {
        ContextCompat.getSystemService(context, NotificationManager::class.java)
            ?.cancel(notificationIdFor(eventId))
    }
}
