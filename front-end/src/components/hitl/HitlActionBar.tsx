import { useState } from 'react';
import { Info, Loader2, Lock } from 'lucide-react';

import { api } from '../../api';
import { useAuth } from '../../auth/AuthContext';
import {
  ActionSpec,
  allowedActions,
  blockedReason,
  reasonRequired,
} from '../../domain/permissions';
import { SecurityEvent } from '../../domain/types';
import { useEvents } from '../../realtime/EventsProvider';
import { InlineError } from '../common/States';
import { ReasonDialog } from './ReasonDialog';

interface HitlActionBarProps {
  event: SecurityEvent;
  /** Bố cục gọn cho sidebar, rộng cho trang chi tiết. */
  compact?: boolean;
  onDone?: (updated: SecurityEvent) => void;
}

const TONE_CLASS: Record<ActionSpec['tone'], string> = {
  primary:
    'bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-500 focus-visible:ring-emerald-400',
  danger:
    'bg-red-600 hover:bg-red-500 text-white border-red-500 focus-visible:ring-red-400',
  warning:
    'bg-amber-600/20 hover:bg-amber-600/30 text-amber-200 border-amber-500/50 focus-visible:ring-amber-400',
  neutral:
    'bg-gray-800 hover:bg-gray-700 text-gray-200 border-gray-700 focus-visible:ring-gray-400',
};

/**
 * Thanh hành động HITL — BAC-53.
 *
 * Ba bảo đảm:
 *   1. Chỉ hiện action hợp lệ theo full state × role × scope matrix.
 *   2. Khóa toàn bộ nút trong lúc gửi → không double-submit.
 *   3. Lỗi 403 / 409 / chưa-có-backend hiện thành thông điệp đọc được.
 */
export function HitlActionBar({ event, compact, onDone }: HitlActionBarProps) {
  const { user, reportApiError } = useAuth();
  const { upsert } = useEvents();

  const [submitting, setSubmitting] = useState<ActionSpec['type'] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [pendingReason, setPendingReason] = useState<ActionSpec | null>(null);

  if (!user) return null;

  const actions = allowedActions(event, user.role, user.cameraScope);
  const blocked = blockedReason(event, user.role);

  const send = async (spec: ActionSpec, reason?: string) => {
    setSubmitting(spec.type);
    setError(null);
    try {
      const updated = await api.postAction(event.id, {
        action: spec.type,
        reason,
        expectedVersion: event.version,
      });
      upsert(updated);
      onDone?.(updated);
      setPendingReason(null);
    } catch (err) {
      reportApiError(err);
      setError(err);
      setPendingReason(null);
    } finally {
      setSubmitting(null);
    }
  };

  const handleClick = (spec: ActionSpec) => {
    if (submitting) return; // chốt chống double-submit
    if (reasonRequired(spec.type, event.effectiveSeverity)) {
      setPendingReason(spec);
      return;
    }
    void send(spec);
  };

  if (!actions.length) {
    return (
      <div className="space-y-2">
        {blocked && (
          <p className="flex items-start gap-1.5 rounded-lg border border-gray-800 bg-gray-900/60 p-2.5 text-[11px] leading-relaxed text-gray-400">
            <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" aria-hidden />
            <span>{blocked}</span>
          </p>
        )}
        {error != null && <InlineError error={error} />}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className={`flex flex-wrap gap-2 ${compact ? '' : 'pt-1'}`}>
        {actions.map((spec) => {
          const isSubmitting = submitting === spec.type;
          const disabled = submitting !== null;

          return (
            <button
              key={spec.type}
              onClick={() => handleClick(spec)}
              disabled={disabled}
              aria-busy={isSubmitting}
              className={`flex items-center justify-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all focus:outline-none focus-visible:ring-2 disabled:cursor-not-allowed disabled:opacity-50 ${
                TONE_CLASS[spec.tone]
              } ${compact ? 'flex-1' : ''}`}
            >
              {isSubmitting && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />}
              <span>{spec.label}</span>
            </button>
          );
        })}
      </div>

      {blocked && (
        <p className="flex items-start gap-1.5 text-[11px] leading-relaxed text-gray-500">
          <Info className="mt-0.5 h-3 w-3 shrink-0" aria-hidden />
          <span>{blocked}</span>
        </p>
      )}

      {error != null && <InlineError error={error} />}

      {pendingReason && (
        <ReasonDialog
          title={`${pendingReason.label} — sự cố #${event.id}`}
          description={`${event.cameraName} · ${event.description}`}
          confirmLabel={pendingReason.label}
          submitting={submitting === pendingReason.type}
          onCancel={() => setPendingReason(null)}
          onSubmit={(reason) => void send(pendingReason, reason)}
        />
      )}
    </div>
  );
}
