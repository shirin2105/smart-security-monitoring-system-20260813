/**
 * Empty / loading / error state dùng chung — BAC-56 yêu cầu "tất cả màn hình có
 * empty/loading/error state". Gom về một nơi để trình bày nhất quán.
 */

import { ReactNode } from 'react';
import {
  AlertTriangle,
  Inbox,
  Loader2,
  RefreshCw,
  ShieldOff,
  WifiOff,
} from 'lucide-react';

import { ApiError } from '../../api/errors';

export function LoadingState({ label = 'Đang tải dữ liệu…' }: { label?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex flex-1 flex-col items-center justify-center gap-3 p-10 text-slate-500 dark:text-gray-400"
    >
      <Loader2 className="h-6 w-6 animate-spin text-blue-600 dark:text-blue-400" />
      <p className="text-xs font-medium">{label}</p>
    </div>
  );
}

export function EmptyState({
  title,
  hint,
  icon,
}: {
  title: string;
  hint?: string;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2 p-10 text-center">
      <div className="mb-1 text-slate-400 dark:text-gray-600">
        {icon ?? <Inbox className="h-10 w-10" />}
      </div>
      <p className="text-sm font-semibold text-slate-800 dark:text-gray-300">{title}</p>
      {hint && <p className="max-w-sm text-xs leading-relaxed text-slate-500 dark:text-gray-400">{hint}</p>}
    </div>
  );
}

/** Icon + tiêu đề theo từng loại lỗi, để người dùng biết nên làm gì tiếp. */
function describe(error: unknown): { icon: ReactNode; title: string; message: string } {
  if (error instanceof ApiError) {
    switch (error.kind) {
      case 'NETWORK':
        return {
          icon: <WifiOff className="h-10 w-10 text-amber-500 dark:text-amber-400" />,
          title: 'Không kết nối được máy chủ',
          message: error.message,
        };
      case 'FORBIDDEN':
        return {
          icon: <ShieldOff className="h-10 w-10 text-amber-500 dark:text-amber-400" />,
          title: 'Không đủ quyền',
          message: error.message,
        };
      case 'NOT_IMPLEMENTED':
        return {
          icon: <AlertTriangle className="h-10 w-10 text-blue-500 dark:text-blue-400" />,
          title: 'Tính năng chưa sẵn sàng ở backend',
          message: error.message,
        };
      default:
        return {
          icon: <AlertTriangle className="h-10 w-10 text-rose-500 dark:text-red-400" />,
          title: 'Đã xảy ra lỗi',
          message: error.message,
        };
    }
  }
  return {
    icon: <AlertTriangle className="h-10 w-10 text-rose-500 dark:text-red-400" />,
    title: 'Đã xảy ra lỗi',
    message: 'Lỗi không xác định. Vui lòng thử lại.',
  };
}

export function ErrorState({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  const { icon, title, message } = describe(error);

  return (
    <div
      role="alert"
      className="flex flex-1 flex-col items-center justify-center gap-3 p-10 text-center"
    >
      {icon}
      <p className="text-sm font-semibold text-slate-800 dark:text-gray-200">{title}</p>
      <p className="max-w-md text-xs leading-relaxed text-slate-600 dark:text-gray-400">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 flex items-center gap-1.5 rounded-lg border border-slate-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3.5 py-2 text-xs font-semibold text-slate-700 dark:text-gray-200 transition-colors hover:bg-slate-50 dark:hover:bg-gray-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 shadow-sm"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Thử lại</span>
        </button>
      )}
    </div>
  );
}

/** Banner lỗi gọn cho thao tác trong form/panel, không chiếm cả màn hình. */
export function InlineError({ error }: { error: unknown }) {
  const { message } = describe(error);
  return (
    <div
      role="alert"
      className="flex items-start gap-2 rounded-lg border border-rose-200 dark:border-red-500/30 bg-rose-50 dark:bg-red-500/10 p-3 text-xs text-rose-800 dark:text-red-300"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-500 dark:text-red-400" />
      <span className="leading-relaxed">{message}</span>
    </div>
  );
}
