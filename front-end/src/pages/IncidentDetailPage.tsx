import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, ImageOff, ShieldQuestion } from 'lucide-react';

import { api } from '../api';
import {
  AiGeneratedBadge,
  EscalationBadge,
  EventTypeBadge,
  SeverityBadge,
  StateBadge,
} from '../components/common/Badges';
import { EmptyState, ErrorState, LoadingState } from '../components/common/States';
import { HitlActionBar } from '../components/hitl/HitlActionBar';
import { SEVERITY_LABEL } from '../domain/types';
import { useAsync } from '../hooks/useAsync';
import { useEvents } from '../realtime/EventsProvider';

export function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const eventId = Number(id);
  const { revision } = useEvents();

  const detail = useAsync(() => api.getEvent(eventId), [eventId, revision]);

  if (Number.isNaN(eventId)) {
    return <EmptyState title="Mã sự cố không hợp lệ" />;
  }

  if (detail.loading && !detail.data) return <LoadingState label="Đang tải sự cố…" />;
  if (detail.error != null) {
    return <ErrorState error={detail.error} onRetry={detail.reload} />;
  }
  if (!detail.data) return <EmptyState title="Không tìm thấy sự cố" />;

  const event = detail.data;
  const artifactUsable =
    event.artifact?.redactionStatus === 'COMPLETE' && Boolean(event.artifact.url);

  return (
    <div className="flex-1 overflow-y-auto">
      <Link
        to="/incidents"
        className="mb-4 inline-flex items-center gap-1.5 text-xs font-semibold text-gray-500 dark:text-gray-400 transition-colors hover:text-blue-600 dark:hover:text-blue-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
        <span>Quay lại nhật ký sự cố</span>
      </Link>

      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        {/* Bằng chứng + mô tả */}
        <section className="space-y-4 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 p-6 shadow-sm">
          <header className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <SeverityBadge severity={event.effectiveSeverity} />
              <StateBadge state={event.state} />
              <EscalationBadge escalation={event.escalation} />
              <EventTypeBadge eventType={event.eventType} />
            </div>
            <h1 className="text-lg font-extrabold text-gray-900 dark:text-white">
              Sự cố #{event.id} · {event.cameraName}
            </h1>
            <p className="font-mono text-[11px] font-medium text-gray-500 dark:text-gray-400">
              Phát hiện lúc {new Date(event.detectedAt).toLocaleString('vi-VN')} · phiên
              bản {event.version}
            </p>
          </header>

          {artifactUsable ? (
            <div className="relative flex aspect-video max-h-[500px] w-full items-center justify-center overflow-hidden rounded-xl border border-gray-200 dark:border-gray-800 bg-slate-950 shadow-sm">
              <img
                src={event.artifact!.url}
                alt={`Ảnh bằng chứng đã che mặt của sự cố #${event.id}`}
                className="h-full w-full object-cover"
              />
            </div>
          ) : (
            <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-slate-50 dark:bg-gray-950/60 p-6">
              <EmptyState
                icon={<ImageOff className="h-8 w-8 text-gray-400" />}
                title="Ảnh bằng chứng không khả dụng"
                hint="Hệ thống chỉ hiển thị ảnh sau khi che mặt thành công. Nếu che mặt lỗi, ảnh bị loại bỏ và chỉ giữ lại dữ liệu mô tả."
              />
            </div>
          )}

          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <h2 className="font-mono text-xs font-bold uppercase text-gray-700 dark:text-gray-400">
                Mô tả sự cố
              </h2>
              {event.aiGenerated && <AiGeneratedBadge />}
            </div>
            <p className="text-sm leading-relaxed text-gray-800 dark:text-gray-200 font-medium">{event.description}</p>
            {event.aiGenerated && (
              <p className="text-[11px] leading-relaxed text-gray-500">
                Nội dung do AI tổng hợp từ dữ liệu phát hiện, chỉ mang tính hỗ trợ. Quyết
                định xử lý thuộc về người trực.
              </p>
            )}
          </div>

          {event.recommendedSeverity &&
            event.recommendedSeverity !== event.effectiveSeverity && (
              <p className="flex items-start gap-2 rounded-xl border border-violet-200 dark:border-gray-800 bg-violet-50/60 dark:bg-gray-950/60 p-3.5 text-[11px] leading-relaxed text-violet-900 dark:text-gray-400">
                <ShieldQuestion className="mt-0.5 h-4 w-4 shrink-0 text-violet-600 dark:text-violet-400" aria-hidden />
                <span>
                  AI đề xuất mức{' '}
                  <strong className="text-violet-700 dark:text-violet-300">
                    {SEVERITY_LABEL[event.recommendedSeverity]}
                  </strong>
                  , nhưng mức áp dụng theo chính sách là{' '}
                  <strong className="text-gray-900 dark:text-gray-200">
                    {SEVERITY_LABEL[event.effectiveSeverity]}
                  </strong>
                  . Mức áp dụng luôn do chính sách quyết định, không phải AI.
                </span>
              </p>
            )}
        </section>

        {/* Hành động + lịch sử */}
        <div className="space-y-5">
          <section className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 p-6 shadow-sm">
            <h2 className="mb-3 font-mono text-xs font-bold uppercase text-gray-700 dark:text-gray-400">
              Hành động của bạn
            </h2>
            <HitlActionBar event={event} />
          </section>

          <section className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 p-6 shadow-sm">
            <h2 className="mb-3 font-mono text-xs font-bold uppercase text-gray-700 dark:text-gray-400">
              Lịch sử xử lý ({event.actions.length})
            </h2>

            {event.actions.length === 0 ? (
              <EmptyState
                title="Chưa có thao tác nào"
                hint="Mọi thao tác xác nhận, bỏ qua hay phê duyệt đều được ghi lại ở đây."
              />
            ) : (
              <ol className="relative space-y-4 border-l border-gray-200 dark:border-gray-800 pl-5">
                {[...event.actions]
                  .sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime())
                  .map((action) => (
                    <li key={action.id} className="relative">
                      <span
                        className="absolute -left-[27px] top-1.5 h-3 w-3 rounded-full border-2 border-white dark:border-gray-900 bg-blue-600"
                        aria-hidden
                      />
                      <div className="rounded-xl border border-gray-200 dark:border-gray-800/80 bg-slate-50 dark:bg-gray-950/70 p-3.5 shadow-sm">
                        <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
                          <span className="text-xs font-bold text-blue-600 dark:text-blue-400">
                            {action.actorName}
                          </span>
                          <span className="font-mono text-[11px] text-gray-500">
                            {new Date(action.at).toLocaleString('vi-VN')}
                          </span>
                        </div>
                        <p className="text-xs font-semibold text-gray-800 dark:text-gray-200">{action.action}</p>
                        {action.reason && (
                          <p className="mt-1.5 border-l-2 border-slate-300 dark:border-gray-700 pl-2 text-[11px] italic leading-relaxed text-gray-600 dark:text-gray-400">
                            Lý do: {action.reason}
                          </p>
                        )}
                      </div>
                    </li>
                  ))}
              </ol>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
