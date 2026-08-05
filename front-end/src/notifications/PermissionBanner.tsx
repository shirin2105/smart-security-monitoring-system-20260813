import { Bell, BellOff } from 'lucide-react';

import { useNotifications } from './NotificationCenter';

/**
 * Lời mời bật thông báo hệ thống.
 *
 * Trình duyệt chỉ cho gọi `requestPermission()` từ thao tác của người dùng, nên
 * bắt buộc phải có nút bấm — không thể tự xin quyền lúc tải trang.
 */
export function PermissionBanner() {
  const { permission, shouldPrompt, request, muted, toggleMuted } = useNotifications();

  if (permission === 'unsupported') {
    return (
      <p className="rounded-xl border border-gray-800 bg-gray-900/60 p-3 text-[11px] leading-relaxed text-gray-400">
        Trình duyệt này không hỗ trợ thông báo hệ thống, hoặc bạn đang mở qua địa chỉ
        không bảo mật. Cảnh báo vẫn hiện trong ứng dụng khi bạn đang mở màn hình này.
      </p>
    );
  }

  if (permission === 'denied') {
    return (
      <p className="rounded-xl border border-amber-500/40 bg-amber-950/30 p-3 text-[11px] leading-relaxed text-amber-200">
        Bạn đã chặn thông báo cho trang này. Để nhận cảnh báo khi không mở app, hãy vào
        cài đặt trình duyệt và cho phép lại. Trong lúc đó cảnh báo vẫn hiện trong ứng dụng.
      </p>
    );
  }

  if (shouldPrompt) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-blue-500/40 bg-blue-950/30 p-3">
        <Bell className="h-5 w-5 shrink-0 text-blue-400" aria-hidden />
        <p className="min-w-0 flex-1 text-[11px] leading-relaxed text-blue-100">
          Bật thông báo để nhận cảnh báo nghiêm trọng ngay cả khi không mở ứng dụng.
        </p>
        <button
          onClick={() => void request()}
          className="shrink-0 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-blue-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
        >
          Bật
        </button>
      </div>
    );
  }

  // permission === 'granted' — chỉ còn công tắc tạm tắt.
  return (
    <button
      onClick={toggleMuted}
      aria-pressed={muted}
      className="flex w-full items-center gap-3 rounded-xl border border-gray-800 bg-gray-900/60 p-3 text-left transition-colors hover:bg-gray-800/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
    >
      {muted ? (
        <BellOff className="h-5 w-5 shrink-0 text-gray-500" aria-hidden />
      ) : (
        <Bell className="h-5 w-5 shrink-0 text-emerald-400" aria-hidden />
      )}
      <span className="min-w-0 flex-1 text-[11px] leading-relaxed text-gray-300">
        {muted
          ? 'Thông báo hệ thống đang tắt. Chạm để bật lại.'
          : 'Thông báo hệ thống đang bật. Chạm để tạm tắt.'}
      </span>
    </button>
  );
}
