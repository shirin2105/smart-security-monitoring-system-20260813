import { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';
import { ListFilter, SearchX } from 'lucide-react';

import { api } from '../api';
import { EMPTY_QUERY, IncidentQuery } from '../api/types';
import {
  EscalationBadge,
  EventTypeBadge,
  SeverityBadge,
  StateBadge,
} from '../components/common/Badges';
import { EmptyState, ErrorState, LoadingState } from '../components/common/States';
import { IncidentFilters } from '../components/incidents/IncidentFilters';
import { Pagination } from '../components/incidents/Pagination';
import { useAsync } from '../hooks/useAsync';
import { useEvents } from '../realtime/EventsProvider';

/** Nhật ký sự cố có lọc, phân trang và mở chi tiết — BAC-54. */
export function IncidentsPage() {
  const [query, setQuery] = useState<IncidentQuery>(EMPTY_QUERY);
  const { revision } = useEvents();

  const cameras = useAsync(() => api.getCameras(), []);

  const page = useAsync(
    () => api.getEvents(query),
    [JSON.stringify(query), revision],
  );

  const patchQuery = useCallback((patch: Partial<IncidentQuery>) => {
    setQuery((previous) => ({ ...previous, ...patch }));
  }, []);

  const resetQuery = useCallback(() => setQuery(EMPTY_QUERY), []);

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto">
      <header className="flex items-center gap-2.5">
        <div className="rounded-xl border border-blue-500/40 bg-blue-600/10 dark:bg-blue-600/20 p-2 text-blue-600 dark:text-blue-400 shadow-sm">
          <ListFilter className="h-5 w-5" aria-hidden />
        </div>
        <h1 className="text-base font-extrabold tracking-wide text-gray-900 dark:text-white">
          NHẬT KÝ SỰ CỐ
        </h1>
      </header>

      <IncidentFilters
        query={query}
        cameras={cameras.data ?? []}
        onChange={patchQuery}
        onReset={resetQuery}
      />

      <section className="flex min-h-[20rem] flex-1 flex-col rounded-2xl border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 p-4 shadow-sm">
        {page.loading && !page.data ? (
          <LoadingState label="Đang tải danh sách sự cố…" />
        ) : page.error != null ? (
          <ErrorState error={page.error} onRetry={page.reload} />
        ) : !page.data || page.data.items.length === 0 ? (
          <EmptyState
            icon={<SearchX className="h-10 w-10 text-gray-400" />}
            title="Không có sự cố nào khớp bộ lọc"
            hint="Thử mở rộng khoảng thời gian hoặc xóa bớt điều kiện lọc."
          />
        ) : (
          <>
            <div className="min-h-0 flex-1 overflow-x-auto">
              <table className="w-full min-w-[52rem] border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-800 font-mono text-[10px] font-bold uppercase text-gray-500 dark:text-gray-400">
                    <th scope="col" className="px-3.5 py-3">
                      Thời điểm
                    </th>
                    <th scope="col" className="px-3.5 py-3">
                      Camera
                    </th>
                    <th scope="col" className="px-3.5 py-3">
                      Loại
                    </th>
                    <th scope="col" className="px-3.5 py-3">
                      Mức độ
                    </th>
                    <th scope="col" className="px-3.5 py-3">
                      Trạng thái
                    </th>
                    <th scope="col" className="px-3.5 py-3">
                      Mô tả
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-800/60">
                  {page.data.items.map((event) => (
                    <tr
                      key={event.id}
                      className="transition-colors hover:bg-slate-50 dark:hover:bg-gray-800/40"
                    >
                      <td className="whitespace-nowrap px-3.5 py-3 font-mono text-[11px] font-medium text-gray-500 dark:text-gray-400">
                        {new Date(event.detectedAt).toLocaleString('vi-VN')}
                      </td>
                      <td className="px-3.5 py-3 font-semibold text-gray-900 dark:text-gray-200">{event.cameraName}</td>
                      <td className="px-3.5 py-3">
                        <EventTypeBadge eventType={event.eventType} />
                      </td>
                      <td className="px-3.5 py-3">
                        <SeverityBadge severity={event.effectiveSeverity} />
                      </td>
                      <td className="px-3.5 py-3">
                        <div className="flex flex-wrap gap-1">
                          <StateBadge state={event.state} />
                          <EscalationBadge escalation={event.escalation} />
                        </div>
                      </td>
                      <td className="max-w-md px-3.5 py-3">
                        <Link
                          to={`/incidents/${event.id}`}
                          className="line-clamp-2 font-medium text-gray-700 dark:text-gray-300 underline-offset-2 hover:text-blue-600 dark:hover:text-blue-300 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                        >
                          {event.description}
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <Pagination
              page={page.data.page}
              pageSize={page.data.pageSize}
              total={page.data.total}
              onChange={(next) => patchQuery({ page: next })}
            />
          </>
        )}
      </section>
    </div>
  );
}
