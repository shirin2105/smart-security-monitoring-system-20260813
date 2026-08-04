import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bell, CheckCircle2, Clock, Filter } from 'lucide-react';

import { SecurityEvent } from '../../domain/types';
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
      className="glass-panel flex w-full shrink-0 flex-col overflow-hidden rounded-2xl border border-gray-800 lg:min-h-0 lg:w-[26rem]"
    >
      <div className="flex items-center justify-between gap-2 border-b border-gray-800 bg-gray-950/80 p-4">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Bell className="h-5 w-5 text-amber-400" aria-hidden />
            {activeCount > 0 && (
              <span className="absolute -right-1 -top-1 h-2.5 w-2.5 animate-ping rounded-full bg-red-500" />
            )}
          </div>
          <div>
            <h2 className="text-sm font-bold tracking-wide text-white">
              CẢNH BÁO THỜI GIAN THỰC
            </h2>
            <p className="text-[11px] text-gray-400">{events.length} sự cố gần nhất</p>
          </div>
        </div>

        {activeCount > 0 && (
          <span className="rounded-full border border-red-500/40 bg-red-500/20 px-2 py-0.5 font-mono text-xs font-bold text-red-400">
            {activeCount} chờ xử lý
          </span>
        )}
      </div>

      <div className="flex items-center gap-1 border-b border-gray-800/80 bg-gray-900/60 p-2 text-xs">
        <Filter className="ml-2 mr-1 h-3.5 w-3.5 text-gray-500" aria-hidden />
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            aria-pressed={filter === tab.key}
            className={`rounded-md px-2.5 py-1 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
              filter === tab.key
                ? 'border border-blue-500/30 bg-blue-600/30 font-semibold text-blue-300'
                : 'border border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab.label} ({tab.count})
          </button>
        ))}
      </div>

      {/*
        Dưới lg sidebar không bị khóa chiều cao, nên giới hạn danh sách để nó
        không kéo dài vô tận; từ lg trở lên thì để flex quyết định.
      */}
      <div className="max-h-[32rem] min-h-0 flex-1 overflow-y-auto lg:max-h-none">
        {loading && events.length === 0 ? (
          <LoadingState label="Đang tải cảnh báo…" />
        ) : error != null && events.length === 0 ? (
          <ErrorState error={error} onRetry={onRetry} />
        ) : visible.length === 0 ? (
          <EmptyState
            icon={<CheckCircle2 className="h-10 w-10 text-emerald-500/50" />}
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
      className={`rounded-xl border p-3.5 transition-all ${
        active
          ? critical
            ? 'border-red-500/60 bg-red-950/40'
            : 'border-amber-500/50 bg-amber-950/20'
          : 'border-gray-800 bg-gray-900/60 opacity-80'
      }`}
    >
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        <SeverityBadge severity={event.effectiveSeverity} />
        <StateBadge state={event.state} />
        <EscalationBadge escalation={event.escalation} />
        <span className="ml-auto flex items-center gap-1 font-mono text-[11px] text-gray-400">
          <Clock className="h-3 w-3 text-gray-500" aria-hidden />
          {new Date(event.detectedAt).toLocaleTimeString('vi-VN', { hour12: false })}
        </span>
      </div>

      <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
        <EventTypeBadge eventType={event.eventType} />
        <span className="text-xs font-semibold text-gray-200">{event.cameraName}</span>
      </div>

      {event.artifact?.redactionStatus === 'COMPLETE' && event.artifact.url && (
        <img
          src={event.artifact.url}
          alt={`Ảnh bằng chứng sự cố #${event.id}`}
          className="mb-2 h-28 w-full rounded-lg border border-gray-800 object-cover"
        />
      )}

      {event.artifact && event.artifact.redactionStatus !== 'COMPLETE' && (
        <p className="mb-2 rounded-lg border border-gray-800 bg-gray-950/60 p-2 text-[11px] leading-relaxed text-gray-500">
          Ảnh bằng chứng không khả dụng — chưa che mặt xong nên hệ thống không hiển thị.
        </p>
      )}

      <p className="mb-2 text-xs leading-relaxed text-gray-300">{event.description}</p>

      {event.aiGenerated && (
        <div className="mb-2">
          <AiGeneratedBadge />
        </div>
      )}

      <div className="border-t border-gray-800/80 pt-2">
        <HitlActionBar event={event} compact />
      </div>

      <Link
        to={`/incidents/${event.id}`}
        className="mt-2 inline-block text-[11px] text-blue-400 underline-offset-2 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        Xem chi tiết & lịch sử xử lý →
      </Link>
    </article>
  );
}
