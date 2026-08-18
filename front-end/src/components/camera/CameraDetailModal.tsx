import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { VideoOff } from 'lucide-react';

import { Dialog, DialogHeader } from '@astryxdesign/core/Dialog';
import { Card } from '@astryxdesign/core/Card';
import { HStack, VStack } from '@astryxdesign/core/Stack';
import { Text } from '@astryxdesign/core/Text';
import { AspectRatio } from '@astryxdesign/core/AspectRatio';
import { Switch } from '@astryxdesign/core/Switch';

import { api } from '../../api';
import { isTrackInZone } from '../../domain/geometry';
import { Camera, CameraZone, SecurityEvent } from '../../domain/types';
import { EmptyState } from '../common/States';
import { HealthDot, SeverityBadge, SourceBadge, StateBadge } from '../common/Badges';
import { useEvents } from '../../realtime/EventsProvider';

interface CameraDetailModalProps {
  camera: Camera;
  events: SecurityEvent[];
  onClose: () => void;
}

const OPEN_STATES = ['OPEN', 'PENDING_REVIEW', 'ACKNOWLEDGED', 'CONFIRMED'];

/** Chế độ xem chi tiết một camera */
export function CameraDetailModal({ camera, events, onClose }: CameraDetailModalProps) {
  const navigate = useNavigate();
  const [devMode, setDevMode] = useState<boolean>(true);
  const [zones, setZones] = useState<CameraZone[]>([]);
  const { telemetryMap } = useEvents();
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  useEffect(() => {
    api.getZones().then(setZones).catch((err) => {
      console.error('Không thể tải cấu hình vùng Intrusion:', err);
    });
  }, []);

  const camKey = camera.id <= 9 ? `cam_0${camera.id}` : `cam_${camera.id}`;
  const cameraZone = zones.find(
    (z) => z.cameraId === camKey || z.cameraId === `cam_${camera.id}` || z.cameraId === String(camera.id)
  );

  const telemetry =
    telemetryMap?.[camera.id] ??
    (telemetryMap as any)?.[`cam_${camera.id}`] ??
    (telemetryMap as any)?.[`cam_0${camera.id}`];

  useEffect(() => {
    if (!devMode || !videoRef.current || !telemetry) return;
    if (typeof telemetry.videoTime === 'number' && videoRef.current.duration > 0 && !videoRef.current.paused) {
      const targetTime = telemetry.videoTime % videoRef.current.duration;
      const diff = Math.abs(videoRef.current.currentTime - targetTime);
      if (diff > 0.05) {
        videoRef.current.currentTime = targetTime;
      }
    }
  }, [devMode, telemetry]);

  const activeEvent = events.find(
    (event) => event.cameraId === camera.id && OPEN_STATES.includes(event.state)
  );

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
    if (!devMode || camera.health === 'OFFLINE') return null;

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
            const isAbandonedObject = isLuggage && activeEvent && activeEvent.eventType === 'ABANDONED_OBJECT';

            let borderColor = 'border-emerald-500 bg-emerald-500/20';
            let badgeColor = 'bg-emerald-600';
            let label = `Người #${track.trackId} (${Math.round(track.confidence * 100)}%)`;
            let extraClass = '';

            if (isIntruder) {
              borderColor = 'border-red-500 bg-red-500/20';
              badgeColor = 'bg-red-600';
              label = `XÂM NHẬP #${track.trackId} (${Math.round(track.confidence * 100)}%)`;
              extraClass = 'animate-bbox';
            } else if (isAbandonedObject) {
              borderColor = 'border-rose-500 bg-rose-500/20';
              badgeColor = 'bg-rose-600';
              label = `Vật thể bỏ quên #${track.trackId}`;
              extraClass = 'animate-bbox';
            } else if (isLuggage) {
              borderColor = 'border-amber-500 bg-amber-500/20';
              badgeColor = 'bg-amber-600';
              label = `Hành lý #${track.trackId}`;
            }

            return (
              <div
                key={`modal-track-${track.trackId}`}
                className={`pointer-events-none absolute border-2 ${borderColor} rounded-sm z-30 box-border ${extraClass}`}
                style={{
                  left: `${leftPct}%`,
                  top: `${topPct}%`,
                  width: `${widthPct}%`,
                  height: `${heightPct}%`,
                }}
              >
                <span className={`absolute -top-4.5 left-0 rounded ${badgeColor} px-1 font-mono text-[9px] font-bold uppercase tracking-wider text-white shadow-sm whitespace-nowrap pointer-events-none`}>
                  {label}
                </span>
              </div>
            );
          })}
        </>
      );
    }

    return (
      <div className="pointer-events-none absolute top-3 right-3 z-30 rounded bg-slate-900/80 border border-emerald-500/40 px-2 py-1 font-mono text-[10px] font-medium text-emerald-400">
        DEV: 0 đối tượng
      </div>
    );
  };

  return (
    <Dialog
      isOpen={true}
      onOpenChange={(isOpen) => {
        if (!isOpen) onClose();
      }}
      width={840}
      maxHeight="90vh"
      purpose="info"
    >
      <DialogHeader
        title={camera.name}
        subtitle={camera.location}
        endContent={
          <HStack gap={3} vAlign="center">
            <Switch
              label="Hiển thị nhận diện AI"
              value={devMode}
              onChange={(checked) => setDevMode(checked)}
              size="sm"
            />
            <HealthDot health={camera.health} />
            <SourceBadge sourceType={camera.sourceType} />
          </HStack>
        }
        onOpenChange={(isOpen) => {
          if (!isOpen) onClose();
        }}
      />
      <VStack gap={4} padding={4}>
        {/* Video Preview */}
        <AspectRatio ratio={16 / 9}>
          <div
            style={{
              position: 'relative',
              width: '100%',
              height: '100%',
              backgroundColor: 'var(--color-background-body)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 'var(--radius-container)',
              overflow: 'hidden',
              border: '1px solid var(--color-border)',
            }}
          >
            {camera.health === 'OFFLINE' ? (
              <VStack gap={2} hAlign="center" vAlign="center">
                <VideoOff size={36} />
                <Text type="code" size="xsm" color="secondary">
                  CAMERA MẤT KẾT NỐI
                </Text>
              </VStack>
            ) : camera.previewUrl.match(/\.(mp4|webm|avi)(\?.*)?$/i) ? (
              <video
                ref={videoRef}
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

            {/* Intrusion Zone Overlay (hiển thị khi ở Dev Mode) */}
            {devMode && cameraZone && cameraZone.polygon && cameraZone.polygon.length >= 3 && (
              <svg
                viewBox="0 0 1280 720"
                preserveAspectRatio="none"
                style={{
                  position: 'absolute',
                  inset: 0,
                  width: '100%',
                  height: '100%',
                  pointerEvents: 'none',
                  zIndex: 20,
                }}
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

            {/* Khung phát hiện (chỉ hiển thị ở Dev Mode) */}
            {renderBbox()}
          </div>
        </AspectRatio>

        {/* Events list */}
        <VStack gap={3}>
          <Text type="label" weight="bold" color="secondary" size="xsm">
            SỰ CỐ GẦN ĐÂY TRÊN CAMERA NÀY ({events.length})
          </Text>

          {events.length === 0 ? (
            <EmptyState
              title="Chưa ghi nhận sự cố nào"
              hint="Camera đang hoạt động bình thường trong khoảng thời gian đang xem."
            />
          ) : (
            <VStack gap={2}>
              {events.map((event) => (
                <Card
                  key={event.id}
                  elevation="low"
                  padding={3}
                  onClick={() => {
                    onClose();
                    navigate(`/incidents/${event.id}`);
                  }}
                >
                  <VStack gap={1}>
                    <HStack justify="between" vAlign="center" gap={2} style={{ flexWrap: 'nowrap' }}>
                      <HStack gap={1.5} vAlign="center">
                        <SeverityBadge severity={event.effectiveSeverity} />
                        <StateBadge state={event.state} />
                      </HStack>
                      <Text type="code" size="xsm" color="secondary" style={{ flexShrink: 0, whiteSpace: 'nowrap' }}>
                        {new Date(event.detectedAt).toLocaleString('vi-VN')}
                      </Text>
                    </HStack>
                    <Text type="body">
                      {event.description}
                    </Text>
                  </VStack>
                </Card>
              ))}
            </VStack>
          )}
        </VStack>
      </VStack>
    </Dialog>
  );
}
