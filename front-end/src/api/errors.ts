/**
 * Phân loại lỗi API để UI hiển thị đúng thông điệp — BAC-53 yêu cầu
 * "clear 403/409 errors", BAC-52 yêu cầu xử lý phiên hết hạn.
 */

export type ApiErrorKind =
  | 'UNAUTHORIZED' // 401 — token thiếu/hết hạn
  | 'FORBIDDEN' // 403 — sai role hoặc ngoài scope
  | 'CONFLICT' // 409 — bản ghi đã đổi, cần tải lại
  | 'NOT_FOUND'
  | 'VALIDATION' // 4xx còn lại
  | 'SERVER' // 5xx
  | 'NETWORK' // không kết nối được
  | 'NOT_IMPLEMENTED'; // backend chưa có endpoint tương ứng

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number;

  constructor(kind: ApiErrorKind, message: string, status = 0) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = status;
  }

  static fromStatus(status: number, detail?: string): ApiError {
    switch (status) {
      case 401:
        return new ApiError(
          'UNAUTHORIZED',
          detail ?? 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.',
          status,
        );
      case 403:
        return new ApiError(
          'FORBIDDEN',
          detail ?? 'Tài khoản của bạn không có quyền thực hiện thao tác này.',
          status,
        );
      case 404:
        return new ApiError('NOT_FOUND', detail ?? 'Không tìm thấy dữ liệu.', status);
      case 409:
        return new ApiError(
          'CONFLICT',
          detail ??
            'Sự cố đã được người khác cập nhật. Vui lòng tải lại để xem trạng thái mới nhất.',
          status,
        );
      default:
        if (status >= 500) {
          return new ApiError('SERVER', detail ?? 'Máy chủ gặp sự cố.', status);
        }
        return new ApiError('VALIDATION', detail ?? 'Yêu cầu không hợp lệ.', status);
    }
  }
}

/** Dùng cho action đã có trong contract nhưng backend chưa implement. */
export function notImplemented(what: string): ApiError {
  return new ApiError(
    'NOT_IMPLEMENTED',
    `Backend chưa hỗ trợ "${what}". Bật chế độ mock (VITE_USE_MOCK=true) để thử luồng này.`,
  );
}

export function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err;
  return new ApiError(
    'NETWORK',
    'Không kết nối được tới máy chủ. Kiểm tra backend có đang chạy không.',
  );
}
