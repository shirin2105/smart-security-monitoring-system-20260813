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
    // `revision` đổi khi có action/alert mới → danh sách tự làm mới.
    [JSON.stringify(query), revision],
  );

  const patchQuery = useCallback((patch: Partial<IncidentQuery>) => {
    setQuery((previous) => ({ ...previous, ...patch }));
  }, []);

  const resetQuery = useCallback(() => setQuery(EMPTY_QUERY), []);

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-4 md:p-6">
      <header className="flex items-center gap-2">
        <ListFilter className="h-5 w-5 text-blue-400" aria-hidden />
        <h1 className="text-base font-bold tracking-wide text-white">NHẬT KÝ SỰ CỐ</h1>
      </header>

      <IncidentFilters
        query={query}
        cameras={cameras.data ?? []}
        onChange={patchQuery}
        onReset={resetQuery}
      />

      <section className="flex min-h-[20rem] flex-1 flex-col rounded-2xl border border-gray-800 bg-gray-900/60 p-4">
        {page.loading && !page.data ? (
          <LoadingState label="Đang tải danh sách sự cố…" />
        ) : page.error != null ? (
          <ErrorState error={page.error} onRetry={page.reload} />
        ) : !page.data || page.data.items.length === 0 ? (
          <EmptyState
            icon={<SearchX className="h-10 w-10" />}
            title="Không có sự cố nào khớp bộ lọc"
            hint="Thử mở rộng khoảng thời gian hoặc xóa bớt điều kiện lọc."
          />
        ) : (
          <>
            <div className="min-h-0 flex-1 overflow-x-auto">
              <table className="w-full min-w-[52rem] border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-gray-800 font-mono text-[10px] uppercase text-gray-400">
                    <th scope="col" className="px-3 py-2">
                      Thời điểm
                    </th>
                    <th scope="col" className="px-3 py-2">
                      Camera
                    </th>
                    <th scope="col" className="px-3 py-2">
                      Loại
                    </th>
                    <th scope="col" className="px-3 py-2">
                      Mức độ
                    </th>
                    <th scope="col" className="px-3 py-2">
                      Trạng thái
                    </th>
                    <th scope="col" className="px-3 py-2">
                      Mô tả
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {page.data.items.map((event) => (
                    <tr
                      key={event.id}
                      className="border-b border-gray-800/60 transition-colors hover:bg-gray-800/40"
                    >
                      <td className="whitespace-nowrap px-3 py-2.5 font-mono text-[11px] text-gray-400">
                        {new Date(event.detectedAt).toLocaleString('vi-VN')}
                      </td>
                      <td className="px-3 py-2.5 text-gray-200">{event.cameraName}</td>
                      <td className="px-3 py-2.5">
                        <EventTypeBadge eventType={event.eventType} />
                      </td>
                      <td className="px-3 py-2.5">
                        <SeverityBadge severity={event.effectiveSeverity} />
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex flex-wrap gap-1">
                          <StateBadge state={event.state} />
                          <EscalationBadge escalation={event.escalation} />
                        </div>
                      </td>
                      <td className="max-w-md px-3 py-2.5">
                        <Link
                          to={`/incidents/${event.id}`}
                          className="line-clamp-2 text-gray-300 underline-offset-2 hover:text-blue-300 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
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
