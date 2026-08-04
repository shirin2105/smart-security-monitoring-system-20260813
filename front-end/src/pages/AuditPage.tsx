import { Link } from 'react-router-dom';
import { History, ScrollText } from 'lucide-react';

import { api } from '../api';
import { EmptyState, ErrorState, LoadingState } from '../components/common/States';
import { useAsync } from '../hooks/useAsync';
import { useEvents } from '../realtime/EventsProvider';

/** Nhật ký thao tác — append-only, không có chức năng sửa/xóa theo thiết kế. */
export function AuditPage() {
  const { revision } = useEvents();
  const logs = useAsync(() => api.getAuditLog(), [revision]);

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6">
      <header className="mb-4 flex items-center gap-2">
        <History className="h-5 w-5 text-blue-400" aria-hidden />
        <div>
          <h1 className="text-base font-bold tracking-wide text-white">
            NHẬT KÝ THAO TÁC (AUDIT TRAIL)
          </h1>
          <p className="text-[11px] text-gray-400">
            Chỉ ghi thêm, không thể sửa hoặc xóa — mọi quyết định của người trực đều lưu
            vĩnh viễn.
          </p>
        </div>
      </header>

      <section className="min-h-[20rem] rounded-2xl border border-gray-800 bg-gray-900/60 p-5">
        {logs.loading && !logs.data ? (
          <LoadingState label="Đang tải nhật ký…" />
        ) : logs.error != null ? (
          <ErrorState error={logs.error} onRetry={logs.reload} />
        ) : !logs.data || logs.data.length === 0 ? (
          <EmptyState
            icon={<ScrollText className="h-10 w-10" />}
            title="Chưa có thao tác nào được ghi nhận"
            hint="Nhật ký sẽ xuất hiện ngay khi có người tiếp nhận hoặc xử lý một sự cố."
          />
        ) : (
          <ol className="relative space-y-4 border-l border-gray-800 pl-6">
            {logs.data.map((log) => (
              <li key={log.id} className="relative">
                <span
                  className="absolute -left-[31px] top-1.5 h-3 w-3 rounded-full border-2 border-gray-900 bg-blue-500"
                  aria-hidden
                />
                <div className="rounded-xl border border-gray-800/80 bg-gray-950/70 p-4">
                  <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-blue-400">
                      {log.actorName}
                    </span>
                    <span className="font-mono text-[11px] text-gray-400">
                      {new Date(log.at).toLocaleString('vi-VN')}
                    </span>
                  </div>

                  <p className="text-xs font-medium text-gray-200">{log.action}</p>

                  {log.reason && (
                    <p className="mt-1.5 border-l-2 border-gray-700 pl-2 text-[11px] italic leading-relaxed text-gray-400">
                      Lý do: {log.reason}
                    </p>
                  )}

                  {log.incidentId != null && (
                    <Link
                      to={`/incidents/${log.incidentId}`}
                      className="mt-2 inline-block font-mono text-[11px] text-blue-400 underline-offset-2 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                    >
                      Sự cố #{log.incidentId} →
                    </Link>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
