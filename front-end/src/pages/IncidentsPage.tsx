import { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ListFilter, SearchX } from 'lucide-react';

import { Card } from '@astryxdesign/core/Card';
import { HStack, VStack, StackItem } from '@astryxdesign/core/Stack';
import { Text, Heading } from '@astryxdesign/core/Text';
import { Table, pixel, proportional } from '@astryxdesign/core/Table';
import type { TableColumn } from '@astryxdesign/core/Table';

import { api } from '../api';
import { EMPTY_QUERY, IncidentQuery } from '../api/types';
import { SecurityEvent } from '../domain/types';
import {
  EscalationBadge,
  EventTypeBadge,
  SeverityBadge,
  SourceBadge,
  StateBadge,
} from '../components/common/Badges';
import { EmptyState, ErrorState, LoadingState } from '../components/common/States';
import { IncidentFilters } from '../components/incidents/IncidentFilters';
import { Pagination } from '../components/incidents/Pagination';
import { useAsync } from '../hooks/useAsync';
import { useEvents } from '../realtime/EventsProvider';

export function IncidentsPage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState<IncidentQuery>(EMPTY_QUERY);
  const { revision } = useEvents();

  const cameras = useAsync(() => api.getCameras(), []);

  const page = useAsync(
    () => api.getEvents(query),
    [JSON.stringify(query), revision],
  );

  const patchQuery = useCallback((patch: Partial<IncidentQuery>) => {
    setQuery((previous) => ({ ...previous, ...patch }));
  }, []);

  const resetQuery = useCallback(() => setQuery(EMPTY_QUERY), []);

  const columns = useMemo<TableColumn<SecurityEvent>[]>(
    () => [
      {
        key: 'detectedAt',
        header: 'Thời điểm',
        width: pixel(175),
        renderCell: (event) => (
          <Text type="code" size="xsm" color="secondary">
            {new Date(event.detectedAt).toLocaleString('vi-VN')}
          </Text>
        ),
      },
      {
        key: 'cameraName',
        header: 'Camera',
        width: pixel(180),
        renderCell: (event) => (
          <Text type="label" weight="semibold">
            {event.cameraName}
          </Text>
        ),
      },
      {
        key: 'eventType',
        header: 'Loại sự kiện',
        width: pixel(170),
        renderCell: (event) => <EventTypeBadge eventType={event.eventType} />,
      },
      {
        key: 'effectiveSeverity',
        header: 'Mức độ',
        width: pixel(110),
        renderCell: (event) => <SeverityBadge severity={event.effectiveSeverity} />,
      },
      {
        key: 'state',
        header: 'Trạng thái',
        width: pixel(260),
        renderCell: (event) => (
          <HStack gap={1} vAlign="center" style={{ flexWrap: 'nowrap' }}>
            <StateBadge state={event.state} />
            <EscalationBadge escalation={event.escalation} />
            <SourceBadge sourceType={event.sourceType} />
          </HStack>
        ),
      },
      {
        key: 'description',
        header: 'Mô tả sự cố',
        width: proportional(1, { minWidth: 260 }),
        renderCell: (event) => (
          <Text type="body" maxLines={2}>
            {event.description}
          </Text>
        ),
      },
    ],
    [],
  );

  const plugins = useMemo(
    () => ({
      rowClick: {
        transformBodyRow: (props: any, item: SecurityEvent) => ({
          ...props,
          htmlProps: {
            ...props.htmlProps,
            onClick: () => navigate(`/incidents/${item.id}`),
            style: { ...props.htmlProps?.style, cursor: 'pointer' },
          },
        }),
      },
    }),
    [navigate],
  );

  return (
    <VStack gap={4} padding={4} height="100%">
      {/* Header */}
      <HStack gap={2} vAlign="center">
        <ListFilter size={20} />
        <Heading level={1}>
          NHẬT KÝ SỰ CỐ
        </Heading>
      </HStack>

      {/* Filters */}
      <IncidentFilters
        query={query}
        cameras={cameras.data ?? []}
        onChange={patchQuery}
        onReset={resetQuery}
      />

      {/* Table section */}
      <Card elevation="low" padding={3} style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {page.loading && !page.data ? (
          <LoadingState label="Đang tải danh sách sự cố…" />
        ) : page.error != null ? (
          <ErrorState error={page.error} onRetry={page.reload} />
        ) : !page.data || page.data.items.length === 0 ? (
          <EmptyState
            icon={<SearchX size={40} />}
            title="Không có sự cố nào khớp bộ lọc"
            hint="Thử mở rộng khoảng thời gian hoặc xóa bớt điều kiện lọc."
          />
        ) : (
          <VStack gap={3} height="100%">
            <StackItem size="fill" isScrollable>
              <Table
                data={page.data.items}
                columns={columns}
                idKey="id"
                density="balanced"
                hasHover
                plugins={plugins}
              />
            </StackItem>

            <Pagination
              page={page.data.page}
              pageSize={page.data.pageSize}
              total={page.data.total}
              onChange={(next) => patchQuery({ page: next })}
            />
          </VStack>
        )}
      </Card>
    </VStack>
  );
}

