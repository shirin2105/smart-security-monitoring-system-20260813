package vn.t176.patrol.ui.common

/** Ba trạng thái mà mọi màn hình đều phải xử lý. */
sealed interface UiState<out T> {
    data object Loading : UiState<Nothing>
    data class Error(val message: String) : UiState<Nothing>
    data class Content<T>(val data: T) : UiState<T>
}
