import { Link } from 'react-router-dom';
import { ChevronRight, ShieldCheck } from 'lucide-react';

import {
  EscalationBadge,
  EventTypeBadge,
  SeverityBadge,
  StateBadge,
} from '../../components/common/Badges';
import { EmptyState, ErrorState, LoadingState } from '../../components/common/States';
import { needsManagerDecision, selectManagerAlerts } from '../../domain/notifications';
import { SecurityEvent } from '../../domain/types';
import { PermissionBanner } from '../../notifications/PermissionBanner';
import { useEvents } from '../../realtime/EventsProvider';

/** "Nhận thông báo quan trọng" — hộp thư của Quản lý an ninh trên điện thoại. */
export function ManagerInboxPage() {
  const { events, loading, error, reload } = useEvents();

  const alerts = selectManagerAlerts(events);
  const decisionCount = alerts.filter(needsManagerDecision).length;

  return (
    <div className="flex flex-1 flex-col gap-3 p-4">
      <PermissionBanner />

      <header>
        <h1 className="text-base font-bold text-white">Thông báo quan trọng</h1>
        <p className="mt-0.5 text-xs text-gray-400" aria-live="polite">
          {decisionCount > 0 ? (
            <>
              <span className="font-semibold text-red-400">{decisionCount} việc</span> đang
              chờ bạn quyết định
            </>
          ) : (
            'Không có việc nào đang chờ bạn quyết định'
          )}
        </p>
      </header>

      {loading && events.length === 0 ? (
        <LoadingState label="Đang tải thông báo…" />
      ) : error != null && events.length === 0 ? (
        <ErrorState error={error} onRetry={reload} />
      ) : alerts.length === 0 ? (
        <EmptyState
          icon={<ShieldCheck className="h-10 w-10 text-emerald-500/50" />}
          title="Chưa có cảnh báo nào cần bạn duyệt"
          hint="Chỉ sự cố mức nghiêm trọng và yêu cầu xin ý kiến từ Bảo vệ mới hiện ở đây."
        />
      ) : (
        <ul aria-label="Danh sách thông báo" className="flex flex-col gap-2.5">
          {alerts.map((event) => (
            <li key={event.id}>
              <AlertRow event={event} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function AlertRow({ event }: { event: SecurityEvent }) {
  const urgent = needsManagerDecision(event);

  return (
    <Link
      to={`/m/incidents/${event.id}`}
      className={`flex items-stretch gap-3 rounded-xl border p-3 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
        urgent
          ? 'border-red-500/50 bg-red-950/30'
          : 'border-gray-800 bg-gray-900/60'
      }`}
    >
      {event.artifact?.redactionStatus === 'COMPLETE' && event.artifact.url && (
        <img
          src={event.artifact.url}
          alt=""
          className="h-16 w-16 shrink-0 rounded-lg border border-gray-800 object-cover"
        />
      )}

      <div className="min-w-0 flex-1">
        <div className="mb-1 flex flex-wrap items-center gap-1">
          <SeverityBadge severity={event.effectiveSeverity} />
          <EscalationBadge escalation={event.escalation} />
          {!urgent && <StateBadge state={event.state} />}
        </div>

        <p className="truncate text-xs font-semibold text-gray-100">{event.cameraName}</p>
        <p className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-gray-400">
          {event.description}
        </p>

        <div className="mt-1 flex items-center gap-2">
          <EventTypeBadge eventType={event.eventType} />
          <span className="font-mono text-[10px] text-gray-500">
            {new Date(event.detectedAt).toLocaleTimeString('vi-VN', { hour12: false })}
          </span>
        </div>
      </div>

      <ChevronRight className="my-auto h-4 w-4 shrink-0 text-gray-600" aria-hidden />
    </Link>
  );
}
