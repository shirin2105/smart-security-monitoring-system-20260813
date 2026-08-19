import { useState } from 'react';
import { Lock, Info } from 'lucide-react';

import { Button } from '@astryxdesign/core/Button';
import { HStack, VStack } from '@astryxdesign/core/Stack';
import { Text } from '@astryxdesign/core/Text';

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
  compact?: boolean;
  onDone?: (updated: SecurityEvent) => void;
}

const BUTTON_VARIANT: Record<ActionSpec['tone'], 'primary' | 'destructive' | 'secondary'> = {
  primary: 'primary',
  danger: 'destructive',
  warning: 'secondary',
  neutral: 'secondary',
};

export function HitlActionBar({ event, onDone }: HitlActionBarProps) {
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
    if (submitting) return;
    if (reasonRequired(spec.type, event.effectiveSeverity)) {
      setPendingReason(spec);
      return;
    }
    void send(spec);
  };

  if (!actions.length) {
    return (
      <VStack gap={2}>
        {blocked && (
          <HStack gap={1.5} vAlign="start" padding={2}>
            <Lock size={14} color="var(--color-warning)" style={{ flexShrink: 0, marginTop: 2 }} />
            <Text type="supporting" color="secondary">
              {blocked}
            </Text>
          </HStack>
        )}
        {error != null && <InlineError error={error} />}
      </VStack>
    );
  }

  return (
    <VStack gap={2}>
      <HStack gap={2} wrap="wrap">
        {actions.map((spec) => {
          const isSubmitting = submitting === spec.type;
          const disabled = submitting !== null;

          return (
            <Button
              key={spec.type}
              label={spec.label}
              variant={BUTTON_VARIANT[spec.tone]}
              size="sm"
              isLoading={isSubmitting}
              isDisabled={disabled}
              onClick={() => handleClick(spec)}
            />
          );
        })}
      </HStack>

      {blocked && (
        <HStack gap={1.5} vAlign="start">
          <Info size={12} color="var(--color-text-secondary)" style={{ flexShrink: 0, marginTop: 2 }} />
          <Text type="supporting" color="secondary">
            {blocked}
          </Text>
        </HStack>
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
    </VStack>
  );
}
