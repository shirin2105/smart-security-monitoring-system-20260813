/**
 * Nhãn màu theo ngữ nghĩa cho severity / state / escalation / camera health.
 * Dùng Token và StatusDot theo chuẩn Astryx Design System.
 */

import { Bot } from 'lucide-react';
import { Token } from '@astryxdesign/core/Token';
import { StatusDot } from '@astryxdesign/core/StatusDot';
import { HStack } from '@astryxdesign/core/Stack';
import { Text } from '@astryxdesign/core/Text';

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

const SEVERITY_COLOR: Record<Severity, 'cyan' | 'yellow' | 'orange' | 'red'> = {
  INFO: 'cyan',
  WARNING: 'yellow',
  HIGH: 'orange',
  CRITICAL: 'red',
};

const STATE_COLOR: Record<EventState, 'blue' | 'green' | 'orange' | 'red' | 'gray' | 'purple'> = {
  OPEN: 'blue',
  ACKNOWLEDGED: 'green',
  PENDING_REVIEW: 'orange',
  CONFIRMED: 'red',
  RESOLVED: 'gray',
  DISMISSED: 'gray',
  EXPIRED: 'purple',
};

const ESCALATION_COLOR: Record<EscalationState, 'default' | 'orange' | 'red' | 'gray'> = {
  NONE: 'default',
  REQUESTED: 'orange',
  APPROVED: 'red',
  DECLINED: 'gray',
};

const HEALTH_VARIANT: Record<CameraHealth, 'success' | 'warning' | 'error'> = {
  HEALTHY: 'success',
  DEGRADED: 'warning',
  OFFLINE: 'error',
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <Token
      size="sm"
      color={SEVERITY_COLOR[severity]}
      label={SEVERITY_LABEL[severity]}
    />
  );
}

export function StateBadge({ state }: { state: EventState }) {
  return (
    <Token
      size="sm"
      color={STATE_COLOR[state]}
      label={STATE_LABEL[state]}
    />
  );
}

export function EscalationBadge({ escalation }: { escalation: EscalationState }) {
  if (escalation === 'NONE') return null;

  return (
    <Token
      size="sm"
      color={ESCALATION_COLOR[escalation]}
      label={ESCALATION_LABEL[escalation]}
    />
  );
}

export function EventTypeBadge({ eventType }: { eventType: EventType }) {
  return (
    <Token
      size="sm"
      color="gray"
      label={EVENT_TYPE_LABEL[eventType]}
    />
  );
}

export function HealthDot({ health }: { health: CameraHealth }) {
  return (
    <HStack gap={1} vAlign="center">
      <StatusDot variant={HEALTH_VARIANT[health]} label={CAMERA_HEALTH_LABEL[health]} />
      <Text type="label" size="xsm" weight="semibold">
        {CAMERA_HEALTH_LABEL[health]}
      </Text>
    </HStack>
  );
}

/** PRD §8.1: nguồn giả lập bắt buộc gắn nhãn SIMULATED. */
export function SimulatedBadge() {
  return (
    <Token
      size="sm"
      color="purple"
      label="Dữ liệu giả lập"
    />
  );
}

/** Nguồn phát hiện: CV pipeline thật (LIVE) hay simulator. */
export function SourceBadge({ sourceType }: { sourceType: 'LIVE' | 'SIMULATED' }) {
  if (sourceType === 'LIVE') {
    return (
      <Token
        size="sm"
        color="green"
        label="Camera trực tiếp"
      />
    );
  }
  return <SimulatedBadge />;
}

/** FR-AI-03: nội dung do LLM sinh phải được gắn nhãn rõ ràng. */
export function AiGeneratedBadge() {
  return (
    <Token
      size="sm"
      color="purple"
      icon={<Bot size={12} />}
      label="AI phân tích"
    />
  );
}
