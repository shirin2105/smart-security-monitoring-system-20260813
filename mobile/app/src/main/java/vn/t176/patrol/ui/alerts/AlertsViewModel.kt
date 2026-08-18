package vn.t176.patrol.ui.alerts

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import vn.t176.patrol.data.repository.EventRepository
import vn.t176.patrol.domain.model.EventState
import vn.t176.patrol.domain.model.SecurityEvent
import vn.t176.patrol.ui.common.UiState
import java.time.Instant

/**
 * Bộ lọc nhanh trên thanh chip.
 *
 * Ba lựa chọn thôi, và chúng trả lời ba câu hỏi khác nhau mà người trực thật sự
 * hỏi khi mở app: "có gì mới không", "có gì cháy nhà không", "còn gì chưa ai
 * nhận không". Thêm bộ lọc thứ tư là bắt người dùng phải nghĩ.
 */
enum class AlertFilter(val label: String) {
    ALL("Tất cả"),
    URGENT("Khẩn cấp"),
    UNHANDLED("Chưa xử lý"),
    ;

    fun matches(event: SecurityEvent): Boolean = when (this) {
        ALL -> true
        URGENT -> event.severity.isPushWorthy
        UNHANDLED -> event.state == EventState.OPEN
    }
}

/** Số lượng cho từng chip, tính trên toàn bộ danh sách chứ không phải bản đã lọc. */
data class AlertCounts(
    val all: Int = 0,
    val urgent: Int = 0,
    val unhandled: Int = 0,
) {
    fun of(filter: AlertFilter): Int = when (filter) {
        AlertFilter.ALL -> all
        AlertFilter.URGENT -> urgent
        AlertFilter.UNHANDLED -> unhandled
    }
}

/** Trạng thái kết nối suy ra từ lần tải gần nhất — không phải đèn trang trí. */
enum class SyncStatus { SYNCING, ONLINE, OFFLINE }

class AlertsViewModel(
    private val repository: EventRepository,
) : ViewModel() {

    private val _all = MutableStateFlow<UiState<List<SecurityEvent>>>(UiState.Loading)

    /**
     * Push chỉ gửi HIGH/CRITICAL, nhưng trong app hiển thị đủ mọi mức độ.
     * Mặc định vào thẳng "Khẩn cấp" vì đó là thứ người ta mở app để xem.
     */
    private val _filter = MutableStateFlow(AlertFilter.URGENT)
    val filter: StateFlow<AlertFilter> = _filter.asStateFlow()

    private val _refreshing = MutableStateFlow(false)
    val refreshing: StateFlow<Boolean> = _refreshing.asStateFlow()

    private val _lastSyncAt = MutableStateFlow<Instant?>(null)
    val lastSyncAt: StateFlow<Instant?> = _lastSyncAt.asStateFlow()

    /** Bộ đếm luôn tính trên danh sách đầy đủ, nếu không chip sẽ tự đếm chính nó. */
    val counts: StateFlow<AlertCounts> = _all
        .map { state ->
            val data = (state as? UiState.Content)?.data.orEmpty()
            AlertCounts(
                all = data.size,
                urgent = data.count { it.severity.isPushWorthy },
                unhandled = data.count { it.state == EventState.OPEN },
            )
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), AlertCounts())

    val syncStatus: StateFlow<SyncStatus> =
        combine(_all, _refreshing) { all, refreshing ->
            when {
                refreshing -> SyncStatus.SYNCING
                all is UiState.Error -> SyncStatus.OFFLINE
                else -> SyncStatus.ONLINE
            }
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), SyncStatus.SYNCING)

    val state: StateFlow<UiState<List<SecurityEvent>>> =
        combine(_all, _filter) { all, filter ->
            when (all) {
                is UiState.Content -> UiState.Content(all.data.filter(filter::matches))
                else -> all
            }
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), UiState.Loading)

    // Cố ý KHÔNG tải trong `init`: màn hình gọi `refresh()` mỗi lần quay lại
    // foreground, nên trạng thái luôn phản ánh thao tác vừa làm ở màn chi tiết.

    fun setFilter(value: AlertFilter) {
        _filter.value = value
    }

    fun refresh() {
        _refreshing.value = true
        load()
    }

    private fun load() {
        viewModelScope.launch {
            try {
                _all.value = UiState.Content(repository.list())
                _lastSyncAt.value = Instant.now()
            } catch (e: Exception) {
                _all.value = UiState.Error(
                    e.message ?: "Không tải được danh sách cảnh báo.",
                )
            } finally {
                _refreshing.value = false
            }
        }
    }
}
