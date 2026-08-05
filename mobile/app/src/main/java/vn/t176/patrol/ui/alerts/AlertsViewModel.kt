package vn.t176.patrol.ui.alerts

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.launch
import vn.t176.patrol.data.repository.EventRepository
import vn.t176.patrol.domain.model.SecurityEvent
import vn.t176.patrol.ui.common.UiState

class AlertsViewModel(
    private val repository: EventRepository,
) : ViewModel() {

    private val _all = MutableStateFlow<UiState<List<SecurityEvent>>>(UiState.Loading)

    /**
     * Push chỉ gửi HIGH/CRITICAL, nhưng trong app hiển thị đủ mọi mức độ với bộ
     * lọc mặc định là quan trọng — plan mục 2: "Push khác với hiển thị".
     */
    private val _onlyImportant = MutableStateFlow(true)
    val onlyImportant: StateFlow<Boolean> = _onlyImportant.asStateFlow()

    private val _refreshing = MutableStateFlow(false)
    val refreshing: StateFlow<Boolean> = _refreshing.asStateFlow()

    val state: StateFlow<UiState<List<SecurityEvent>>> =
        combine(_all, _onlyImportant) { all, important ->
            when (all) {
                is UiState.Content -> UiState.Content(
                    if (important) all.data.filter { it.severity.isPushWorthy } else all.data,
                )

                else -> all
            }
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), UiState.Loading)

    // Cố ý KHÔNG tải trong `init`: màn hình gọi `refresh()` mỗi lần quay lại
    // foreground, nên trạng thái luôn phản ánh thao tác vừa làm ở màn chi tiết.

    fun toggleFilter() {
        _onlyImportant.value = !_onlyImportant.value
    }

    fun refresh() {
        _refreshing.value = true
        load()
    }

    private fun load() {
        viewModelScope.launch {
            try {
                _all.value = UiState.Content(repository.list())
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
