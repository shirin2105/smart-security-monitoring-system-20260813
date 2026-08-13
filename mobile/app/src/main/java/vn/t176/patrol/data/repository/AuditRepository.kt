package vn.t176.patrol.data.repository

import kotlinx.coroutines.delay
import vn.t176.patrol.data.fake.FakeEventStore
import vn.t176.patrol.domain.model.AuditEntry

/** Một trang audit kèm con trỏ tới trang sau. `null` nghĩa là hết. */
data class AuditPage(
    val entries: List<AuditEntry>,
    val nextCursor: Int?,
)

interface AuditRepository {
    suspend fun page(cursor: Int?): AuditPage
}

/**
 * Audit là màn dành riêng cho Quản lý (bảng mục 2 của plan).
 * Đọc từ store dùng chung nên hành động Bảo vệ vừa làm hiện ngay ở đây.
 * Phân trang theo cursor để khớp contract `GET /api/v1/audit?cursor=`.
 */
class FakeAuditRepository(
    private val store: FakeEventStore,
) : AuditRepository {

    override suspend fun page(cursor: Int?): AuditPage {
        delay(FAKE_LATENCY_MS)
        val all = store.snapshotAudit()
        val from = cursor ?: 0
        val slice = all.drop(from).take(PAGE_SIZE)
        val next = (from + PAGE_SIZE).takeIf { it < all.size }
        return AuditPage(entries = slice, nextCursor = next)
    }

    private companion object {
        const val FAKE_LATENCY_MS = 350L
        const val PAGE_SIZE = 4
    }
}
