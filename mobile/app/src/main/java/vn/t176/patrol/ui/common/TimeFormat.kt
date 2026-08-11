package vn.t176.patrol.ui.common

import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit

/**
 * Định dạng mốc thời gian ISO-8601 sang giờ địa phương.
 *
 * Backend trả UTC. Nếu chuỗi thiếu offset thì coi là UTC — đây đúng là lỗi đã
 * gặp ở bản web, nơi timestamp trần bị hiểu thành giờ máy và lệch 7 tiếng.
 */
object TimeFormat {

    private val formatter: DateTimeFormatter =
        DateTimeFormatter.ofPattern("HH:mm:ss dd/MM/yyyy").withZone(ZoneId.systemDefault())

    private val shortFormatter: DateTimeFormatter =
        DateTimeFormatter.ofPattern("HH:mm").withZone(ZoneId.systemDefault())

    private fun parse(iso: String): Instant? = runCatching {
        Instant.parse(if (iso.endsWith("Z") || iso.contains('+')) iso else "${iso}Z")
    }.getOrNull()

    fun full(iso: String): String = parse(iso)?.let(formatter::format) ?: iso

    fun short(iso: String): String = parse(iso)?.let(shortFormatter::format) ?: iso

    /** "3 phút trước" — giúp người trực ước lượng độ mới mà không phải tính nhẩm. */
    fun relative(iso: String, now: Instant = Instant.now()): String {
        val instant = parse(iso) ?: return iso
        val minutes = ChronoUnit.MINUTES.between(instant, now)
        return when {
            minutes < 1 -> "vừa xong"
            minutes < 60 -> "$minutes phút trước"
            minutes < 60 * 24 -> "${minutes / 60} giờ trước"
            else -> "${minutes / (60 * 24)} ngày trước"
        }
    }
}
