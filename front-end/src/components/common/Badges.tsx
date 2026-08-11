/**
 * Nhãn màu theo ngữ nghĩa cho severity / state / escalation / camera health.
 * BAC-56 yêu cầu "màu cảnh báo và trạng thái HITL nhất quán" — mọi màn hình
 * dùng chung các component này thay vì tự đặt class.
 */

import { Bot, CircleDot } from 'lucide-react';

import {
  CAMERA_HEALTH_LABEL,
  CameraHealth,
  ESCALATION_LABEL,
  EscalationState,
  EVENT_TYPE_LABEL,
  EventState,
  EventType,
  STATE_LABEL,
  SEVERITY_LABEL,
  Severity,
} from '../../domain/types';

const BASE =
  'inline-flex items-center gap-1 rounded-md px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider border shadow-sm transition-colors';

const SEVERITY_STYLE: Record<Severity, string> = {
  INFO: 'bg-sky-50 dark:bg-sky-500/15 text-sky-700 dark:text-sky-300 border-sky-300 dark:border-sky-500/40',
  WARNING: 'bg-amber-50 dark:bg-amber-500/15 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-500/40',
  HIGH: 'bg-orange-50 dark:bg-orange-500/15 text-orange-800 dark:text-orange-300 border-orange-300 dark:border-orange-500/40',
  CRITICAL: 'bg-rose-50 dark:bg-red-500/20 text-rose-800 dark:text-red-300 border-rose-300 dark:border-red-500/50',
};

const STATE_STYLE: Record<EventState, string> = {
  OPEN: 'bg-blue-50 dark:bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-500/40',
  ACKNOWLEDGED: 'bg-emerald-50 dark:bg-emerald-500/15 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/40',
  PENDING_REVIEW: 'bg-amber-50 dark:bg-amber-500/15 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-500/40',
  CONFIRMED: 'bg-rose-50 dark:bg-red-500/15 text-rose-800 dark:text-red-300 border-rose-300 dark:border-red-500/40',
  RESOLVED: 'bg-slate-100 dark:bg-gray-600/20 text-slate-700 dark:text-gray-300 border-slate-300 dark:border-gray-600/50',
  DISMISSED: 'bg-slate-100 dark:bg-gray-600/20 text-slate-600 dark:text-gray-400 border-slate-300 dark:border-gray-600/50',
  EXPIRED: 'bg-purple-50 dark:bg-purple-500/15 text-purple-700 dark:text-purple-300 border-purple-300 dark:border-purple-500/40',
};

const HEALTH_STYLE: Record<CameraHealth, string> = {
  HEALTHY: 'text-emerald-600 dark:text-emerald-400 font-semibold',
  DEGRADED: 'text-amber-600 dark:text-amber-400 font-semibold',
  OFFLINE: 'text-rose-600 dark:text-red-400 font-semibold',
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span className={`${BASE} ${SEVERITY_STYLE[severity]}`}>
      {SEVERITY_LABEL[severity]}
    </span>
  );
}

export function StateBadge({ state }: { state: EventState }) {
  return <span className={`${BASE} ${STATE_STYLE[state]}`}>{STATE_LABEL[state]}</span>;
}

export function EscalationBadge({ escalation }: { escalation: EscalationState }) {
  if (escalation === 'NONE') return null;

  const style =
    escalation === 'REQUESTED'
      ? 'bg-amber-50 dark:bg-amber-500/15 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-500/40'
      : escalation === 'APPROVED'
        ? 'bg-rose-50 dark:bg-red-500/15 text-rose-800 dark:text-red-300 border-rose-300 dark:border-red-500/40'
        : 'bg-slate-100 dark:bg-gray-600/20 text-slate-600 dark:text-gray-400 border-slate-300 dark:border-gray-600/50';

  return <span className={`${BASE} ${style}`}>{ESCALATION_LABEL[escalation]}</span>;
}

export function EventTypeBadge({ eventType }: { eventType: EventType }) {
  return (
    <span className={`${BASE} border-slate-300 dark:border-gray-700 bg-slate-100 dark:bg-gray-800/80 text-slate-800 dark:text-gray-300`}>
      {EVENT_TYPE_LABEL[eventType]}
    </span>
  );
}

export function HealthDot({ health }: { health: CameraHealth }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] ${HEALTH_STYLE[health]}`}>
      <CircleDot
        className={`h-3 w-3 ${health === 'HEALTHY' ? 'animate-pulse' : ''}`}
        aria-hidden
      />
      <span>{CAMERA_HEALTH_LABEL[health]}</span>
    </span>
  );
}

/** PRD §8.1: nguồn giả lập bắt buộc gắn nhãn SIMULATED. */
export function SimulatedBadge() {
  return (
    <span className={`${BASE} border-indigo-300 dark:border-indigo-500/40 bg-indigo-50 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-300`}>
      Nguồn giả lập
    </span>
  );
}

/** FR-AI-03: nội dung do LLM sinh phải được gắn nhãn rõ ràng. */
export function AiGeneratedBadge() {
  return (
    <span
      className={`${BASE} border-violet-300 dark:border-violet-500/40 bg-violet-50 dark:bg-violet-500/15 text-violet-700 dark:text-violet-300`}
      title="Mô tả do AI sinh ra, chỉ mang tính hỗ trợ. Quyết định thuộc về người trực."
    >
      <Bot className="h-3 w-3" aria-hidden />
      AI hỗ trợ
    </span>
  );
}
