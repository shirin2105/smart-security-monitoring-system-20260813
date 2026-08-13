import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onChange: (page: number) => void;
}

export function Pagination({ page, pageSize, total, onChange }: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);

  const button =
    'flex items-center gap-1 rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-xs text-gray-200 transition-colors hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500';

  return (
    <nav
      aria-label="Phân trang danh sách sự cố"
      className="flex flex-wrap items-center justify-between gap-3 border-t border-gray-800 px-1 pt-3"
    >
      <p aria-live="polite" className="font-mono text-[11px] text-gray-400">
        Hiển thị <span className="text-gray-200">{first}</span>–
        <span className="text-gray-200">{last}</span> trong tổng số{' '}
        <span className="text-gray-200">{total}</span> sự cố
      </p>

      <div className="flex items-center gap-2">
        <button
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
          className={button}
          aria-label="Trang trước"
        >
          <ChevronLeft className="h-3.5 w-3.5" aria-hidden />
          <span>Trước</span>
        </button>

        <span className="font-mono text-[11px] text-gray-400">
          Trang <span className="text-gray-200">{page}</span> / {totalPages}
        </span>

        <button
          onClick={() => onChange(page + 1)}
          disabled={page >= totalPages}
          className={button}
          aria-label="Trang sau"
        >
          <span>Sau</span>
          <ChevronRight className="h-3.5 w-3.5" aria-hidden />
        </button>
      </div>
    </nav>
  );
}
