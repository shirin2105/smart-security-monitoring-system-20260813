import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { VideoOff, X } from 'lucide-react';

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

/** Chế độ xem chi tiết một camera — acceptance criteria của BAC-50. */
export function CameraDetailModal({ camera, events, onClose }: CameraDetailModalProps) {
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
    telemetry?.tracks?.some((t) => {
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
          {telemetry.tracks.map((track) => {
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
        DEV MODE: 0 tracks
      </div>
    );
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 dark:bg-black/90 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="camera-detail-title"
    >
      <div className="glass-panel flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-2xl">
        <div className="flex items-center justify-between gap-3 border-b border-gray-200 dark:border-gray-800 bg-slate-50 dark:bg-gray-950 px-6 py-4">
          <div className="min-w-0">
            <h3 id="camera-detail-title" className="truncate text-base font-bold text-gray-900 dark:text-white">
              {camera.name}
            </h3>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{camera.location}</span>
              <HealthDot health={camera.health} />
              <SourceBadge sourceType={camera.sourceType} />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-xs font-semibold cursor-pointer text-gray-700 dark:text-gray-300">
              <input
                type="checkbox"
                checked={devMode}
                onChange={(e) => setDevMode(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className={devMode ? 'text-amber-600 dark:text-amber-400 font-bold' : ''}>
                Dev Mode
              </span>
            </label>
            <button
              onClick={onClose}
              className="rounded-lg bg-gray-100 dark:bg-gray-800 p-2 text-gray-500 dark:text-gray-400 transition-colors hover:bg-gray-200 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              aria-label="Đóng"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          </div>
        </div>

        <div className="relative flex aspect-video shrink-0 max-h-[50vh] items-center justify-center overflow-hidden bg-slate-950">
          {camera.health === 'OFFLINE' ? (
            <div className="flex flex-col items-center gap-2 text-slate-500">
              <VideoOff className="h-10 w-10" aria-hidden />
              <span className="font-mono text-xs font-semibold">CAMERA MẤT KẾT NỐI</span>
            </div>
          ) : camera.previewUrl.match(/\.(mp4|webm|avi)(\?.*)?$/i) ? (
            <video
              ref={videoRef}
              src={camera.previewUrl}
              autoPlay
              muted
              loop
              playsInline
              className="h-full w-full object-contain"
            />
          ) : (
            <img src={camera.previewUrl} alt="" className="h-full w-full object-contain" />
          )}

          {/* Intrusion Zone Overlay (hiển thị khi ở Dev Mode) */}
          {devMode && cameraZone && cameraZone.polygon && cameraZone.polygon.length >= 3 && (
            <svg
              viewBox="0 0 1280 720"
              preserveAspectRatio="none"
              className="pointer-events-none absolute inset-0 h-full w-full z-20"
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
                className="font-mono drop-shadow-md select-none"
              >
                {hasIntrusion ? `${cameraZone.name} (XÂM NHẬP)` : cameraZone.name}
              </text>
            </svg>
          )}

          {/* Khung phát hiện (chỉ hiển thị ở Dev Mode) */}
          {renderBbox()}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-6">
          <h4 className="mb-3 font-mono text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-400">
            Sự cố gần đây trên camera này
          </h4>

          {events.length === 0 ? (
            <EmptyState
              title="Chưa ghi nhận sự cố nào"
              hint="Camera đang hoạt động bình thường trong khoảng thời gian đang xem."
            />
          ) : (
            <ul className="space-y-2.5">
              {events.map((event) => (
                <li key={event.id}>
                  <Link
                    to={`/incidents/${event.id}`}
                    onClick={onClose}
                    className="block rounded-xl border border-gray-200 dark:border-gray-800 bg-slate-50/80 dark:bg-gray-950/70 p-3.5 transition-all hover:border-blue-400 dark:hover:border-blue-500/40 hover:bg-slate-100 dark:hover:bg-gray-900 shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  >
                    <div className="mb-1.5 flex flex-wrap items-center gap-2">
                      <SeverityBadge severity={event.effectiveSeverity} />
                      <StateBadge state={event.state} />
                      <span className="ml-auto font-mono text-[11px] text-gray-500 dark:text-gray-400">
                        {new Date(event.detectedAt).toLocaleString('vi-VN')}
                      </span>
                    </div>
                    <p className="text-xs leading-relaxed text-gray-800 dark:text-gray-300">
                      {event.description}
                    </p>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
