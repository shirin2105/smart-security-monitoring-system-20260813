package vn.t176.patrol.domain.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Mô hình nghiệp vụ của app, bám contract mục 6 trong PLAN_mobile_app_t176.md.
 *
 * App là kênh phụ: nó chỉ đọc trạng thái và ghi lại việc người ở hiện trường đã
 * làm gì. Mọi quyết định đóng sự cố nghiêm trọng nằm trên web.
 */

@Serializable
enum class Role {
    /** Bảo vệ vật lý — người đi tuần, đến tận nơi kiểm tra. */
    @SerialName("FIELD_GUARD")
    FIELD_GUARD,

    /** Quản lý an ninh — nhận cảnh báo và tra cứu nhật ký. */
    @SerialName("MANAGER")
    MANAGER,
    ;

    val label: String
        get() = when (this) {
            FIELD_GUARD -> "Bảo vệ vật lý"
            MANAGER -> "Quản lý an ninh"
        }
}

@Serializable
enum class Severity {
    @SerialName("INFO")
    INFO,

    @SerialName("WARNING")
    WARNING,

    @SerialName("HIGH")
    HIGH,

    @SerialName("CRITICAL")
    CRITICAL,
    ;

    /**
     * Ngưỡng đẩy push, giống nhau cho cả hai role (plan mục 2).
     * Khác biệt duy nhất giữa hai role là site/camera scope.
     */
    val isPushWorthy: Boolean
        get() = this == HIGH || this == CRITICAL

    val label: String
        get() = when (this) {
            INFO -> "Thông tin"
            WARNING -> "Cảnh báo"
            HIGH -> "Nghiêm trọng"
            CRITICAL -> "Khẩn cấp"
        }
}

@Serializable
enum class EventState {
    @SerialName("OPEN")
    OPEN,

    @SerialName("ACKNOWLEDGED")
    ACKNOWLEDGED,

    @SerialName("PENDING_REVIEW")
    PENDING_REVIEW,

    @SerialName("CONFIRMED")
    CONFIRMED,

    @SerialName("RESOLVED")
    RESOLVED,

    @SerialName("DISMISSED")
    DISMISSED,

    @SerialName("EXPIRED")
    EXPIRED,
    ;

    /** Đã đóng — không còn hành động nào ở hiện trường. */
    val isClosed: Boolean
        get() = this == RESOLVED || this == DISMISSED || this == EXPIRED

    val label: String
        get() = when (this) {
            OPEN -> "Chờ tiếp nhận"
            ACKNOWLEDGED -> "Đang xử lý"
            PENDING_REVIEW -> "Chờ Quản lý duyệt"
            CONFIRMED -> "Đã xác nhận"
            RESOLVED -> "Đã xử lý xong"
            DISMISSED -> "Đã bỏ qua"
            EXPIRED -> "Quá hạn duyệt"
        }
}

@Serializable
enum class EventType {
    @SerialName("ZONE_INTRUSION")
    ZONE_INTRUSION,

    @SerialName("CROWD_THRESHOLD")
    CROWD_THRESHOLD,

    @SerialName("ABANDONED_OBJECT")
    ABANDONED_OBJECT,

    @SerialName("SUSPECTED_FALL")
    SUSPECTED_FALL,

    @SerialName("COVERAGE_DEGRADED")
    COVERAGE_DEGRADED,
    ;

    val label: String
        get() = when (this) {
            ZONE_INTRUSION -> "Xâm nhập vùng cấm"
            CROWD_THRESHOLD -> "Tụ tập đông người"
            ABANDONED_OBJECT -> "Vật thể bỏ quên"
            SUSPECTED_FALL -> "Nghi ngờ té ngã"
            COVERAGE_DEGRADED -> "Suy giảm giám sát"
        }
}

@Serializable
enum class RedactionStatus {
    @SerialName("COMPLETE")
    COMPLETE,

    @SerialName("PENDING")
    PENDING,

    @SerialName("FAILED")
    FAILED,
}

@Serializable
data class EventArtifact(
    val artifactId: String,
    val redactionStatus: RedactionStatus,
)

@Serializable
data class SecurityEvent(
    val eventId: String,
    val eventType: EventType,
    val severity: Severity,
    val state: EventState,
    val cameraName: String,
    val siteId: String,
    /** ISO-8601 kèm offset. */
    val detectedAt: String,
    val description: String,
    /** Optimistic concurrency — gửi kèm khi POST action, lệch thì server trả 409. */
    val version: Int,
    val artifact: EventArtifact? = null,
) {
    /**
     * Ảnh chỉ được xem khi đã che mặt xong. Che mặt lỗi thì artifact bị loại bỏ
     * và app chỉ hiển thị phần dữ liệu mô tả.
     */
    val hasViewableEvidence: Boolean
        get() = artifact?.redactionStatus == RedactionStatus.COMPLETE
}

@Serializable
data class AuditEntry(
    val id: String,
    val actorName: String,
    val actorRole: Role,
    val action: String,
    val eventId: String? = null,
    val reason: String? = null,
    val at: String,
)

@Serializable
data class UserSession(
    val userId: String,
    val displayName: String,
    val role: Role,
    val siteIds: List<String>,
)
