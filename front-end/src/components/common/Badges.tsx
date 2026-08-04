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
  'inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide border';

const SEVERITY_STYLE: Record<Severity, string> = {
  INFO: 'bg-sky-500/15 text-sky-300 border-sky-500/40',
  WARNING: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
  HIGH: 'bg-orange-500/15 text-orange-300 border-orange-500/40',
  CRITICAL: 'bg-red-500/20 text-red-300 border-red-500/50',
};

const STATE_STYLE: Record<EventState, string> = {
  OPEN: 'bg-blue-500/15 text-blue-300 border-blue-500/40',
  ACKNOWLEDGED: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
  PENDING_REVIEW: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
  CONFIRMED: 'bg-red-500/15 text-red-300 border-red-500/40',
  RESOLVED: 'bg-gray-600/20 text-gray-300 border-gray-600/50',
  DISMISSED: 'bg-gray-600/20 text-gray-400 border-gray-600/50',
  EXPIRED: 'bg-purple-500/15 text-purple-300 border-purple-500/40',
};

const HEALTH_STYLE: Record<CameraHealth, string> = {
  HEALTHY: 'text-emerald-400',
  DEGRADED: 'text-amber-400',
  OFFLINE: 'text-red-400',
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
      ? 'bg-amber-500/15 text-amber-300 border-amber-500/40'
      : escalation === 'APPROVED'
        ? 'bg-red-500/15 text-red-300 border-red-500/40'
        : 'bg-gray-600/20 text-gray-400 border-gray-600/50';

  return <span className={`${BASE} ${style}`}>{ESCALATION_LABEL[escalation]}</span>;
}

export function EventTypeBadge({ eventType }: { eventType: EventType }) {
  return (
    <span className={`${BASE} border-gray-700 bg-gray-800/80 text-gray-300`}>
      {EVENT_TYPE_LABEL[eventType]}
    </span>
  );
}

export function HealthDot({ health }: { health: CameraHealth }) {
  return (
    <span className={`inline-flex items-center gap-1 text-[11px] ${HEALTH_STYLE[health]}`}>
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
    <span className={`${BASE} border-indigo-500/40 bg-indigo-500/15 text-indigo-300`}>
      Nguồn giả lập
    </span>
  );
}

/** FR-AI-03: nội dung do LLM sinh phải được gắn nhãn rõ ràng. */
export function AiGeneratedBadge() {
  return (
    <span
      className={`${BASE} border-violet-500/40 bg-violet-500/15 text-violet-300`}
      title="Mô tả do AI sinh ra, chỉ mang tính hỗ trợ. Quyết định thuộc về người trực."
    >
      <Bot className="h-3 w-3" aria-hidden />
      AI hỗ trợ
    </span>
  );
}
