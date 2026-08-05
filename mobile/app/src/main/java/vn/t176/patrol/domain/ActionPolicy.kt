package vn.t176.patrol.domain

import vn.t176.patrol.domain.model.EventState
import vn.t176.patrol.domain.model.Role
import vn.t176.patrol.domain.model.SecurityEvent
import vn.t176.patrol.domain.model.Severity

/**
 * Nút nào được hiện, với role nào, ở severity và state nào.
 *
 * Đây là bản mã hóa của bảng mục 2 và mục 3 trong PLAN_mobile_app_t176.md, và
 * là chỗ duy nhất quyết định điều đó — màn hình không được tự suy luận thêm.
 *
 * Hai bất biến quan trọng nhất, tương ứng mục 4.5 của plan:
 *
 *   1. **Quản lý không có bất kỳ hành động nào trong app.** Vai trò của Quản lý
 *      ở đây là nhận cảnh báo và tra nhật ký; mọi quyết định đóng sự cố nằm
 *      trên web.
 *   2. **Không tồn tại đường nào dẫn tới confirm/dismiss HIGH|CRITICAL hay
 *      approve/decline escalation.** Những hành động đó không có trong enum
 *      dưới đây, nên không thể gọi nhầm từ bất kỳ đâu trong app.
 *
 * Lưu ý: đây là lớp trình bày. Backend vẫn phải kiểm tra lại toàn bộ, vì ẩn nút
 * không phải là biện pháp bảo mật.
 */
enum class PatrolAction(
    val label: String,
    val requiresReason: Boolean,
) {
    /**
     * "Tôi đang xử lý" — nút quan trọng nhất về vận hành. Nó cho người trực web
     * biết đã có người nhận việc, tránh hai bảo vệ cùng chạy tới một chỗ.
     */
    ACKNOWLEDGE(label = "Tôi đang xử lý", requiresReason = false),

    /** "Đã xử lý xong" — chỉ áp dụng cho sự cố nhẹ. */
    RESOLVE(label = "Đã xử lý xong", requiresReason = true),

    /**
     * "Báo cáo kết quả" — ghi nhận việc đã kiểm tra tại hiện trường nhưng
     * KHÔNG đổi state. Sự cố nghiêm trọng do Quản lý đóng trên web.
     */
    FIELD_REPORT(label = "Báo cáo kết quả", requiresReason = true),
}

object ActionPolicy {

    /**
     * Danh sách nút hiện cho một người dùng trên một sự cố.
     * Trả về rỗng nghĩa là chỉ xem.
     */
    fun allowedActions(role: Role, event: SecurityEvent): List<PatrolAction> {
        // Quản lý không thao tác trong app — xem mục 2 của plan.
        if (role == Role.MANAGER) return emptyList()

        // Sự cố đã đóng thì không còn việc gì ở hiện trường.
        if (event.state.isClosed) return emptyList()

        return buildList {
            if (event.state == EventState.OPEN || event.state == EventState.PENDING_REVIEW) {
                add(PatrolAction.ACKNOWLEDGE)
            }

            if (event.state == EventState.ACKNOWLEDGED) {
                when (event.severity) {
                    Severity.INFO, Severity.WARNING -> add(PatrolAction.RESOLVE)
                    Severity.HIGH, Severity.CRITICAL -> add(PatrolAction.FIELD_REPORT)
                }
            }
        }
    }

    /**
     * Câu giải thích khi không có nút nào, để người dùng hiểu vì sao thay vì
     * nhìn một khoảng trống.
     */
    fun emptyReason(role: Role, event: SecurityEvent): String? = when {
        role == Role.MANAGER ->
            "Bạn theo dõi và tra cứu trên app. Các thao tác xử lý sự cố thực hiện trên web."

        event.state.isClosed ->
            "Sự cố đã đóng, không còn thao tác nào ở hiện trường."

        event.state == EventState.CONFIRMED ->
            "Sự cố đã được xác nhận. Quản lý sẽ đóng trên web."

        else -> null
    }
}
