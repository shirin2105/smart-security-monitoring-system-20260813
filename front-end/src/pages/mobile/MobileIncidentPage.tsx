import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, ImageOff } from 'lucide-react';

import { api } from '../../api';
import {
  AiGeneratedBadge,
  EscalationBadge,
  EventTypeBadge,
  SeverityBadge,
  StateBadge,
} from '../../components/common/Badges';
import { EmptyState, ErrorState, LoadingState } from '../../components/common/States';
import { HitlActionBar } from '../../components/hitl/HitlActionBar';
import { useAsync } from '../../hooks/useAsync';
import { useEvents } from '../../realtime/EventsProvider';

/**
 * Chi tiết sự cố trên điện thoại — nơi Quản lý thực sự ra quyết định.
 *
 * Thanh hành động dính đáy màn hình để không phải cuộn tìm nút, và dùng vùng
 * chạm ≥44px theo khuyến nghị của cả iOS lẫn Android.
 */
export function MobileIncidentPage() {
  const { id } = useParams<{ id: string }>();
  const eventId = Number(id);
  const { revision } = useEvents();

  const detail = useAsync(() => api.getEvent(eventId), [eventId, revision]);

  if (Number.isNaN(eventId)) return <EmptyState title="Mã sự cố không hợp lệ" />;
  if (detail.loading && !detail.data) return <LoadingState label="Đang tải sự cố…" />;
  if (detail.error != null) {
    return <ErrorState error={detail.error} onRetry={detail.reload} />;
  }
  if (!detail.data) return <EmptyState title="Không tìm thấy sự cố" />;

  const event = detail.data;
  const artifactUsable =
    event.artifact?.redactionStatus === 'COMPLETE' && Boolean(event.artifact.url);

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex flex-1 flex-col gap-4 p-4">
        <Link
          to="/m"
          className="inline-flex items-center gap-1.5 text-xs text-gray-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          <span>Danh sách thông báo</span>
        </Link>

        <div className="flex flex-wrap items-center gap-1.5">
          <SeverityBadge severity={event.effectiveSeverity} />
          <StateBadge state={event.state} />
          <EscalationBadge escalation={event.escalation} />
          <EventTypeBadge eventType={event.eventType} />
        </div>

        <div>
          <h1 className="text-sm font-bold text-white">
            Sự cố #{event.id} · {event.cameraName}
          </h1>
          <p className="mt-0.5 font-mono text-[11px] text-gray-400">
            {new Date(event.detectedAt).toLocaleString('vi-VN')}
          </p>
        </div>

        {artifactUsable ? (
          <img
            src={event.artifact!.url}
            alt={`Ảnh bằng chứng đã che mặt của sự cố #${event.id}`}
            className="w-full rounded-xl border border-gray-800 object-cover"
          />
        ) : (
          <div className="rounded-xl border border-gray-800 bg-gray-950/60 py-4">
            <EmptyState
              icon={<ImageOff className="h-7 w-7" />}
              title="Ảnh bằng chứng không khả dụng"
              hint="Ảnh chỉ hiển thị sau khi che mặt thành công."
            />
          </div>
        )}

        <div>
          <div className="mb-1.5 flex items-center gap-2">
            <h2 className="font-mono text-[11px] font-semibold uppercase text-gray-400">
              Mô tả
            </h2>
            {event.aiGenerated && <AiGeneratedBadge />}
          </div>
          <p className="text-sm leading-relaxed text-gray-200">{event.description}</p>
        </div>

        <section>
          <h2 className="mb-2 font-mono text-[11px] font-semibold uppercase text-gray-400">
            Lịch sử xử lý ({event.actions.length})
          </h2>

          {event.actions.length === 0 ? (
            <p className="rounded-lg border border-gray-800 bg-gray-900/60 p-3 text-[11px] text-gray-500">
              Chưa có ai thao tác trên sự cố này.
            </p>
          ) : (
            <ol className="space-y-2">
              {[...event.actions]
                .sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime())
                .map((action) => (
                  <li
                    key={action.id}
                    className="rounded-lg border border-gray-800 bg-gray-900/60 p-2.5"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-[11px] font-semibold text-blue-400">
                        {action.actorName}
                      </span>
                      <span className="shrink-0 font-mono text-[10px] text-gray-500">
                        {new Date(action.at).toLocaleString('vi-VN')}
                      </span>
                    </div>
                    <p className="mt-0.5 text-[11px] text-gray-200">{action.action}</p>
                    {action.reason && (
                      <p className="mt-1 border-l-2 border-gray-700 pl-2 text-[10px] italic leading-relaxed text-gray-400">
                        {action.reason}
                      </p>
                    )}
                  </li>
                ))}
            </ol>
          )}
        </section>
      </div>

      {/* Dính trên thanh điều hướng dưới để luôn trong tầm ngón cái. */}
      <div className="sticky bottom-20 z-30 border-t border-gray-800 bg-gray-950/95 p-3 backdrop-blur">
        <HitlActionBar event={event} touch />
      </div>
    </div>
  );
}
