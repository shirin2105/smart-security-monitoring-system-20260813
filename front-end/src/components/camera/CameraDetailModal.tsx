import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { VideoOff, X } from 'lucide-react';

import { Camera, SecurityEvent } from '../../domain/types';
import { EmptyState } from '../common/States';
import { HealthDot, SeverityBadge, SimulatedBadge, StateBadge } from '../common/Badges';

interface CameraDetailModalProps {
  camera: Camera;
  events: SecurityEvent[];
  onClose: () => void;
}

/** Chế độ xem chi tiết một camera — acceptance criteria của BAC-50. */
export function CameraDetailModal({ camera, events, onClose }: CameraDetailModalProps) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4 backdrop-blur-md"
      role="dialog"
      aria-modal="true"
      aria-labelledby="camera-detail-title"
    >
      <div className="glass-panel flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-gray-800 bg-gray-900">
        <div className="flex items-center justify-between gap-3 border-b border-gray-800 bg-gray-950 px-5 py-4">
          <div className="min-w-0">
            <h3 id="camera-detail-title" className="truncate text-base font-bold text-white">
              {camera.name}
            </h3>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <span className="text-xs text-gray-400">{camera.location}</span>
              <HealthDot health={camera.health} />
              <SimulatedBadge />
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg bg-gray-800 p-2 text-gray-400 transition-colors hover:bg-gray-700 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            aria-label="Đóng"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>

        <div className="relative flex aspect-video shrink-0 items-center justify-center overflow-hidden bg-black">
          {camera.health === 'OFFLINE' ? (
            <div className="flex flex-col items-center gap-2 text-gray-600">
              <VideoOff className="h-10 w-10" aria-hidden />
              <span className="font-mono text-xs">CAMERA MẤT KẾT NỐI</span>
            </div>
          ) : (
            <img src={camera.previewUrl} alt="" className="h-full w-full object-cover" />
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-5">
          <h4 className="mb-3 font-mono text-xs font-semibold uppercase text-gray-400">
            Sự cố gần đây trên camera này
          </h4>

          {events.length === 0 ? (
            <EmptyState
              title="Chưa ghi nhận sự cố nào"
              hint="Camera đang hoạt động bình thường trong khoảng thời gian đang xem."
            />
          ) : (
            <ul className="space-y-2">
              {events.map((event) => (
                <li key={event.id}>
                  <Link
                    to={`/incidents/${event.id}`}
                    onClick={onClose}
                    className="block rounded-xl border border-gray-800 bg-gray-950/70 p-3 transition-colors hover:border-blue-500/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  >
                    <div className="mb-1.5 flex flex-wrap items-center gap-2">
                      <SeverityBadge severity={event.effectiveSeverity} />
                      <StateBadge state={event.state} />
                      <span className="ml-auto font-mono text-[11px] text-gray-500">
                        {new Date(event.detectedAt).toLocaleString('vi-VN')}
                      </span>
                    </div>
                    <p className="text-xs leading-relaxed text-gray-300">
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
