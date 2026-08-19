import { useState } from 'react';
import { Activity, Maximize2, Video, VideoOff } from 'lucide-react';

import { Grid } from '@astryxdesign/core/Grid';
import { Card } from '@astryxdesign/core/Card';
import { HStack, VStack, StackItem } from '@astryxdesign/core/Stack';
import { Text, Heading } from '@astryxdesign/core/Text';
import { Button } from '@astryxdesign/core/Button';
import { Badge } from '@astryxdesign/core/Badge';
import { AspectRatio } from '@astryxdesign/core/AspectRatio';
import { Table, pixel, proportional } from '@astryxdesign/core/Table';

import { Camera, SecurityEvent } from '../../domain/types';
import { EmptyState } from '../common/States';
import { HealthDot, SeverityBadge, SourceBadge } from '../common/Badges';
import { CameraDetailModal } from './CameraDetailModal';
import { LiveCameraVideo } from './LiveCameraVideo';

interface CameraGridProps {
  cameras: Camera[];
  events: SecurityEvent[];
}

const OPEN_STATES = ['OPEN', 'PENDING_REVIEW', 'ACKNOWLEDGED', 'CONFIRMED'];

export function CameraGrid({ cameras, events }: CameraGridProps) {
  const [selected, setSelected] = useState<Camera | null>(null);

  const activeFor = (cameraId: number) =>
    events.find(
      (event) => event.cameraId === cameraId && OPEN_STATES.includes(event.state),
    );

  const healthyCount = cameras.filter((cam) => cam.health === 'HEALTHY').length;

  if (!cameras.length) {
    return (
      <EmptyState
        icon={<VideoOff size={40} />}
        title="Chưa có camera nào"
        hint="Kiểm tra backend đã seed dữ liệu camera chưa, hoặc bật chế độ mock để xem dữ liệu mẫu."
      />
    );
  }

  return (
    <VStack gap={3} height="100%" as="section" aria-label="Lưới camera giám sát">
      {/* Header toolbar */}
      <HStack justify="between" vAlign="center" wrap="wrap" gap={2}>
        <HStack gap={2} vAlign="center">
          <Video size={18} />
          <Heading level={2}>
            HỆ THỐNG CAMERA ({cameras.length} KÊNH)
          </Heading>
        </HStack>

        <HStack gap={4} vAlign="center">
          <Text type="code" size="xsm" color={healthyCount === cameras.length ? 'primary' : 'secondary'}>
            {healthyCount}/{cameras.length} camera hoạt động
          </Text>
        </HStack>
      </HStack>

      {/* Grid of cameras */}
      <Grid columns={{ minWidth: 320, max: 3 }} gap={3}>
        {cameras.map((camera) => {
          const active = activeFor(camera.id);
          const critical = active?.effectiveSeverity === 'CRITICAL';
          const offline = camera.health === 'OFFLINE';

          return (
            <Card
              key={camera.id}
              elevation={active ? 'high' : 'low'}
              padding={0}
              style={{
                overflow: 'hidden',
                borderRadius: 'var(--radius-container)',
                border: critical
                  ? '2px solid var(--color-error)'
                  : active
                  ? '2px solid var(--color-warning)'
                  : '1px solid var(--color-border)',
                backgroundColor: 'var(--color-background-card)',
                transition: 'all 0.15s ease-in-out',
              }}
            >
              {/* Video container */}
              <div
                style={{
                  position: 'relative',
                  width: '100%',
                  backgroundColor: '#000',
                  cursor: 'pointer',
                }}
                onClick={() => setSelected(camera)}
              >
                <AspectRatio ratio={16 / 9}>
                  {!offline && camera.previewUrl ? (
                    <LiveCameraVideo
                      cameraId={camera.id}
                      src={camera.previewUrl}
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                        display: 'block',
                      }}
                    />
                  ) : (
                    <div
                      style={{
                        width: '100%',
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        backgroundColor: 'var(--color-background-muted)',
                        color: 'var(--color-text-secondary)',
                      }}
                    >
                      <VideoOff size={32} />
                      <Text type="label" size="sm" color="secondary" style={{ marginTop: 'var(--spacing-1)' }}>
                        Mất tín hiệu
                      </Text>
                    </div>
                  )}
                </AspectRatio>

                {/* Overlays */}
                {/* Top left: Camera info */}
                <div
                  style={{
                    position: 'absolute',
                    top: 'var(--spacing-2)',
                    left: 'var(--spacing-2)',
                    zIndex: 10,
                    pointerEvents: 'none',
                  }}
                >
                  <HStack
                    gap={1.5}
                    vAlign="center"
                    style={{
                      backgroundColor: 'rgba(0, 0, 0, 0.75)',
                      padding: '4px 8px',
                      borderRadius: 'var(--radius-inner)',
                      backdropFilter: 'blur(4px)',
                    }}
                  >
                    <HealthDot health={camera.health} />
                    <Text type="code" size="xsm" weight="bold" style={{ color: '#fff' }}>
                      {camera.id <= 9 ? `CAM-0${camera.id}` : `CAM-${camera.id}`}
                    </Text>
                    <Text type="label" size="xsm" style={{ color: '#fff' }}>
                      · {camera.name}
                    </Text>
                  </HStack>
                </div>

                {/* Top right: Active alert badge */}
                {active && (
                  <div
                    style={{
                      position: 'absolute',
                      top: 'var(--spacing-2)',
                      right: 'var(--spacing-2)',
                      zIndex: 10,
                      pointerEvents: 'none',
                    }}
                  >
                    <SeverityBadge severity={active.effectiveSeverity} />
                  </div>
                )}

                {/* Bottom right: Maximize button */}
                <div
                  style={{
                    position: 'absolute',
                    bottom: 'var(--spacing-2)',
                    right: 'var(--spacing-2)',
                    zIndex: 10,
                  }}
                >
                  <Button
                    size="sm"
                    variant="ghost"
                    icon={<Maximize2 size={14} />}
                    label="Phóng to"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelected(camera);
                    }}
                    style={{
                      backgroundColor: 'rgba(0, 0, 0, 0.6)',
                      color: 'var(--color-text-inverted)',
                    }}
                  />
                </div>
              </div>

              {/* Card Footer */}
              <div style={{ padding: 'var(--spacing-2) var(--spacing-3)' }}>
                <HStack justify="between" vAlign="center">
                  <Text type="supporting" size="xsm" color="secondary">
                    {camera.location}
                  </Text>
                  <SourceBadge sourceType={camera.sourceType} />
                </HStack>
              </div>
            </Card>
          );
        })}
      </Grid>

      {/* Summary KPI Cards */}
      <VStack gap={3}>
        <Grid columns={{ minWidth: 240, max: 3 }} gap={3}>
          <Card elevation="low" padding={3}>
            <VStack gap={1}>
              <HStack justify="between" vAlign="center">
                <Text type="supporting" size="xsm" color="secondary">
                  KÊNH TRỰC TUYẾN
                </Text>
                <Badge variant={healthyCount === cameras.length ? 'success' : 'warning'} label={`${healthyCount}/${cameras.length}`} />
              </HStack>
              <Text type="label" size="lg" weight="bold">
                {healthyCount} Kênh hoạt động
              </Text>
              <Text type="supporting" size="xsm" color="secondary">
                Tất cả camera được giám sát liên tục 24/7
              </Text>
            </VStack>
          </Card>

          <Card elevation="low" padding={3}>
            <VStack gap={1}>
              <HStack justify="between" vAlign="center">
                <Text type="supporting" size="xsm" color="secondary">
                  TRẠNG THÁI HỆ THỐNG
                </Text>
                <HealthDot health={healthyCount === cameras.length ? 'HEALTHY' : 'DEGRADED'} />
              </HStack>
              <Text type="label" size="lg" weight="bold">
                {healthyCount === cameras.length ? 'Hoạt động ổn định' : 'Có kênh gặp sự cố'}
              </Text>
              <Text type="supporting" size="xsm" color="secondary">
                {cameras.filter((c) => c.health === 'OFFLINE').length} kênh mất tín hiệu
              </Text>
            </VStack>
          </Card>

          <Card elevation="low" padding={3}>
            <VStack gap={1}>
              <HStack justify="between" vAlign="center">
                <Text type="supporting" size="xsm" color="secondary">
                  SỰ CỐ CẦN THEO DÕI
                </Text>
                <Activity size={16} color="var(--color-warning)" />
              </HStack>
              <Text type="label" size="lg" weight="bold" color={events.filter((e) => OPEN_STATES.includes(e.state)).length > 0 ? 'accent' : 'primary'}>
                {events.filter((e) => OPEN_STATES.includes(e.state)).length} Sự cố chưa xử lý
              </Text>
              <Text type="supporting" size="xsm" color="secondary">
                {events.filter((e) => OPEN_STATES.includes(e.state) && e.effectiveSeverity === 'CRITICAL').length} khẩn cấp · Cần xử lý
              </Text>
            </VStack>
          </Card>
        </Grid>

        {/* Camera Channel Details Table */}
        <Card elevation="low" padding={3}>
          <VStack gap={2} style={{ width: '100%', minWidth: 0 }}>
            <Text type="label" weight="bold">
              DANH SÁCH CAMERA GIÁM SÁT
            </Text>
            <StackItem size="fill" isScrollable style={{ minWidth: 0, width: '100%' }}>
              <Table<Camera>
                density="balanced"
                hasHover
                data={cameras}
                idKey="id"
                columns={[
                  {
                    key: 'id',
                    header: 'Mã & Tên Camera',
                    width: pixel(200),
                    renderCell: (cam) => (
                      <HStack gap={2} vAlign="center">
                        <Text type="code" size="xsm" weight="bold" color="accent">
                          {cam.id <= 9 ? `CAM-0${cam.id}` : `CAM-${cam.id}`}
                        </Text>
                        <Text type="label" weight="semibold">
                          {cam.name}
                        </Text>
                      </HStack>
                    ),
                  },
                  {
                    key: 'location',
                    header: 'Vị trí lắp đặt',
                    width: proportional(1, { minWidth: 180 }),
                    renderCell: (cam) => (
                      <Text type="body" size="xsm">
                        {cam.location}
                      </Text>
                    ),
                  },
                  {
                    key: 'health',
                    header: 'Tín hiệu',
                    width: pixel(140),
                    renderCell: (cam) => (
                      <HStack gap={1.5} vAlign="center">
                        <HealthDot health={cam.health} />
                        <Text type="label" size="xsm">
                          {cam.health === 'HEALTHY'
                            ? 'Trực tuyến'
                            : cam.health === 'DEGRADED'
                            ? 'Chập chờn'
                            : 'Mất kết nối'}
                        </Text>
                      </HStack>
                    ),
                  },
                  {
                    key: 'sourceType',
                    header: 'Loại nguồn',
                    width: pixel(130),
                    renderCell: (cam) => <SourceBadge sourceType={cam.sourceType} />,
                  },
                  {
                    key: 'actions',
                    header: 'Thao tác',
                    width: pixel(120),
                    renderCell: (cam) => (
                      <Button
                        size="sm"
                        variant="secondary"
                        icon={<Maximize2 size={12} />}
                        label="Phóng to"
                        onClick={() => setSelected(cam)}
                      />
                    ),
                  },
                ]}
              />
            </StackItem>
          </VStack>
        </Card>
      </VStack>

      {selected && (
        <CameraDetailModal
          camera={selected}
          events={events.filter((event) => event.cameraId === selected.id)}
          onClose={() => setSelected(null)}
        />
      )}
    </VStack>
  );
}
