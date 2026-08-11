import { useState } from 'react';
import { Maximize2, ShieldAlert, Video, VideoOff } from 'lucide-react';

import { Camera, EVENT_TYPE_LABEL, SecurityEvent } from '../../domain/types';
import { EmptyState } from '../common/States';
import { HealthDot, SimulatedBadge } from '../common/Badges';
import { CameraDetailModal } from './CameraDetailModal';

interface CameraGridProps {
  cameras: Camera[];
  events: SecurityEvent[];
}

/** Event còn "sống" trên camera — dùng để vẽ khung cảnh báo lên tile. */
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
        <p className="font-mono text-xs text-gray-600 dark:text-gray-400">
          <span
            className={healthyCount === cameras.length ? 'font-bold text-emerald-600 dark:text-emerald-400' : 'font-bold text-amber-600 dark:text-amber-400'}
          >
            {healthyCount}/{cameras.length}
          </span>{' '}
          camera hoạt động bình thường
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 content-start md:grid-cols-2 lg:min-h-0 lg:flex-1 lg:overflow-y-auto lg:pr-1 xl:grid-cols-3">
        {cameras.map((camera) => {
          const active = activeFor(camera.id);
          const critical = active?.effectiveSeverity === 'CRITICAL';
          const offline = camera.health === 'OFFLINE';

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
                <HealthDot health={camera.health} />
              </div>

              <div className="relative flex aspect-video items-center justify-center overflow-hidden bg-slate-900">
                {offline ? (
                  <div className="flex flex-col items-center gap-2 text-slate-500">
                    <VideoOff className="h-8 w-8" aria-hidden />
                    <span className="font-mono text-[11px] font-semibold">KHÔNG CÓ TÍN HIỆU</span>
                  </div>
                ) : (
                  <img
                    src={camera.previewUrl}
                    alt=""
                    className="h-full w-full object-cover opacity-85 transition-transform duration-500 group-hover:scale-105"
                  />
                )}

                {/* Lưới radar trang trí */}
                {!offline && (
                  <>
                    <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] opacity-25" />
                    <div className="animate-radar pointer-events-none absolute inset-x-0 h-1 bg-blue-500/40" />
                  </>
                )}

                {/* Khung phát hiện */}
                {active && !offline && (
                  <div
                    className="animate-bbox pointer-events-none absolute flex items-start border-2 border-red-500 bg-red-500/20 p-1 rounded-sm"
                    style={{
                      left: `${((camera.id * 15) % 50) + 10}%`,
                      top: `${((camera.id * 20) % 40) + 15}%`,
                      width: '35%',
                      height: '45%',
                    }}
                  >
                    <span className="rounded bg-red-600 px-1 font-mono text-[9px] font-bold uppercase tracking-wider text-white shadow-sm">
                      {EVENT_TYPE_LABEL[active.eventType]}
                    </span>
                  </div>
                )}

                {/* HUD dưới */}
                <div className="absolute inset-x-0 bottom-0 z-20 flex items-center justify-between gap-2 bg-gradient-to-t from-black/90 to-transparent px-3.5 py-2 font-mono text-[11px] text-gray-300">
                  <span className="truncate">{camera.location}</span>
                  <SimulatedBadge />
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
    </section>
  );
}
