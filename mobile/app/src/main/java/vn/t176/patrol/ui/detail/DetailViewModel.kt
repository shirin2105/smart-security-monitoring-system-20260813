package vn.t176.patrol.ui.detail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import vn.t176.patrol.data.repository.ActionRepository
import vn.t176.patrol.data.repository.EventRepository
import vn.t176.patrol.data.repository.StaleVersionException
import vn.t176.patrol.domain.PatrolAction
import vn.t176.patrol.domain.model.SecurityEvent
import vn.t176.patrol.ui.common.UiState
import java.util.UUID

class DetailViewModel(
    private val eventRepository: EventRepository,
    private val actionRepository: ActionRepository,
    private val eventId: String,
    private val actorName: String,
) : ViewModel() {

    private val _state = MutableStateFlow<UiState<SecurityEvent>>(UiState.Loading)
    val state: StateFlow<UiState<SecurityEvent>> = _state.asStateFlow()

    /** Hành động đang gửi — dùng để khóa toàn bộ nút, chống bấm hai lần. */
    private val _submitting = MutableStateFlow<PatrolAction?>(null)
    val submitting: StateFlow<PatrolAction?> = _submitting.asStateFlow()

    private val _message = MutableStateFlow<String?>(null)
    val message: StateFlow<String?> = _message.asStateFlow()

    /**
     * Idempotency-Key giữ theo từng hành động cho tới khi gửi thành công.
     *
     * Nếu sinh key mới mỗi lần bấm thì thao tác thử lại sau lỗi mạng sẽ bị
     * server coi là yêu cầu mới và ghi thành hai bản — đúng thứ mà ràng buộc ở
     * mục 3 của plan muốn tránh.
     */
    private val pendingKeys = mutableMapOf<PatrolAction, String>()

    init {
        load()
    }

    /**
     * Bất biến mục 4.3 của plan: **không tin nội dung notification**. Mở màn này
     * luôn phải hỏi lại trạng thái thật, vì sự cố có thể đã được xử lý trên web
     * trong lúc thông báo còn nằm ở khay.
     */
    fun load() {
        viewModelScope.launch {
            _state.value = UiState.Loading
            try {
                val event = eventRepository.byId(eventId)
                _state.value = if (event == null) {
                    UiState.Error("Không tìm thấy sự cố này. Có thể nó đã bị gỡ.")
                } else {
                    UiState.Content(event)
                }
            } catch (e: Exception) {
                _state.value = UiState.Error(e.message ?: "Không tải được chi tiết sự cố.")
            }
        }
    }

    fun perform(action: PatrolAction, reason: String?) {
        val current = (_state.value as? UiState.Content)?.data ?: return
        if (_submitting.value != null) return // chốt chống double-submit

        viewModelScope.launch {
            _submitting.value = action
            _message.value = null

            val key = pendingKeys.getOrPut(action) { UUID.randomUUID().toString() }

            try {
                val updated = actionRepository.perform(
                    eventId = eventId,
                    action = action,
                    actorName = actorName,
                    reason = reason,
                    expectedVersion = current.version,
                    idempotencyKey = key,
                )
                pendingKeys.remove(action)
                _state.value = UiState.Content(updated)
                _message.value = when (action) {
                    PatrolAction.ACKNOWLEDGE ->
                        "Đã ghi nhận bạn đang xử lý. Người trực web thấy được ngay."

                    PatrolAction.RESOLVE -> "Đã đóng sự cố."
                    PatrolAction.FIELD_REPORT ->
                        "Đã gửi báo cáo. Quản lý sẽ đóng sự cố trên web."
                }
            } catch (e: StaleVersionException) {
                // Người khác đã xử lý trước: báo rồi tải lại trạng thái mới nhất.
                _message.value = e.message
                pendingKeys.remove(action)
                load()
            } catch (e: Exception) {
                _message.value = e.message ?: "Không gửi được thao tác. Vui lòng thử lại."
            } finally {
                _submitting.value = null
            }
        }
    }

    fun dismissMessage() {
        _message.value = null
    }
}
