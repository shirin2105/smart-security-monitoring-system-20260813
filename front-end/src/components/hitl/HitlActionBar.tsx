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
import { useToast } from '../../hooks/useToast';
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
    'bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-500 focus-visible:ring-emerald-400 shadow-sm',
  danger:
    'bg-rose-600 hover:bg-rose-500 text-white border-rose-500 focus-visible:ring-rose-400 shadow-sm',
  warning:
    'bg-amber-500/10 dark:bg-amber-600/20 hover:bg-amber-500/20 dark:hover:bg-amber-600/30 text-amber-800 dark:text-amber-200 border-amber-400 dark:border-amber-500/50 focus-visible:ring-amber-400',
  neutral:
    'bg-slate-100 dark:bg-gray-800 hover:bg-slate-200 dark:hover:bg-gray-700 text-slate-800 dark:text-gray-200 border-slate-300 dark:border-gray-700 focus-visible:ring-gray-400 shadow-sm',
};

/**
 * Thanh hành động HITL — BAC-53.
 */
export function HitlActionBar({ event, compact, onDone }: HitlActionBarProps) {
  const { user, reportApiError } = useAuth();
  const { upsert } = useEvents();
  const toast = useToast();

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
      toast.success(
        `Thao tác thành công: ${spec.label}`,
        `Sự cố #${event.id} tại ${event.cameraName} đã được cập nhật.`,
      );
      onDone?.(updated);
      setPendingReason(null);
    } catch (err) {
      reportApiError(err);
      setError(err);
      toast.error(
        `Lỗi thao tác ${spec.label}`,
        err instanceof Error ? err.message : 'Không thể thực hiện hành động.',
      );
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
          <p className="flex items-start gap-1.5 rounded-lg border border-amber-200 dark:border-gray-800 bg-amber-50/50 dark:bg-gray-900/60 p-2.5 text-[11px] leading-relaxed text-amber-900 dark:text-gray-400">
            <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden />
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
              className={`flex items-center justify-center gap-1.5 rounded-lg border px-3.5 py-2 text-xs font-bold transition-all focus:outline-none focus-visible:ring-2 disabled:cursor-not-allowed disabled:opacity-50 active:scale-95 ${
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
        <p className="flex items-start gap-1.5 text-[11px] leading-relaxed text-slate-500 dark:text-gray-500">
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
