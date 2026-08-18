import { useEffect, useRef, useState } from 'react';
import { Edit3, ShieldAlert, Video, VideoOff } from 'lucide-react';

import { Grid } from '@astryxdesign/core/Grid';
import { Card } from '@astryxdesign/core/Card';
import { HStack, VStack } from '@astryxdesign/core/Stack';
import { Text, Heading } from '@astryxdesign/core/Text';
import { Switch } from '@astryxdesign/core/Switch';
import { Button } from '@astryxdesign/core/Button';
import { AspectRatio } from '@astryxdesign/core/AspectRatio';

import { api } from '../../api';
import { isTrackInZone } from '../../domain/geometry';
import { Camera, CameraZone, SecurityEvent } from '../../domain/types';
import { EmptyState } from '../common/States';
import { HealthDot, SourceBadge } from '../common/Badges';
import { CameraDetailModal } from './CameraDetailModal';
import { ZoneEditorCanvas } from './ZoneEditorCanvas';
import { useEvents } from '../../realtime/EventsProvider';

interface CameraGridProps {
  cameras: Camera[];
  events: SecurityEvent[];
}

const OPEN_STATES = ['OPEN', 'PENDING_REVIEW', 'ACKNOWLEDGED', 'CONFIRMED'];

export function CameraGrid({ cameras, events }: CameraGridProps) {
  const [selected, setSelected] = useState<Camera | null>(null);
  const [editingZoneCamera, setEditingZoneCamera] = useState<Camera | null>(null);
  const [zones, setZones] = useState<CameraZone[]>([]);
  const [devMode, setDevMode] = useState<boolean>(false);
  const { telemetryMap } = useEvents();
  const videoRefs = useRef<Record<number, HTMLVideoElement | null>>({});

  useEffect(() => {
    api.getZones().then(setZones).catch((err) => {
      console.error('Không thể tải cấu hình vùng Intrusion:', err);
    });
  }, []);

  const handleSaveZone = async (zone: CameraZone) => {
    const updated = await api.saveZone(zone);
    setZones((prev) => {
      const idx = prev.findIndex(
        (z) => z.zoneId === updated.zoneId || z.cameraId === updated.cameraId,
      );
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = updated;
        return next;
      }
      return [...prev, updated];
    });
  };

  useEffect(() => {
    if (!devMode) return;
    cameras.forEach((camera) => {
      const video = videoRefs.current[camera.id];
      const telemetry =
        telemetryMap?.[camera.id] ??
        (telemetryMap as Record<string, unknown>)?.[`cam_${camera.id}`] ??
        (telemetryMap as Record<string, unknown>)?.[`cam_0${camera.id}`];
      if (
        video &&
        telemetry &&
        typeof (telemetry as { videoTime?: number }).videoTime === 'number' &&
        video.duration > 0 &&
        !video.paused
      ) {
        const targetTime = ((telemetry as { videoTime: number }).videoTime) % video.duration;
        const diff = Math.abs(video.currentTime - targetTime);
        if (diff > 0.05) {
          video.currentTime = targetTime;
        }
      }
    });
  }, [devMode, telemetryMap, cameras]);

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
            LƯỚI CAMERA ({cameras.length} LUỒNG)
          </Heading>
        </HStack>

        <HStack gap={4} vAlign="center">
          <Switch
            label="Dev Mode (Realtime Bbox)"
            value={devMode}
            onChange={(checked) => setDevMode(checked)}
            size="sm"
          />
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

          const camKey = camera.id <= 9 ? `cam_0${camera.id}` : `cam_${camera.id}`;
          const cameraZone = zones.find(
            (z) => z.cameraId === camKey || z.cameraId === `cam_${camera.id}` || z.cameraId === String(camera.id),
          );

          const telemetry =
            telemetryMap?.[camera.id] ??
            (telemetryMap as any)?.[`cam_${camera.id}`] ??
            (telemetryMap as any)?.[`cam_0${camera.id}`];

          const hasIntrusion = Boolean(
            cameraZone?.polygon &&
            cameraZone.polygon.length >= 3 &&
            cameraZone.enabled !== false &&
            telemetry?.tracks?.some((t: any) => {
              const isLuggage = t.className === 'luggage' || t.className === 'bag' || t.className === 'suitcase';
              return (
                !isLuggage &&
                isTrackInZone(
                  t.bbox,
                  telemetry.frameSize?.[0] || 1280,
                  telemetry.frameSize?.[1] || 720,
                  cameraZone.polygon
                )
              );
            })
          );

          const renderBbox = () => {
            if (!devMode || offline) return null;

            if (telemetry && telemetry.tracks && telemetry.tracks.length > 0) {
              const [frameW, frameH] = telemetry.frameSize || [1280, 720];
              const frameAspect = frameW / frameH;
              const containerAspect = 16 / 9;

              let renderWidthPct = 100;
              let renderHeightPct = 100;
              let offsetXPct = 0;
              let offsetYPct = 0;

              if (frameAspect > containerAspect) {
                renderHeightPct = (containerAspect / frameAspect) * 100;
                offsetYPct = (100 - renderHeightPct) / 2;
              } else if (frameAspect < containerAspect) {
                renderWidthPct = (frameAspect / containerAspect) * 100;
                offsetXPct = (100 - renderWidthPct) / 2;
              }

              return (
                <>
                  {telemetry.tracks.map((track: any) => {
                    const [x1, y1, x2, y2] = track.bbox;
                    const isPercentage = x1 <= 1 && y1 <= 1 && x2 <= 1 && y2 <= 1;

                    const relX1 = isPercentage ? x1 : x1 / frameW;
                    const relY1 = isPercentage ? y1 : y1 / frameH;
                    const relW = isPercentage ? x2 - x1 : (x2 - x1) / frameW;
                    const relH = isPercentage ? y2 - y1 : (y2 - y1) / frameH;

                    const leftPct = offsetXPct + Math.max(0, Math.min(1, relX1)) * renderWidthPct;
                    const topPct = offsetYPct + Math.max(0, Math.min(1, relY1)) * renderHeightPct;
                    const widthPct = Math.max(0, Math.min(100 - leftPct, relW * renderWidthPct));
                    const heightPct = Math.max(0, Math.min(100 - topPct, relH * renderHeightPct));

                    const isLuggage = track.className === 'luggage' || track.className === 'bag' || track.className === 'suitcase';
                    const isPerson = !isLuggage;

                    const inIntrusionZone = isPerson && cameraZone && cameraZone.polygon && cameraZone.polygon.length >= 3 && cameraZone.enabled !== false
                      ? isTrackInZone(track.bbox, frameW, frameH, cameraZone.polygon)
                      : false;

                    const isIntruder = isPerson && inIntrusionZone;
                    const isAbandonedObject = isLuggage && active && active.eventType === 'ABANDONED_OBJECT';

                    let borderColor = '#10b981';
                    let badgeBg = '#059669';
                    let label = `Người #${track.trackId} (${Math.round(track.confidence * 100)}%)`;
                    let extraClass = '';

                    if (isIntruder) {
                      borderColor = '#ef4444';
                      badgeBg = '#dc2626';
                      label = `XÂM NHẬP #${track.trackId} (${Math.round(track.confidence * 100)}%)`;
                      extraClass = 'animate-bbox';
                    } else if (isAbandonedObject) {
                      borderColor = '#f43f5e';
                      badgeBg = '#e11d48';
                      label = `Vật thể bỏ quên #${track.trackId}`;
                      extraClass = 'animate-bbox';
                    } else if (isLuggage) {
                      borderColor = '#f59e0b';
                      badgeBg = '#d97706';
                      label = `Hành lý #${track.trackId}`;
                    }

                    return (
                      <div
                        key={`track-${track.trackId}`}
                        className={extraClass}
                        style={{
                          position: 'absolute',
                          left: `${leftPct}%`,
                          top: `${topPct}%`,
                          width: `${widthPct}%`,
                          height: `${heightPct}%`,
                          border: `2px solid ${borderColor}`,
                          backgroundColor: `color-mix(in srgb, ${borderColor} 20%, transparent)`,
                          borderRadius: 'var(--radius-inner)',
                          zIndex: 30,
                          boxSizing: 'border-box',
                          pointerEvents: 'none',
                        }}
                      >
                        <span
                          style={{
                            position: 'absolute',
                            bottom: 'calc(100% + 2px)',
                            left: 0,
                            backgroundColor: badgeBg,
                            color: '#ffffff',
                            padding: '1px 4px',
                            fontFamily: 'monospace',
                            fontSize: '9px',
                            fontWeight: 700,
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em',
                            borderRadius: 'var(--radius-inner)',
                            boxShadow: '0 1px 2px rgba(0,0,0,0.3)',
                            whiteSpace: 'nowrap',
                            pointerEvents: 'none',
                          }}
                        >
                          {label}
                        </span>
                      </div>
                    );
                  })}
                </>
              );
            }

            return (
              <div
                style={{
                  position: 'absolute',
                  top: '8px',
                  right: '8px',
                  zIndex: 30,
                  borderRadius: 'var(--radius-inner)',
                  backgroundColor: 'rgba(15, 23, 42, 0.85)',
                  border: '1px solid rgba(16, 185, 129, 0.4)',
                  padding: '2px 6px',
                  fontFamily: 'monospace',
                  fontSize: '9px',
                  fontWeight: 500,
                  color: '#34d399',
                  pointerEvents: 'none',
                }}
              >
                DEV: 0 tracks
              </div>
            );
          };

          return (
            <Card
              key={camera.id}
              elevation="low"
              padding={0}
              onClick={() => setSelected(camera)}
            >
              <div
                style={{
                  position: 'relative',
                  overflow: 'hidden',
                  cursor: 'pointer',
                  borderRadius: 'var(--radius-container)',
                  border: critical
                    ? '2px solid var(--color-error)'
                    : active
                    ? '1px solid var(--color-warning)'
                    : '1px solid var(--color-border)',
                }}
              >
                {/* Top HUD */}
                <HStack
                  justify="between"
                  vAlign="center"
                  paddingInline={3}
                  paddingBlock={2}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    zIndex: 20,
                    background: 'linear-gradient(to bottom, rgba(0,0,0,0.8), transparent)',
                  }}
                >
                  <Text type="label" weight="bold" style={{ color: 'white' }}>
                    {camera.name}
                  </Text>
                  <HStack gap={2} vAlign="center">
                    {devMode && (
                      <Button
                        label="Vùng"
                        variant="secondary"
                        size="sm"
                        icon={<Edit3 size={12} />}
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingZoneCamera(camera);
                        }}
                      />
                    )}
                    <HealthDot health={camera.health} />
                  </HStack>
                </HStack>

                {/* Video / Aspect container */}
                <AspectRatio ratio={16 / 9}>
                  <div
                    style={{
                      width: '100%',
                      height: '100%',
                      position: 'relative',
                      backgroundColor: 'var(--color-background-muted)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {offline ? (
                      <VStack gap={2} hAlign="center" vAlign="center">
                        <VideoOff size={32} />
                        <Text type="code" size="xsm" color="secondary">
                          KHÔNG CÓ TÍN HIỆU
                        </Text>
                      </VStack>
                    ) : camera.previewUrl.match(/\.(mp4|webm|avi)(\?.*)?$/i) ? (
                      <video
                        ref={(el) => {
                          videoRefs.current[camera.id] = el;
                        }}
                        src={camera.previewUrl}
                        autoPlay
                        muted
                        loop
                        playsInline
                        style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                      />
                    ) : (
                      <img
                        src={camera.previewUrl}
                        alt=""
                        style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                      />
                    )}

                    {/* Radar animation */}
                    {!offline && <div className="animate-radar" style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }} />}

                    {/* Intrusion zone overlay */}
                    {devMode && cameraZone && cameraZone.polygon && cameraZone.polygon.length >= 3 && (
                      <svg
                        viewBox="0 0 1280 720"
                        preserveAspectRatio="none"
                        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', zIndex: 20, pointerEvents: 'none' }}
                      >
                        <polygon
                          points={cameraZone.polygon.map((p) => `${p[0]},${p[1]}`).join(' ')}
                          fill={hasIntrusion ? 'rgba(239, 68, 68, 0.35)' : 'rgba(245, 158, 11, 0.25)'}
                          stroke={hasIntrusion ? '#ef4444' : '#f59e0b'}
                          strokeWidth="3"
                          strokeDasharray="5 3"
                        />
                        <text
                          x={cameraZone.polygon[0][0] + 5}
                          y={cameraZone.polygon[0][1] + 20}
                          fill={hasIntrusion ? '#ef4444' : '#f59e0b'}
                          fontSize="16"
                          fontWeight="bold"
                          style={{ fontFamily: 'monospace', userSelect: 'none' }}
                        >
                          {hasIntrusion ? `${cameraZone.name} (XÂM NHẬP)` : cameraZone.name}
                        </text>
                      </svg>
                    )}

                    {/* Bounding boxes */}
                    {renderBbox()}
                  </div>
                </AspectRatio>

                {/* Bottom HUD */}
                <HStack
                  justify="between"
                  vAlign="center"
                  paddingInline={3}
                  paddingBlock={2}
                  style={{
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    right: 0,
                    zIndex: 20,
                    background: 'linear-gradient(to top, rgba(0,0,0,0.85), transparent)',
                  }}
                >
                  <Text type="code" size="xsm" style={{ color: 'rgba(255, 255, 255, 0.95)', textShadow: '0 1px 2px rgba(0,0,0,0.8)' }}>
                    {camera.location}
                  </Text>
                  <SourceBadge sourceType={camera.sourceType} />
                </HStack>

                {/* Active alert indicator */}
                {active && (
                  <HStack
                    gap={2}
                    vAlign="center"
                    paddingInline={3}
                    paddingBlock={2}
                    style={{
                      backgroundColor: 'var(--color-error-muted)',
                      borderTop: '1px solid var(--color-error)',
                    }}
                  >
                    <ShieldAlert size={14} color="var(--color-error)" style={{ flexShrink: 0 }} />
                    <Text type="label" size="xsm" weight="semibold" maxLines={1}>
                      {active.description}
                    </Text>
                  </HStack>
                )}
              </div>
            </Card>
          );
        })}
      </Grid>

      {selected && (
        <CameraDetailModal
          camera={selected}
          events={events.filter((event) => event.cameraId === selected.id)}
          onClose={() => setSelected(null)}
        />
      )}

      {editingZoneCamera && (
        <ZoneEditorCanvas
          camera={editingZoneCamera}
          existingZone={zones.find(
            (z) =>
              z.cameraId ===
                (editingZoneCamera.id <= 9 ? `cam_0${editingZoneCamera.id}` : `cam_${editingZoneCamera.id}`) ||
              z.cameraId === `cam_${editingZoneCamera.id}` ||
              z.cameraId === String(editingZoneCamera.id),
          )}
          onSave={handleSaveZone}
          onClose={() => setEditingZoneCamera(null)}
        />
      )}
    </VStack>
  );
}
