/**
 * Cấu hình runtime của API client.
 *
 * Không hardcode `http://localhost:8000` nữa — bản trước hardcode ở 8 chỗ nên
 * container `frontend` trong docker-compose không gọi được backend. Giờ lấy từ
 * biến môi trường Vite, mặc định về localhost cho dev.
 */

const DEFAULT_API_BASE = 'http://localhost:8000';

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE
).replace(/\/$/, '');

export const WS_URL =
  import.meta.env.VITE_WS_URL ||
  `${API_BASE_URL.replace(/^http/, 'ws')}/ws/alerts`;

/** Mock mode: chạy UI trên fixture, không cần backend (BAC-49 acceptance). */
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

export const TOKEN_STORAGE_KEY = 'sec_token';
export const USER_STORAGE_KEY = 'sec_user';
