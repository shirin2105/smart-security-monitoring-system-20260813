package vn.t176.patrol.data.local

import android.content.Context
import vn.t176.patrol.domain.model.Role
import vn.t176.patrol.domain.model.UserSession

/**
 * Lưu phiên đăng nhập.
 *
 * Phase 1 dùng `SharedPreferences` vì chưa có JWT thật để giữ. Khi Phase 2 nối
 * API, đổi sang DataStore Preferences như plan mục 5 và lưu thêm access/refresh
 * token; interface giữ nguyên nên màn hình không phải sửa.
 */
class SessionStore(context: Context) {

    private val prefs = context.getSharedPreferences(FILE, Context.MODE_PRIVATE)

    fun save(session: UserSession) {
        prefs.edit()
            .putString(KEY_USER_ID, session.userId)
            .putString(KEY_NAME, session.displayName)
            .putString(KEY_ROLE, session.role.name)
            .putString(KEY_SITES, session.siteIds.joinToString(","))
            .apply()
    }

    fun load(): UserSession? {
        val userId = prefs.getString(KEY_USER_ID, null) ?: return null
        val roleName = prefs.getString(KEY_ROLE, null) ?: return null
        val role = runCatching { Role.valueOf(roleName) }.getOrNull() ?: return null

        return UserSession(
            userId = userId,
            displayName = prefs.getString(KEY_NAME, "").orEmpty(),
            role = role,
            siteIds = prefs.getString(KEY_SITES, "").orEmpty()
                .split(",")
                .filter { it.isNotBlank() },
        )
    }

    /**
     * Bất biến mục 4.4 của plan: đăng xuất phải xóa device token.
     * Ở Phase 3 hàm này gọi thêm `DELETE /api/v1/devices/{token}` trước khi xóa cục bộ.
     */
    fun clear() {
        prefs.edit().clear().apply()
    }

    private companion object {
        const val FILE = "patrol_session"
        const val KEY_USER_ID = "user_id"
        const val KEY_NAME = "display_name"
        const val KEY_ROLE = "role"
        const val KEY_SITES = "site_ids"
    }
}
