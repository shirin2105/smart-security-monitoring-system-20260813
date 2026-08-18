import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ListFilter, SearchX } from 'lucide-react';

import { Card } from '@astryxdesign/core/Card';
import { HStack, VStack, StackItem } from '@astryxdesign/core/Stack';
import { Text, Heading } from '@astryxdesign/core/Text';
import { Table, TableRow, TableCell, TableHeaderCell } from '@astryxdesign/core/Table';

import { api } from '../api';
import { EMPTY_QUERY, IncidentQuery } from '../api/types';
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
              <Table density="compact" hasHover>
                <thead>
                  <TableRow>
                    <TableHeaderCell style={{ width: 170, whiteSpace: 'nowrap' }}>Thời điểm</TableHeaderCell>
                    <TableHeaderCell style={{ width: 160, whiteSpace: 'nowrap' }}>Camera</TableHeaderCell>
                    <TableHeaderCell style={{ width: 160, whiteSpace: 'nowrap' }}>Loại sự kiện</TableHeaderCell>
                    <TableHeaderCell style={{ width: 110, whiteSpace: 'nowrap' }}>Mức độ</TableHeaderCell>
                    <TableHeaderCell style={{ width: 260, whiteSpace: 'nowrap' }}>Trạng thái</TableHeaderCell>
                    <TableHeaderCell>Mô tả sự cố</TableHeaderCell>
                  </TableRow>
                </thead>
                <tbody>
                  {page.data.items.map((event) => (
                    <TableRow
                      key={event.id}
                      onClick={() => navigate(`/incidents/${event.id}`)}
                      style={{ cursor: 'pointer' }}
                    >
                      <TableCell style={{ whiteSpace: 'nowrap' }}>
                        <Text type="code" size="xsm" color="secondary">
                          {new Date(event.detectedAt).toLocaleString('vi-VN')}
                        </Text>
                      </TableCell>
                      <TableCell style={{ whiteSpace: 'nowrap' }}>
                        <Text type="label" weight="semibold">
                          {event.cameraName}
                        </Text>
                      </TableCell>
                      <TableCell style={{ whiteSpace: 'nowrap' }}>
                        <EventTypeBadge eventType={event.eventType} />
                      </TableCell>
                      <TableCell style={{ whiteSpace: 'nowrap' }}>
                        <SeverityBadge severity={event.effectiveSeverity} />
                      </TableCell>
                      <TableCell>
                        <HStack gap={1} vAlign="center" style={{ flexWrap: 'nowrap' }}>
                          <StateBadge state={event.state} />
                          <EscalationBadge escalation={event.escalation} />
                          <SourceBadge sourceType={event.sourceType} />
                        </HStack>
                      </TableCell>
                      <TableCell>
                        <Text type="body" maxLines={2}>
                          {event.description}
                        </Text>
                      </TableCell>
                    </TableRow>
                  ))}
                </tbody>
              </Table>
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

