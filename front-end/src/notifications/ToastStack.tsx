import { useNavigate } from 'react-router-dom';
import { ShieldAlert, X } from 'lucide-react';

import { useNotifications } from './NotificationCenter';

/**
 * Thông báo trong ứng dụng. Luôn hoạt động kể cả khi người dùng chưa cấp quyền
 * thông báo hệ thống, nên đây là lớp bảo đảm cuối cùng để cảnh báo quan trọng
 * không lọt qua mắt Quản lý khi đang mở app.
 */
export function ToastStack() {
  const { toasts, dismiss, basePath } = useNotifications();
  const navigate = useNavigate();

  if (!toasts.length) return null;

  return (
    <div
      role="region"
      aria-label="Thông báo quan trọng"
      aria-live="assertive"
      className="pointer-events-none fixed inset-x-0 top-3 z-[60] flex flex-col items-center gap-2 px-3"
    >
      {toasts.map((toast) => (
        <div
          key={toast.key}
          className="pointer-events-auto flex w-full max-w-md items-start gap-3 rounded-xl border border-red-500/50 bg-red-950/95 p-3 shadow-2xl backdrop-blur"
        >
          <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-red-400" aria-hidden />

          <button
            onClick={() => {
              navigate(`${basePath}/incidents/${toast.event.id}`);
              dismiss(toast.key);
            }}
            className="min-w-0 flex-1 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
          >
            <p className="text-xs font-bold text-red-200">{toast.headline}</p>
            <p className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-red-100/80">
              {toast.event.description}
            </p>
            <p className="mt-1 text-[10px] font-semibold text-red-300">Chạm để xử lý →</p>
          </button>

          <button
            onClick={() => dismiss(toast.key)}
            aria-label="Đóng thông báo"
            className="shrink-0 rounded-md p-1 text-red-300/70 transition-colors hover:bg-red-900/60 hover:text-red-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
      ))}
    </div>
  );
}
