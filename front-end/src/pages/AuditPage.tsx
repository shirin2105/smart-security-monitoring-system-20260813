import { useNavigate } from 'react-router-dom';
import { History, ScrollText } from 'lucide-react';

import { Card } from '@astryxdesign/core/Card';
import { HStack, VStack } from '@astryxdesign/core/Stack';
import { Text, Heading } from '@astryxdesign/core/Text';
import { Button } from '@astryxdesign/core/Button';

import { api } from '../api';
import { EmptyState, ErrorState, LoadingState } from '../components/common/States';
import { useAsync } from '../hooks/useAsync';
import { useEvents } from '../realtime/EventsProvider';

export function AuditPage() {
  const navigate = useNavigate();
  const { revision } = useEvents();
  const logs = useAsync(() => api.getAuditLog(), [revision]);

  return (
    <VStack gap={4} padding={4} height="100%" isScrollable>
      {/* Header */}
      <HStack gap={2} vAlign="center">
        <History size={20} />
        <VStack gap={0.5}>
          <Heading level={1}>
            NHẬT KÝ THAO TÁC (AUDIT TRAIL)
          </Heading>
          <Text type="supporting" size="xsm" color="secondary">
            Chỉ ghi thêm, không thể sửa hoặc xóa — mọi quyết định của người trực đều lưu vĩnh viễn.
          </Text>
        </VStack>
      </HStack>

      <Card elevation="low" padding={4}>
        {logs.loading && !logs.data ? (
          <LoadingState label="Đang tải nhật ký…" />
        ) : logs.error != null ? (
          <ErrorState error={logs.error} onRetry={logs.reload} />
        ) : !logs.data || logs.data.length === 0 ? (
          <EmptyState
            icon={<ScrollText size={40} />}
            title="Chưa có thao tác nào được ghi nhận"
            hint="Nhật ký sẽ xuất hiện ngay khi có người tiếp nhận hoặc xử lý một sự cố."
          />
        ) : (
          <VStack gap={3}>
            {logs.data.map((log) => (
              <Card
                key={log.id}
                elevation="none"
                padding={3}
                style={{
                  backgroundColor: 'var(--color-background-muted)',
                  border: '1px solid var(--color-border)',
                }}
              >
                <VStack gap={1.5}>
                  <HStack justify="between" vAlign="center" gap={2} style={{ flexWrap: 'nowrap' }}>
                    <Text type="label" weight="bold" color="accent">
                      {log.actorName}
                    </Text>
                    <Text type="code" size="xsm" color="secondary" style={{ flexShrink: 0, whiteSpace: 'nowrap' }}>
                      {new Date(log.at).toLocaleString('vi-VN')}
                    </Text>
                  </HStack>

                  <Text type="body" weight="semibold">
                    {log.action}
                  </Text>

                  {log.reason && (
                    <VStack
                      gap={0}
                      paddingInline={2}
                      paddingBlock={1}
                      style={{
                        borderLeft: '2px solid var(--color-border-emphasized)',
                      }}
                    >
                      <Text type="supporting" color="secondary">
                        Lý do: {log.reason}
                      </Text>
                    </VStack>
                  )}

                  {log.incidentId != null && (
                    <HStack justify="start">
                      <Button
                        label={`Sự cố #${log.incidentId} →`}
                        variant="ghost"
                        size="sm"
                        onClick={() => navigate(`/incidents/${log.incidentId}`)}
                      />
                    </HStack>
                  )}
                </VStack>
              </Card>
            ))}
          </VStack>
        )}
      </Card>
    </VStack>
  );
}

