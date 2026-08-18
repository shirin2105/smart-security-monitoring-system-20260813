import { useState } from 'react';
import {
  AlertTriangle,
  Building2,
  Camera as CameraIcon,
  Flame,
  Map as MapIcon,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';

import { Card } from '@astryxdesign/core/Card';
import { SelectableCard } from '@astryxdesign/core/SelectableCard';
import { Grid } from '@astryxdesign/core/Grid';
import { HStack, VStack } from '@astryxdesign/core/Stack';
import { Text, Heading } from '@astryxdesign/core/Text';
import { Token } from '@astryxdesign/core/Token';
import { StatusDot } from '@astryxdesign/core/StatusDot';
import { ProgressBar } from '@astryxdesign/core/ProgressBar';
import { AspectRatio } from '@astryxdesign/core/AspectRatio';

import { api } from '../api';
import { HealthDot, SeverityBadge, StateBadge } from '../components/common/Badges';
import { ErrorState, LoadingState } from '../components/common/States';
import { Camera } from '../domain/types';
import { useAsync } from '../hooks/useAsync';
import { useEvents } from '../realtime/EventsProvider';

interface Zone {
  id: string;
  name: string;
  code: string;
  riskScore: number;
  status: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  cameraCount: number;
  activeIncidents: number;
  coordinates: { x: number; y: number; width: number; height: number };
}

const ZONES: Zone[] = [
  {
    id: 'z1',
    name: 'Cổng Chính & Trạm Kiểm Soát',
    code: 'ZONE-A',
    riskScore: 85,
    status: 'CRITICAL',
    cameraCount: 2,
    activeIncidents: 3,
    coordinates: { x: 60, y: 60, width: 320, height: 160 },
  },
  {
    id: 'z2',
    name: 'Bãi Xe Nhân Viên & Khách',
    code: 'ZONE-B',
    riskScore: 62,
    status: 'HIGH',
    cameraCount: 2,
    activeIncidents: 1,
    coordinates: { x: 420, y: 60, width: 320, height: 160 },
  },
  {
    id: 'z3',
    name: 'Sảnh Trung Tâm & Lễ Tân',
    code: 'ZONE-C',
    riskScore: 35,
    status: 'MEDIUM',
    cameraCount: 1,
    activeIncidents: 0,
    coordinates: { x: 60, y: 240, width: 320, height: 150 },
  },
  {
    id: 'z4',
    name: 'Khu Vực Kho Vận & Xuất Hàng',
    code: 'ZONE-D',
    riskScore: 18,
    status: 'LOW',
    cameraCount: 1,
    activeIncidents: 0,
    coordinates: { x: 420, y: 240, width: 320, height: 150 },
  },
];

const ZONE_STATUS_TOKEN_COLOR: Record<Zone['status'], 'red' | 'orange' | 'cyan' | 'green'> = {
  CRITICAL: 'red',
  HIGH: 'orange',
  MEDIUM: 'cyan',
  LOW: 'green',
};

const ZONE_PROGRESS_VARIANT: Record<Zone['status'], 'error' | 'warning' | 'accent' | 'success'> = {
  CRITICAL: 'error',
  HIGH: 'warning',
  MEDIUM: 'accent',
  LOW: 'success',
};

const ZONE_COLOR_MAP: Record<Zone['status'], string> = {
  CRITICAL: 'var(--color-error)',
  HIGH: 'var(--color-warning)',
  MEDIUM: 'var(--color-accent)',
  LOW: 'var(--color-success)',
};

export function HeatmapPage() {
  const { events, revision } = useEvents();
  const camerasRes = useAsync(() => api.getCameras(), [revision]);
  const [selectedZoneId, setSelectedZoneId] = useState<string>('z1');

  if (camerasRes.loading && !camerasRes.data) {
    return <LoadingState label="Đang tải bản đồ điểm nóng an ninh…" />;
  }

  if (camerasRes.error != null) {
    return <ErrorState error={camerasRes.error} onRetry={camerasRes.reload} />;
  }

  const cameras = camerasRes.data ?? [];
  const selectedZone = ZONES.find((z) => z.id === selectedZoneId) || ZONES[0];

  const getZoneCameras = (zoneCode: string): Camera[] => {
    if (zoneCode === 'ZONE-A') return cameras.slice(0, 2);
    if (zoneCode === 'ZONE-B') return cameras.slice(2, 4);
    if (zoneCode === 'ZONE-C') return cameras.slice(4, 5);
    return cameras.slice(5);
  };

  const selectedZoneCameras = getZoneCameras(selectedZone.code);
  const selectedZoneCameraIds = selectedZoneCameras.map((c) => c.id);
  const selectedZoneEvents = events.filter((e) => selectedZoneCameraIds.includes(e.cameraId));

  const totalIncidents = events.filter((e) => ['OPEN', 'ACKNOWLEDGED', 'PENDING_REVIEW'].includes(e.state)).length;

  return (
    <VStack gap={4} padding={4} height="100%" isScrollable>
      {/* Header */}
      <HStack justify="between" vAlign="center" wrap="wrap" gap={3}>
        <HStack gap={2} vAlign="center">
          <MapIcon size={20} />
          <VStack gap={0.5}>
            <Heading level={1}>
              BẢN ĐỒ ĐIỂM NÓNG AN NINH
            </Heading>
            <Text type="supporting" size="xsm" color="secondary">
              Phân tích chỉ số mật độ rủi ro & nhiệt độ sự cố theo vùng mặt bằng
            </Text>
          </VStack>
        </HStack>

        <HStack gap={3} vAlign="center">
          <Card elevation="none" padding={2} style={{ backgroundColor: 'var(--color-background-muted)' }}>
            <HStack gap={1.5} vAlign="center">
              <Flame size={14} color="var(--color-error)" />
              <Text type="supporting" size="xsm" color="secondary">
                Rủi ro cao nhất:
              </Text>
              <Text type="label" size="xsm" weight="bold" color="accent">
                ZONE-A (85%)
              </Text>
            </HStack>
          </Card>

          <Card elevation="none" padding={2} style={{ backgroundColor: 'var(--color-background-muted)' }}>
            <HStack gap={1.5} vAlign="center">
              <ShieldAlert size={14} color="var(--color-warning)" />
              <Text type="supporting" size="xsm" color="secondary">
                Cảnh báo mở:
              </Text>
              <Text type="label" size="xsm" weight="bold">
                {totalIncidents} sự cố
              </Text>
            </HStack>
          </Card>
        </HStack>
      </HStack>

      {/* Grid Zone Metric Cards */}
      <Grid columns={{ minWidth: 220, max: 4 }} gap={3}>
        {ZONES.map((zone) => {
          const isSelected = zone.id === selectedZoneId;
          return (
            <SelectableCard
              key={zone.id}
              label={zone.name}
              isSelected={isSelected}
              onChange={() => setSelectedZoneId(zone.id)}
              padding={3}
            >
              <VStack gap={2}>
                <HStack justify="between" vAlign="center">
                  <Text type="code" size="xsm" weight="bold" color="secondary">
                    {zone.code}
                  </Text>
                  <Token
                    size="sm"
                    color={ZONE_STATUS_TOKEN_COLOR[zone.status]}
                    label={zone.status}
                  />
                </HStack>

                <Text type="body" weight="bold" size="xsm" maxLines={1}>
                  {zone.name}
                </Text>

                <VStack gap={1}>
                  <HStack justify="between" vAlign="center">
                    <Text type="supporting" color="secondary">
                      Chỉ số nhiệt:
                    </Text>
                    <Text type="code" size="xsm" weight="bold">
                      {zone.riskScore}/100
                    </Text>
                  </HStack>
                  <ProgressBar
                    label={`Nhiệt độ ${zone.code}`}
                    isLabelHidden
                    value={zone.riskScore}
                    max={100}
                    variant={ZONE_PROGRESS_VARIANT[zone.status]}
                  />
                </VStack>
              </VStack>
            </SelectableCard>
          );
        })}
      </Grid>

      {/* Map + Detail Panel */}
      <Grid columns={{ minWidth: 360, max: 2 }} gap={4}>
        {/* Floorplan Map Card */}
        <Card elevation="low" padding={4}>
          <VStack gap={3} height="100%">
            <HStack justify="between" vAlign="center" wrap="wrap" gap={2}>
              <HStack gap={1.5} vAlign="center">
                <Building2 size={16} />
                <Heading level={2}>
                  SƠ ĐỒ MẶT BẰNG TÒA NHÀ
                </Heading>
              </HStack>
              <HStack gap={3} vAlign="center" style={{ flexWrap: 'nowrap' }}>
                <HStack gap={1} vAlign="center">
                  <StatusDot variant="error" label="Nguy hiểm" />
                  <Text type="label" size="xsm">Nguy hiểm</Text>
                </HStack>
                <HStack gap={1} vAlign="center">
                  <StatusDot variant="warning" label="Rủi ro" />
                  <Text type="label" size="xsm">Rủi ro</Text>
                </HStack>
                <HStack gap={1} vAlign="center">
                  <StatusDot variant="success" label="An toàn" />
                  <Text type="label" size="xsm">An toàn</Text>
                </HStack>
              </HStack>
            </HStack>

            <AspectRatio ratio={16 / 9}>
              <svg
                viewBox="0 0 800 450"
                style={{
                  width: '100%',
                  height: '100%',
                  backgroundColor: 'var(--color-background-body)',
                  borderRadius: 'var(--radius-container)',
                  border: '1px solid var(--color-border)',
                }}
              >
                {/* Background Grid Lines */}
                <defs>
                  <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="var(--color-border)" strokeWidth="0.5" />
                  </pattern>
                </defs>
                <rect width="800" height="450" fill="url(#grid)" />

                {/* Building Outer Wall */}
                <rect
                  x="40"
                  y="40"
                  width="720"
                  height="370"
                  fill="none"
                  stroke="var(--color-border-emphasized)"
                  strokeWidth="3"
                  rx="6"
                />

                {/* Zones Polygon / Rects */}
                {ZONES.map((zone) => {
                  const isSelected = zone.id === selectedZoneId;
                  const { x, y, width: w, height: h } = zone.coordinates;
                  const color = ZONE_COLOR_MAP[zone.status];

                  return (
                    <g
                      key={zone.id}
                      onClick={() => setSelectedZoneId(zone.id)}
                      style={{ cursor: 'pointer' }}
                    >
                      {/* Zone Area Fill with Heatmap Tint */}
                      <rect
                        x={x}
                        y={y}
                        width={w}
                        height={h}
                        fill={color}
                        fillOpacity={isSelected ? 0.35 : 0.18}
                        stroke={color}
                        strokeWidth={isSelected ? 3 : 1.5}
                        strokeDasharray={isSelected ? 'none' : '4 2'}
                        rx="4"
                      />

                      {/* Zone Label & Indicator */}
                      <rect
                        x={x + 8}
                        y={y + 8}
                        width={70}
                        height={24}
                        rx="4"
                        fill="var(--color-background-surface)"
                        fillOpacity={0.9}
                      />
                      <text
                        x={x + 16}
                        y={y + 24}
                        fill="var(--color-text-primary)"
                        fontSize="12"
                        fontWeight="bold"
                        fontFamily="monospace"
                      >
                        {zone.code}
                      </text>

                      {/* Heat pulse center */}
                      <circle
                        cx={x + w / 2}
                        cy={y + h / 2}
                        r={zone.riskScore / 3}
                        fill={color}
                        fillOpacity="0.2"
                      />
                      <circle
                        cx={x + w / 2}
                        cy={y + h / 2}
                        r="6"
                        fill={color}
                      />
                    </g>
                  );
                })}
              </svg>
            </AspectRatio>
          </VStack>
        </Card>

        {/* Selected Zone Detail */}
        <Card elevation="low" padding={4}>
          <VStack gap={4}>
            {/* Zone header */}
            <VStack gap={0.5}>
              <HStack justify="between" vAlign="center">
                <Text type="code" size="sm" weight="bold" color="secondary">
                  {selectedZone.code}
                </Text>
                <Token
                  size="sm"
                  color={ZONE_STATUS_TOKEN_COLOR[selectedZone.status]}
                  label={`Mức ${selectedZone.status}`}
                />
              </HStack>
              <Heading level={2}>
                {selectedZone.name}
              </Heading>
            </VStack>


            {/* Cameras assigned */}
            <VStack gap={2}>
              <HStack gap={1.5} vAlign="center">
                <CameraIcon size={14} />
                <Text type="label" weight="bold" color="secondary">
                  CAMERA THEO VÙNG ({selectedZoneCameras.length})
                </Text>
              </HStack>
              <VStack gap={2}>
                {selectedZoneCameras.map((cam) => (
                  <Card
                    key={cam.id}
                    elevation="none"
                    padding={3}
                    style={{
                      backgroundColor: 'var(--color-background-muted)',
                      border: '1px solid var(--color-border)',
                    }}
                  >
                    <HStack justify="between" vAlign="center">
                      <VStack gap={0}>
                        <Text type="label" weight="semibold">
                          {cam.name}
                        </Text>
                        <Text type="supporting" color="secondary">
                          {cam.location}
                        </Text>
                      </VStack>
                      <HealthDot health={cam.health} />
                    </HStack>
                  </Card>
                ))}
              </VStack>
            </VStack>

            {/* Active events */}
            <VStack gap={2}>
              <HStack gap={1.5} vAlign="center">
                <AlertTriangle size={14} />
                <Text type="label" weight="bold" color="secondary">
                  SỰ CỐ ĐANG PHÁT HIỆN ({selectedZoneEvents.length})
                </Text>
              </HStack>
              {selectedZoneEvents.length === 0 ? (
                <Card elevation="none" padding={3} style={{ backgroundColor: 'var(--color-background-muted)' }}>
                  <VStack gap={1} hAlign="center" vAlign="center">
                    <ShieldCheck size={24} color="var(--color-success)" />
                    <Text type="label" weight="semibold">
                      Vùng an toàn
                    </Text>
                    <Text type="supporting" color="secondary">
                      Chưa ghi nhận sự cố bất thường trong vùng này.
                    </Text>
                  </VStack>
                </Card>
              ) : (
                <VStack gap={2}>
                  {selectedZoneEvents.map((evt) => (
                    <Card
                      key={evt.id}
                      elevation="none"
                      padding={3}
                      style={{
                        backgroundColor: 'var(--color-background-muted)',
                        border: '1px solid var(--color-border)',
                      }}
                    >
                      <VStack gap={1}>
                        <HStack justify="between" vAlign="center">
                          <SeverityBadge severity={evt.effectiveSeverity} />
                          <StateBadge state={evt.state} />
                        </HStack>
                        <Text type="body">
                          {evt.description}
                        </Text>
                      </VStack>
                    </Card>
                  ))}
                </VStack>
              )}
            </VStack>
          </VStack>
        </Card>
      </Grid>
    </VStack>
  );
}
