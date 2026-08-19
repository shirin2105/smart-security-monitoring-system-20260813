import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, CheckCircle2, Clock } from 'lucide-react';

import { Card } from '@astryxdesign/core/Card';
import { HStack, VStack } from '@astryxdesign/core/Stack';
import { Text, Heading } from '@astryxdesign/core/Text';
import { Badge } from '@astryxdesign/core/Badge';
import { Button } from '@astryxdesign/core/Button';
import { Divider } from '@astryxdesign/core/Divider';
import { SegmentedControl, SegmentedControlItem } from '@astryxdesign/core/SegmentedControl';

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
import { EvidenceMedia } from '../common/EvidenceMedia';

type FilterKey = 'all' | 'active' | 'closed';

const ACTIVE_STATES = ['OPEN', 'PENDING_REVIEW', 'ACKNOWLEDGED', 'CONFIRMED'];

interface AlertSidebarProps {
  events: SecurityEvent[];
  loading: boolean;
  error: unknown;
  onRetry: () => void;
}

export function AlertSidebar({ events, loading, error, onRetry }: AlertSidebarProps) {
  const [filter, setFilter] = useState<FilterKey>('all');

  const activeCount = useMemo(
    () => events.filter((event) => ACTIVE_STATES.includes(event.state)).length,
    [events],
  );

  const criticalCount = useMemo(
    () =>
      events.filter(
        (event) => ACTIVE_STATES.includes(event.state) && event.effectiveSeverity === 'CRITICAL',
      ).length,
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

  return (
    <VStack
      gap={0}
      height="100%"
      as="aside"
      aria-label="Hàng chờ cảnh báo"
      style={{
        height: '100%',
        maxHeight: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <VStack gap={0} paddingInline={4} paddingBlock={3} style={{ flexShrink: 0 }}>
        <HStack justify="between" vAlign="center">
          <HStack gap={2} vAlign="center">
            <Bell
              size={18}
              color={criticalCount > 0 ? 'var(--color-error)' : 'var(--color-text-primary)'}
            />
            <VStack gap={0}>
              <Heading level={2}>
                CẢNH BÁO THỜI GIAN THỰC
              </Heading>
              <Text type="supporting" color="secondary">
                {events.length} sự cố gần nhất · {activeCount} chưa xử lý
              </Text>
            </VStack>
          </HStack>

          {activeCount > 0 && (
            <Badge
              variant={criticalCount > 0 ? 'error' : 'warning'}
              label={activeCount}
            />
          )}
        </HStack>
      </VStack>
      <Divider />

      {/* Filter Tabs */}
      <VStack gap={0} paddingInline={4} paddingBlock={2} style={{ flexShrink: 0 }}>
        <SegmentedControl
          label="Lọc cảnh báo"
          value={filter}
          onChange={(val) => setFilter(val as FilterKey)}
          size="sm"
          layout="fill"
        >
          <SegmentedControlItem value="all" label={`Tất cả (${events.length})`} />
          <SegmentedControlItem value="active" label={`Chờ xử lý (${activeCount})`} />
          <SegmentedControlItem value="closed" label={`Đã giải quyết (${events.length - activeCount})`} />
        </SegmentedControl>
      </VStack>
      <Divider />

      {/* List content - constrained scrollable container */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: 'auto',
          padding: 'var(--spacing-3)',
        }}
      >
        <VStack gap={3}>
          {loading && events.length === 0 ? (
            <LoadingState label="Đang tải cảnh báo…" />
          ) : error != null && events.length === 0 ? (
            <ErrorState error={error} onRetry={onRetry} />
          ) : visible.length === 0 ? (
            <EmptyState
              icon={<CheckCircle2 size={36} />}
              title="Không có cảnh báo nào"
              hint={
                filter === 'all'
                  ? 'Hệ thống đang giám sát bình thường.'
                  : 'Không có sự cố nào trong bộ lọc này.'
              }
            />
          ) : (
            visible.map((event) => (
              <AlertCard key={event.id} event={event} />
            ))
          )}
        </VStack>
      </div>
    </VStack>
  );
}

function AlertCard({ event }: { event: SecurityEvent }) {
  const navigate = useNavigate();
  const critical = event.effectiveSeverity === 'CRITICAL';
  const high = event.effectiveSeverity === 'HIGH';
  const active = ACTIVE_STATES.includes(event.state);

  return (
    <Card
      elevation="low"
      padding={3}
      style={{
        border: critical && active
          ? '1.5px solid var(--color-error)'
          : high && active
          ? '1.5px solid var(--color-warning)'
          : active
          ? '1px solid var(--color-border-emphasized)'
          : '1px solid var(--color-border)',
        backgroundColor: critical && active
          ? 'var(--color-error-muted)'
          : high && active
          ? 'var(--color-warning-muted)'
          : 'var(--color-background-card)',
        borderRadius: 'var(--radius-container)',
        transition: 'all 0.15s ease-in-out',
      }}
    >
      <VStack gap={2}>
        {/* Badges and time */}
        <HStack justify="between" vAlign="center" gap={1.5} style={{ flexWrap: 'nowrap' }}>
          <HStack gap={1} vAlign="center" style={{ flexWrap: 'wrap' }}>
            <SeverityBadge severity={event.effectiveSeverity} />
            <StateBadge state={event.state} />
            <EscalationBadge escalation={event.escalation} />
          </HStack>
          <HStack gap={1} vAlign="center" style={{ flexShrink: 0, whiteSpace: 'nowrap' }}>
            <Clock size={12} />
            <Text type="code" size="xsm" color="secondary">
              {new Date(event.detectedAt).toLocaleTimeString('vi-VN', { hour12: false })}
            </Text>
          </HStack>
        </HStack>

        {/* Type & camera */}
        <HStack justify="between" vAlign="center" gap={1.5}>
          <HStack gap={1.5} vAlign="center">
            <EventTypeBadge eventType={event.eventType} />
            <Text type="label" weight="semibold">
              {event.cameraName}
            </Text>
          </HStack>
          {event.aiGenerated && <AiGeneratedBadge />}
        </HStack>

        {/* Redacted Artifact */}
        {event.artifact?.redactionStatus === 'COMPLETE' && event.artifact.url && (
          <div
            style={{
              position: 'relative',
              width: '100%',
              borderRadius: 'var(--radius-inner)',
              overflow: 'hidden',
              border: '1px solid var(--color-border)',
              backgroundColor: 'var(--color-background-muted)',
            }}
          >
            <EvidenceMedia
              artifact={event.artifact}
              description={event.description}
              style={{
                width: '100%',
                maxHeight: '140px',
                objectFit: 'cover',
                display: 'block',
              }}
              autoPlay
              loop
            />
          </div>
        )}

        {event.artifact && event.artifact.redactionStatus !== 'COMPLETE' && (
          <Text type="supporting" color="secondary">
            Ảnh bằng chứng không khả dụng — chưa che mặt xong nên hệ thống không hiển thị.
          </Text>
        )}

        {/* Description */}
        <Text type="body">
          {event.description}
        </Text>

        {/* HITL Action bar */}
        <Divider />
        <HitlActionBar event={event} />

        {/* Detail link */}
        <Button
          label="Xem chi tiết & lịch sử →"
          variant="ghost"
          size="sm"
          onClick={() => navigate(`/incidents/${event.id}`)}
        />
      </VStack>
    </Card>
  );
}

