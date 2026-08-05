import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ScrollText, Search } from 'lucide-react';

import { api } from '../../api';
import { EmptyState, ErrorState, LoadingState } from '../../components/common/States';
import { useAsync } from '../../hooks/useAsync';
import { useEvents } from '../../realtime/EventsProvider';

/**
 * "Audit" trên điện thoại — nhật ký thao tác chỉ ghi thêm.
 *
 * Trên màn hẹp không dùng bảng được, nên trình bày dạng dòng thời gian và ưu
 * tiên ba thông tin Quản lý cần khi truy vết: ai làm, làm gì, lý do gì.
 */
export function MobileAuditPage() {
  const { revision } = useEvents();
  const [keyword, setKeyword] = useState('');

  const logs = useAsync(() => api.getAuditLog(), [revision]);

  const needle = keyword.trim().toLowerCase();
  const visible = (logs.data ?? []).filter((log) => {
    if (!needle) return true;
    return `${log.actorName} ${log.action} ${log.reason ?? ''} ${log.incidentId ?? ''}`
      .toLowerCase()
      .includes(needle);
  });

  return (
    <div className="flex flex-1 flex-col gap-3 p-4">
      <header>
        <h1 className="text-base font-bold text-white">Nhật ký thao tác</h1>
        <p className="mt-0.5 text-[11px] leading-relaxed text-gray-400">
          Chỉ ghi thêm, không sửa hay xóa được. Mọi quyết định của người trực đều lưu lại.
        </p>
      </header>

      <div className="relative">
        <Search
          className="pointer-events-none absolute inset-y-0 left-3 my-auto h-4 w-4 text-gray-500"
          aria-hidden
        />
        <input
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          aria-label="Tìm trong nhật ký"
          placeholder="Tìm theo người, thao tác hoặc mã sự cố…"
          className="w-full rounded-lg border border-gray-800 bg-gray-950 py-2.5 pl-9 pr-3 text-xs text-gray-200 placeholder-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {logs.loading && !logs.data ? (
        <LoadingState label="Đang tải nhật ký…" />
      ) : logs.error != null ? (
        <ErrorState error={logs.error} onRetry={logs.reload} />
      ) : visible.length === 0 ? (
        <EmptyState
          icon={<ScrollText className="h-10 w-10" />}
          title={needle ? 'Không có bản ghi nào khớp' : 'Chưa có thao tác nào'}
          hint={
            needle
              ? 'Thử từ khóa khác hoặc xóa ô tìm kiếm.'
              : 'Nhật ký sẽ xuất hiện ngay khi có người xử lý một sự cố.'
          }
        />
      ) : (
        <ol className="relative space-y-3 border-l border-gray-800 pl-4">
          {visible.map((log) => (
            <li key={log.id} className="relative">
              <span
                className="absolute -left-[22px] top-2 h-2.5 w-2.5 rounded-full border-2 border-gray-950 bg-blue-500"
                aria-hidden
              />
              <div className="rounded-lg border border-gray-800 bg-gray-900/60 p-3">
                <div className="flex items-start justify-between gap-2">
                  <span className="min-w-0 truncate text-[11px] font-semibold text-blue-400">
                    {log.actorName}
                  </span>
                  <span className="shrink-0 font-mono text-[10px] text-gray-500">
                    {new Date(log.at).toLocaleString('vi-VN')}
                  </span>
                </div>

                <p className="mt-1 text-[11px] leading-relaxed text-gray-200">
                  {log.action}
                </p>

                {log.reason && (
                  <p className="mt-1.5 border-l-2 border-gray-700 pl-2 text-[10px] italic leading-relaxed text-gray-400">
                    Lý do: {log.reason}
                  </p>
                )}

                {log.incidentId != null && (
                  <Link
                    to={`/m/incidents/${log.incidentId}`}
                    className="mt-2 inline-block font-mono text-[10px] text-blue-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  >
                    Sự cố #{log.incidentId} →
                  </Link>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
