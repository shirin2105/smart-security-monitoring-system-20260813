import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bell, CheckCircle2, Clock, Filter } from 'lucide-react';

import { SecurityEvent } from '../../domain/types';
import { EvidenceMedia } from '../common/EvidenceMedia';
import { EmptyState, ErrorState, LoadingState } from '../common/States';
import {
  AiGeneratedBadge,
  EscalationBadge,
  EventTypeBadge,
  SeverityBadge,
  StateBadge,
} from '../common/Badges';
import { HitlActionBar } from '../hitl/HitlActionBar';

type FilterKey = 'all' | 'active' | 'closed';

const ACTIVE_STATES = ['OPEN', 'PENDING_REVIEW', 'ACKNOWLEDGED', 'CONFIRMED'];

interface AlertSidebarProps {
  events: SecurityEvent[];
  loading: boolean;
  error: unknown;
  onRetry: () => void;
}

/** Hàng chờ cảnh báo realtime — BAC-51, kèm hành động HITL của BAC-53. */
export function AlertSidebar({ events, loading, error, onRetry }: AlertSidebarProps) {
  const [filter, setFilter] = useState<FilterKey>('all');

  const activeCount = useMemo(
    () => events.filter((event) => ACTIVE_STATES.includes(event.state)).length,
    [events],
  );

  const visible = useMemo(() => {
    if (filter === 'active') {
      return events.filter((event) => ACTIVE_STATES.includes(event.state));
    }
    if (filter === 'closed') {
      return events.filter((event) => !ACTIVE_STATES.includes(event.state));
    }
    return events;
  }, [events, filter]);

  const tabs: Array<{ key: FilterKey; label: string; count: number }> = [
    { key: 'all', label: 'Tất cả', count: events.length },
    { key: 'active', label: 'Đang mở', count: activeCount },
    { key: 'closed', label: 'Đã đóng', count: events.length - activeCount },
  ];

  return (
    <aside
      aria-label="Hàng chờ cảnh báo"
      className="glass-panel flex w-full shrink-0 flex-col overflow-hidden rounded-2xl border border-gray-200 dark:border-gray-800 lg:w-[26rem] shadow-sm max-h-[calc(100vh-8.5rem)] min-h-0"
    >
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-gray-200 dark:border-gray-800 bg-slate-50/90 dark:bg-gray-950/80 p-4">
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <Bell className="h-5 w-5 text-amber-500 dark:text-amber-400" aria-hidden />
            {activeCount > 0 && (
              <span className="absolute -right-1 -top-1 h-2.5 w-2.5 animate-ping rounded-full bg-rose-500" />
            )}
          </div>
          <div>
            <h2 className="text-sm font-bold tracking-wide text-gray-900 dark:text-white">
              CẢNH BÁO THỜI GIAN THỰC
            </h2>
            <p className="text-[11px] text-gray-500 dark:text-gray-400">{events.length} sự cố gần nhất</p>
          </div>
        </div>

        {activeCount > 0 && (
          <span className="rounded-full border border-rose-300 dark:border-red-500/40 bg-rose-50 dark:bg-red-500/20 px-2.5 py-0.5 font-mono text-xs font-bold text-rose-700 dark:text-red-400">
            {activeCount} chờ xử lý
          </span>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-1 border-b border-gray-200 dark:border-gray-800/80 bg-white/70 dark:bg-gray-900/60 p-2 text-xs">
        <Filter className="ml-2 mr-1 h-3.5 w-3.5 text-gray-400 dark:text-gray-500" aria-hidden />
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            aria-pressed={filter === tab.key}
            className={`rounded-lg px-2.5 py-1 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
              filter === tab.key
                ? 'border border-blue-300 dark:border-blue-500/30 bg-blue-50 dark:bg-blue-600/30 font-semibold text-blue-700 dark:text-blue-300'
                : 'border border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
            }`}
          >
            {tab.label} ({tab.count})
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto max-h-[calc(100vh-14.5rem)]">
        {loading && events.length === 0 ? (
          <LoadingState label="Đang tải cảnh báo…" />
        ) : error != null && events.length === 0 ? (
          <ErrorState error={error} onRetry={onRetry} />
        ) : visible.length === 0 ? (
          <EmptyState
            icon={<CheckCircle2 className="h-10 w-10 text-emerald-500/60" />}
            title="Không có cảnh báo nào"
            hint={
              filter === 'all'
                ? 'Hệ thống đang giám sát bình thường.'
                : 'Không có sự cố nào trong bộ lọc này.'
            }
          />
        ) : (
          <ul className="space-y-3 p-3">
            {visible.map((event) => (
              <li key={event.id}>
                <AlertCard event={event} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}

function AlertCard({ event }: { event: SecurityEvent }) {
  const critical = event.effectiveSeverity === 'CRITICAL';
  const active = ACTIVE_STATES.includes(event.state);

  return (
    <article
      className={`rounded-xl border p-3.5 transition-all shadow-sm card-elevation ${
        active
          ? critical
            ? 'border-rose-300 dark:border-red-500/60 bg-rose-50/70 dark:bg-red-950/40'
            : 'border-amber-300 dark:border-amber-500/50 bg-amber-50/70 dark:bg-amber-950/20'
          : 'border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 opacity-90'
      }`}
    >
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        <SeverityBadge severity={event.effectiveSeverity} />
        <StateBadge state={event.state} />
        <EscalationBadge escalation={event.escalation} />
        <span className="ml-auto flex items-center gap-1 font-mono text-[11px] text-gray-500 dark:text-gray-400">
          <Clock className="h-3 w-3 text-gray-400 dark:text-gray-500" aria-hidden />
          {new Date(event.detectedAt).toLocaleTimeString('vi-VN', { hour12: false })}
        </span>
      </div>

      <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
        <EventTypeBadge eventType={event.eventType} />
        <span className="text-xs font-semibold text-gray-900 dark:text-gray-200">{event.cameraName}</span>
      </div>

      {event.artifact?.redactionStatus === 'COMPLETE' && event.artifact.url && (
        <EvidenceMedia
          artifact={event.artifact}
          description={`sự cố #${event.id}`}
          className="mb-2 h-28 w-full rounded-lg border border-gray-200 dark:border-gray-800 object-cover shadow-sm"
          autoPlay
        />
      )}

      {event.artifact && event.artifact.redactionStatus !== 'COMPLETE' && (
        <p className="mb-2 rounded-lg border border-gray-200 dark:border-gray-800 bg-slate-50 dark:bg-gray-950/60 p-2 text-[11px] leading-relaxed text-gray-500">
          Video bằng chứng chưa sẵn sàng — đang xử lý, sẽ hiển thị ngay khi hoàn tất.
        </p>
      )}

      <p className="mb-2 text-xs leading-relaxed text-gray-700 dark:text-gray-300">{event.description}</p>

      {event.aiGenerated && (
        <div className="mb-2">
          <AiGeneratedBadge />
        </div>
      )}

      <div className="border-t border-gray-200 dark:border-gray-800/80 pt-2">
        <HitlActionBar event={event} compact />
      </div>

      <Link
        to={`/incidents/${event.id}`}
        className="mt-2 inline-block text-[11px] font-semibold text-blue-600 dark:text-blue-400 underline-offset-2 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        Xem chi tiết & lịch sử xử lý →
      </Link>
    </article>
  );
}
