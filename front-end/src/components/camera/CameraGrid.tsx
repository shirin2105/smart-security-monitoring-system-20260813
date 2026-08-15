import { useEffect, useRef, useState } from 'react';
import { Edit3, Maximize2, ShieldAlert, Video, VideoOff } from 'lucide-react';

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

/** Event còn "sống" trên camera — dùng để vẽ khung cảnh báo lên tile. */
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
        (z) => z.zoneId === updated.zoneId || z.cameraId === updated.cameraId
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
      const telemetry = telemetryMap?.[camera.id] ?? (telemetryMap as any)?.[`cam_${camera.id}`] ?? (telemetryMap as any)?.[`cam_0${camera.id}`];
      if (video && telemetry && typeof telemetry.videoTime === 'number' && video.duration > 0 && !video.paused) {
        const targetTime = telemetry.videoTime % video.duration;
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
      <div className="flex flex-1 items-center justify-center rounded-2xl border border-gray-200 dark:border-gray-800 bg-white/50 dark:bg-gray-900/40 backdrop-blur-sm">
        <EmptyState
          icon={<VideoOff className="h-10 w-10 text-gray-400" />}
          title="Chưa có camera nào"
          hint="Kiểm tra backend đã seed dữ liệu camera chưa, hoặc bật chế độ mock để xem dữ liệu mẫu."
        />
      </div>
    );
  }

  return (
    <section className="flex flex-col lg:min-h-0 lg:flex-1" aria-label="Lưới camera giám sát">
      <div className="mb-3.5 flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-gray-900 dark:text-gray-200">
          <Video className="h-4 w-4 text-blue-600 dark:text-blue-400" aria-hidden />
          Lưới camera ({cameras.length} luồng)
        </h2>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-xs font-semibold cursor-pointer text-gray-700 dark:text-gray-300">
            <input
              type="checkbox"
              checked={devMode}
              onChange={(e) => setDevMode(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className={devMode ? 'text-amber-600 dark:text-amber-400 font-bold' : ''}>
              Dev Mode (BBox Debug)
            </span>
          </label>
          <p className="font-mono text-xs text-gray-600 dark:text-gray-400">
            <span
              className={healthyCount === cameras.length ? 'font-bold text-emerald-600 dark:text-emerald-400' : 'font-bold text-amber-600 dark:text-amber-400'}
            >
              {healthyCount}/{cameras.length}
            </span>{' '}
            camera hoạt động bình thường
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 content-start md:grid-cols-2 lg:min-h-0 lg:flex-1 lg:overflow-y-auto lg:pr-1 xl:grid-cols-3">
        {cameras.map((camera) => {
          const active = activeFor(camera.id);
          const critical = active?.effectiveSeverity === 'CRITICAL';
          const offline = camera.health === 'OFFLINE';

          const camKey = camera.id <= 9 ? `cam_0${camera.id}` : `cam_${camera.id}`;
          const cameraZone = zones.find(
            (z) => z.cameraId === camKey || z.cameraId === `cam_${camera.id}` || z.cameraId === String(camera.id)
          );

          const telemetry = telemetryMap?.[camera.id] ?? (telemetryMap as any)?.[`cam_${camera.id}`] ?? (telemetryMap as any)?.[`cam_0${camera.id}`];

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

          // Helper format bbox coords [x1, y1, x2, y2]
          const renderBbox = () => {
            if (!devMode || offline) return null;

            // Dùng telemetry realtime từ luồng CV (hiển thị tất cả đối tượng trong camera tại mọi thời điểm)
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
                    const isAbandonedObject = isLuggage && active && active.eventType === 'ABANDONED_OBJECT';

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
                        key={`track-${track.trackId}`}
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

            // Dev mode active indicator khi không có track
            return (
              <div className="pointer-events-none absolute top-2 right-2 z-30 rounded bg-slate-900/80 border border-emerald-500/40 px-1.5 py-0.5 font-mono text-[9px] font-medium text-emerald-400">
                DEV: 0 tracks
              </div>
            );
          };

          return (
            <button
              key={camera.id}
              onClick={() => setSelected(camera)}
              aria-label={`Xem chi tiết ${camera.name}`}
              className={`group relative flex flex-col justify-between overflow-hidden rounded-2xl border text-left transition-all shadow-sm card-elevation focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 h-fit ${
                critical
                  ? 'border-rose-400 dark:border-red-500 bg-rose-50/90 dark:bg-red-950/40 ring-2 ring-rose-500/50'
                  : active
                    ? 'border-amber-400 dark:border-amber-500/60 bg-amber-50/90 dark:bg-gray-900/90'
                    : 'border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/60 hover:border-blue-400 dark:hover:border-blue-500/50'
              }`}
            >
              {/* HUD trên */}
              <div className="absolute inset-x-0 top-0 z-20 flex items-center justify-between gap-2 bg-gradient-to-b from-black/80 to-transparent px-3.5 py-2.5">
                <span className="truncate font-mono text-xs font-bold tracking-wider text-white drop-shadow-sm">
                  {camera.name}
                </span>
                <div className="flex items-center gap-2">
                  {devMode && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingZoneCamera(camera);
                      }}
                      className="flex items-center gap-1 rounded bg-amber-600/90 px-2 py-0.5 text-[10px] font-bold text-white shadow hover:bg-amber-500"
                      title="Thiết lập vùng Intrusion"
                    >
                      <Edit3 className="h-3 w-3" />
                      <span>Vùng Intrusion</span>
                    </button>
                  )}
                  <HealthDot health={camera.health} />
                </div>
              </div>

              <div className="relative flex aspect-video items-center justify-center overflow-hidden bg-slate-900">
                {offline ? (
                  <div className="flex flex-col items-center gap-2 text-slate-500">
                    <VideoOff className="h-8 w-8" aria-hidden />
                    <span className="font-mono text-[11px] font-semibold">KHÔNG CÓ TÍN HIỆU</span>
                  </div>
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
                    className="h-full w-full object-contain opacity-85 transition-transform duration-500"
                  />
                ) : (
                  <img
                    src={camera.previewUrl}
                    alt=""
                    className="h-full w-full object-contain opacity-85 transition-transform duration-500"
                  />
                )}

                {/* Lưới radar trang trí */}
                {!offline && (
                  <>
                    <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] opacity-25" />
                    <div className="animate-radar pointer-events-none absolute inset-x-0 h-1 bg-blue-500/40" />
                  </>
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
                {/* HUD dưới */}
                <div className="absolute inset-x-0 bottom-0 z-20 flex items-center justify-between gap-2 bg-gradient-to-t from-black/90 to-transparent px-3.5 py-2 font-mono text-[11px] text-gray-300">
                  <span className="truncate">{camera.location}</span>
                  <SourceBadge sourceType={camera.sourceType} />
                </div>

                <div className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center gap-2 bg-blue-900/40 backdrop-blur-[2px] text-xs font-semibold text-white opacity-0 transition-opacity group-hover:opacity-100">
                  <Maximize2 className="h-4 w-4" aria-hidden />
                  <span>Xem chi tiết</span>
                </div>
              </div>

              {active && (
                <div className="flex items-center gap-2 border-t border-rose-200 dark:border-red-500/40 bg-rose-50 dark:bg-red-950/80 p-2.5 text-xs text-rose-800 dark:text-red-300">
                  <ShieldAlert className="h-4 w-4 shrink-0 text-rose-600 dark:text-red-400" aria-hidden />
                  <span className="truncate font-semibold">{active.description}</span>
                </div>
              )}
            </button>
          );
        })}
      </div>

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
              z.cameraId === (editingZoneCamera.id <= 9 ? `cam_0${editingZoneCamera.id}` : `cam_${editingZoneCamera.id}`) ||
              z.cameraId === `cam_${editingZoneCamera.id}` ||
              z.cameraId === String(editingZoneCamera.id)
          )}
          onSave={handleSaveZone}
          onClose={() => setEditingZoneCamera(null)}
        />
      )}
    </section>
  );
}
