package vn.t176.patrol.push

import android.util.Log
import com.google.firebase.messaging.FirebaseMessaging

/**
 * Lấy FCM token của máy và (ở Phase 3) đăng ký với backend.
 *
 * Gọi sau khi đăng nhập chứ không phải lúc mở app: token phải gắn với một
 * người dùng cụ thể thì backend mới biết gửi cảnh báo cho ai.
 */
object PushTokenRegistrar {

    fun fetchAndLog(onToken: (String) -> Unit = {}) {
        FirebaseMessaging.getInstance().token
            .addOnSuccessListener { token ->
                // In ra để lấy đi test từ Firebase Console:
                //   adb logcat -s FCM_TOKEN
                Log.i(AppFirebaseMessagingService.TOKEN_TAG, token)
                onToken(token)

                // Phase 3: POST /api/v1/devices { token, platform: "android" }
            }
            .addOnFailureListener { error ->
                // Thiếu Google Play Services hoặc google-services.json sai cấu
                // hình. Không được làm sập app — app vẫn dùng được, chỉ là
                // không nhận được cảnh báo khi đóng.
                Log.e(
                    AppFirebaseMessagingService.TOKEN_TAG,
                    "Không lấy được FCM token: ${error.message}",
                )
            }
    }

    /**
     * Bất biến mục 4.4: đăng xuất phải gỡ token, nếu không máy này vẫn nhận
     * cảnh báo của người dùng cũ.
     */
    fun unregister() {
        // Phase 3: DELETE /api/v1/devices/{token} trước, rồi mới xóa cục bộ.
        FirebaseMessaging.getInstance().deleteToken()
    }
}
