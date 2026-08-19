import { useNavigate, useParams } from 'react-router-dom';
import { ImageOff } from 'lucide-react';

import { Breadcrumbs, BreadcrumbItem } from '@astryxdesign/core/Breadcrumbs';
import { Card } from '@astryxdesign/core/Card';
import { Grid } from '@astryxdesign/core/Grid';
import { HStack, VStack } from '@astryxdesign/core/Stack';
import { Text, Heading } from '@astryxdesign/core/Text';
import { AspectRatio } from '@astryxdesign/core/AspectRatio';
import { Banner } from '@astryxdesign/core/Banner';

import { api } from '../api';
import {
  AiGeneratedBadge,
  EscalationBadge,
  EventTypeBadge,
  SeverityBadge,
  StateBadge,
} from '../components/common/Badges';
import { EmptyState, ErrorState, LoadingState } from '../components/common/States';
import { HitlActionBar } from '../components/hitl/HitlActionBar';
import { EvidenceMedia } from '../components/common/EvidenceMedia';
import { SEVERITY_LABEL } from '../domain/types';
import { useAsync } from '../hooks/useAsync';
import { useEvents } from '../realtime/EventsProvider';

export function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const eventId = Number(id);
  const { revision } = useEvents();
  const navigate = useNavigate();

  const detail = useAsync(() => api.getEvent(eventId), [eventId, revision]);

  if (Number.isNaN(eventId)) {
    return <EmptyState title="Mã sự cố không hợp lệ" />;
  }

  if (detail.loading && !detail.data) return <LoadingState label="Đang tải sự cố…" />;
  if (detail.error != null) {
    return <ErrorState error={detail.error} onRetry={detail.reload} />;
  }
  if (!detail.data) return <EmptyState title="Không tìm thấy sự cố" />;

  const event = detail.data;
  const artifactUsable =
    event.artifact?.redactionStatus === 'COMPLETE' && Boolean(event.artifact.url);

  return (
    <VStack gap={4} padding={4} height="100%" isScrollable>
      {/* Breadcrumbs */}
      <Breadcrumbs>
        <BreadcrumbItem
          href="/incidents"
          onClick={(e) => {
            e.preventDefault();
            navigate('/incidents');
          }}
        >
          Nhật ký sự cố
        </BreadcrumbItem>
        <BreadcrumbItem isCurrent>
          Sự cố #{event.id}
        </BreadcrumbItem>
      </Breadcrumbs>

      <Grid columns={{ minWidth: 360, max: 2 }} gap={4}>
        {/* Left Column: Evidence + Description */}
        <Card elevation="low" padding={4}>
          <VStack gap={4}>
            {/* Header info */}
            <VStack gap={2}>
              <HStack gap={1.5} vAlign="center" wrap="wrap">
                <SeverityBadge severity={event.effectiveSeverity} />
                <StateBadge state={event.state} />
                <EscalationBadge escalation={event.escalation} />
                <EventTypeBadge eventType={event.eventType} />
              </HStack>

              <Heading level={1}>
                Sự cố #{event.id} · {event.cameraName}
              </Heading>

              <Text type="code" size="xsm" color="secondary">
                Phát hiện lúc {new Date(event.detectedAt).toLocaleString('vi-VN')} · phiên bản {event.version}
              </Text>
            </VStack>

            {/* Evidence Image/Video */}
            {artifactUsable ? (
              <AspectRatio ratio={16 / 9}>
                <EvidenceMedia
                  artifact={event.artifact!}
                  description={`sự cố #${event.id}`}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'contain',
                    borderRadius: 'var(--radius-container)',
                    border: '1px solid var(--color-border)',
                    backgroundColor: 'var(--color-background-muted)',
                  }}
                  autoPlay
                  controls
                  loop
                />
              </AspectRatio>
            ) : (
              <Card elevation="none" padding={4} style={{ backgroundColor: 'var(--color-background-muted)' }}>
                <EmptyState
                  icon={<ImageOff size={32} />}
                  title="Ảnh bằng chứng không khả dụng"
                  hint="Hệ thống chỉ hiển thị ảnh sau khi che mặt thành công. Nếu che mặt lỗi, ảnh bị loại bỏ và chỉ giữ lại dữ liệu mô tả."
                />
              </Card>
            )}

            {/* Description */}
            <VStack gap={1.5}>
              <HStack gap={2} vAlign="center">
                <Text type="label" weight="bold">
                  MÔ TẢ SỰ CỐ
                </Text>
                {event.aiGenerated && <AiGeneratedBadge />}
              </HStack>

              <Text type="body">
                {event.description}
              </Text>

              {event.aiGenerated && (
                <Text type="supporting" color="secondary">
                  Nội dung do AI tổng hợp từ dữ liệu phát hiện, chỉ mang tính hỗ trợ. Quyết định xử lý thuộc về người trực.
                </Text>
              )}
            </VStack>

            {/* Recommended severity note */}
            {event.recommendedSeverity && event.recommendedSeverity !== event.effectiveSeverity && (
              <Banner
                status="info"
                container="card"
                title="Đề xuất từ AI"
                description={`AI đề xuất mức ${SEVERITY_LABEL[event.recommendedSeverity]}, nhưng mức áp dụng theo chính sách là ${SEVERITY_LABEL[event.effectiveSeverity]}. Mức áp dụng luôn do chính sách quyết định.`}
              />
            )}
          </VStack>
        </Card>

        {/* Right Column: Actions + History */}
        <VStack gap={4}>
          {/* Actions Card */}
          <Card elevation="low" padding={4}>
            <VStack gap={3}>
              <Heading level={2}>
                HÀNH ĐỘNG CỦA BẠN
              </Heading>
              <HitlActionBar event={event} />
            </VStack>
          </Card>

          {/* History Card */}
          <Card elevation="low" padding={4}>
            <VStack gap={3}>
              <Heading level={2}>
                LỊCH SỬ XỬ LÝ ({event.actions.length})
              </Heading>

              {event.actions.length === 0 ? (
                <EmptyState
                  title="Chưa có thao tác nào"
                  hint="Mọi thao tác xác nhận, bỏ qua hay phê duyệt đều được ghi lại ở đây."
                />
              ) : (
                <VStack gap={2}>
                  {[...event.actions]
                    .sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime())
                    .map((action) => (
                      <Card
                        key={action.id}
                        elevation="none"
                        padding={3}
                        style={{
                          backgroundColor: 'var(--color-background-muted)',
                          border: '1px solid var(--color-border)',
                        }}
                      >
                        <VStack gap={1}>
                          <HStack justify="between" vAlign="center" gap={2} style={{ flexWrap: 'nowrap' }}>
                            <Text type="label" weight="bold" size="xsm" color="accent">
                              {action.actorName}
                            </Text>
                            <Text type="code" size="xsm" color="secondary" style={{ flexShrink: 0, whiteSpace: 'nowrap' }}>
                              {new Date(action.at).toLocaleString('vi-VN')}
                            </Text>
                          </HStack>

                          <Text type="body" weight="medium">
                            {action.action}
                          </Text>

                          {action.reason && (
                            <VStack
                              gap={0}
                              paddingInline={2}
                              paddingBlock={1}
                              style={{
                                borderLeft: '2px solid var(--color-border-emphasized)',
                              }}
                            >
                              <Text type="supporting" color="secondary">
                                Lý do: {action.reason}
                              </Text>
                            </VStack>
                          )}
                        </VStack>
                      </Card>
                    ))}
                </VStack>
              )}
            </VStack>
          </Card>
        </VStack>
      </Grid>
    </VStack>
  );
}

