package vn.t176.patrol.ui.audit

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import vn.t176.patrol.data.repository.AuditRepository
import vn.t176.patrol.domain.model.AuditEntry
import vn.t176.patrol.ui.common.UiState

class AuditViewModel(
    private val repository: AuditRepository,
) : ViewModel() {

    private val _state = MutableStateFlow<UiState<List<AuditEntry>>>(UiState.Loading)
    val state: StateFlow<UiState<List<AuditEntry>>> = _state.asStateFlow()

    private val _loadingMore = MutableStateFlow(false)
    val loadingMore: StateFlow<Boolean> = _loadingMore.asStateFlow()

    private var nextCursor: Int? = null

    /** Hết trang thì ẩn nút "tải thêm" thay vì để người dùng bấm vào khoảng không. */
    private val _hasMore = MutableStateFlow(true)
    val hasMore: StateFlow<Boolean> = _hasMore.asStateFlow()

    // Không tải trong `init` — màn hình gọi `reload()` khi quay lại foreground,
    // để thao tác Bảo vệ vừa thực hiện xuất hiện ngay trong nhật ký.

    fun reload() {
        viewModelScope.launch {
            _state.value = UiState.Loading
            nextCursor = null
            try {
                val page = repository.page(null)
                nextCursor = page.nextCursor
                _hasMore.value = page.nextCursor != null
                _state.value = UiState.Content(page.entries)
            } catch (e: Exception) {
                _state.value = UiState.Error(e.message ?: "Không tải được nhật ký.")
            }
        }
    }

    fun loadMore() {
        val cursor = nextCursor ?: return
        val current = (_state.value as? UiState.Content)?.data ?: return
        if (_loadingMore.value) return

        viewModelScope.launch {
            _loadingMore.value = true
            try {
                val page = repository.page(cursor)
                nextCursor = page.nextCursor
                _hasMore.value = page.nextCursor != null
                _state.value = UiState.Content(current + page.entries)
            } catch (_: Exception) {
                // Lỗi tải thêm không được xóa mất phần đã hiển thị.
                _hasMore.value = false
            } finally {
                _loadingMore.value = false
            }
        }
    }
}
