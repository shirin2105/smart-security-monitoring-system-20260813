import { Link } from 'react-router-dom';
import { Compass } from 'lucide-react';

export function NotFoundPage() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-10 text-center">
      <Compass className="h-10 w-10 text-gray-600" aria-hidden />
      <h1 className="text-base font-bold text-white">Không tìm thấy trang</h1>
      <p className="max-w-sm text-xs leading-relaxed text-gray-400">
        Đường dẫn bạn truy cập không tồn tại hoặc đã được đổi.
      </p>
      <Link
        to="/"
        className="mt-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-blue-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
      >
        Về màn hình giám sát
      </Link>
    </div>
  );
}
