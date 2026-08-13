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
  riskScore: number; // 0 - 100
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
    coordinates: { x: 5, y: 10, width: 40, height: 35 },
  },
  {
    id: 'z2',
    name: 'Bãi Xe Nhân Viên & Khách',
    code: 'ZONE-B',
    riskScore: 62,
    status: 'HIGH',
    cameraCount: 2,
    activeIncidents: 1,
    coordinates: { x: 50, y: 10, width: 45, height: 35 },
  },
  {
    id: 'z3',
    name: 'Sảnh Trung Tâm & Lễ Tân',
    code: 'ZONE-C',
    riskScore: 35,
    status: 'MEDIUM',
    cameraCount: 1,
    activeIncidents: 0,
    coordinates: { x: 5, y: 50, width: 40, height: 40 },
  },
  {
    id: 'z4',
    name: 'Khu Vực Kho Vận & Xuất Hàng',
    code: 'ZONE-D',
    riskScore: 18,
    status: 'LOW',
    cameraCount: 1,
    activeIncidents: 0,
    coordinates: { x: 50, y: 50, width: 45, height: 40 },
  },
];

const ZONE_STATUS_STYLE: Record<Zone['status'], { badge: string; border: string; bg: string; dot: string }> = {
  CRITICAL: {
    badge: 'bg-rose-50 dark:bg-red-500/20 text-rose-700 dark:text-red-300 border-rose-300 dark:border-red-500/50',
    border: 'border-rose-500 dark:border-red-500',
    bg: 'bg-rose-500/10 dark:bg-red-500/15',
    dot: 'bg-rose-500 animate-ping',
  },
  HIGH: {
    badge: 'bg-amber-50 dark:bg-amber-500/20 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-500/50',
    border: 'border-amber-500 dark:border-amber-500',
    bg: 'bg-amber-500/10 dark:bg-amber-500/15',
    dot: 'bg-amber-500',
  },
  MEDIUM: {
    badge: 'bg-blue-50 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-500/50',
    border: 'border-blue-500 dark:border-blue-500',
    bg: 'bg-blue-500/10 dark:bg-blue-500/15',
    dot: 'bg-blue-500',
  },
  LOW: {
    badge: 'bg-emerald-50 dark:bg-emerald-500/20 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/50',
    border: 'border-emerald-500 dark:border-emerald-500',
    bg: 'bg-emerald-500/10 dark:bg-emerald-500/15',
    dot: 'bg-emerald-500',
  },
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

  // Map cameras to zone mock assignment
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
    <div className="flex flex-1 flex-col gap-5 overflow-y-auto">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="rounded-xl border border-blue-500/40 bg-blue-600/10 dark:bg-blue-600/20 p-2 text-blue-600 dark:text-blue-400 shadow-sm">
            <MapIcon className="h-5 w-5" aria-hidden />
          </div>
          <div>
            <h1 className="text-base font-extrabold tracking-wide text-gray-900 dark:text-white">
              BẢN ĐỒ ĐIỂM NÓNG AN NINH
            </h1>
            <p className="text-[11px] text-gray-500 dark:text-gray-400">
              Phân tích chỉ số mật độ rủi ro & nhiệt độ sự cố theo vùng mặt bằng
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 font-mono text-xs">
          <div className="flex items-center gap-2 rounded-xl border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 px-3.5 py-2 shadow-sm">
            <Flame className="h-4 w-4 text-rose-500" />
            <span className="text-gray-600 dark:text-gray-400">Rủi ro cao nhất:</span>
            <span className="font-bold text-rose-600 dark:text-rose-400">ZONE-A (85%)</span>
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 px-3.5 py-2 shadow-sm">
            <ShieldAlert className="h-4 w-4 text-amber-500" />
            <span className="text-gray-600 dark:text-gray-400">Cảnh báo mở:</span>
            <span className="font-bold text-amber-600 dark:text-amber-400">{totalIncidents} sự cố</span>
          </div>
        </div>
      </header>

      {/* Grid tổng quan metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {ZONES.map((zone) => {
          const isSelected = zone.id === selectedZoneId;
          const style = ZONE_STATUS_STYLE[zone.status];
          return (
            <button
              key={zone.id}
              onClick={() => setSelectedZoneId(zone.id)}
              className={`flex flex-col text-left rounded-2xl border p-4.5 transition-all shadow-sm card-elevation focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                isSelected
                  ? 'border-blue-500 ring-2 ring-blue-500/40 bg-blue-50/50 dark:bg-gray-900'
                  : 'border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/60 hover:border-gray-300 dark:hover:border-gray-700'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-xs font-bold text-gray-500 dark:text-gray-400">{zone.code}</span>
                <span className={`inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[10px] font-bold border ${style.badge}`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
                  {zone.status}
                </span>
              </div>
              <h3 className="text-sm font-bold text-gray-900 dark:text-white truncate mb-3">{zone.name}</h3>

              {/* Progress bar rủi ro */}
              <div className="mt-auto space-y-1.5">
                <div className="flex justify-between text-[11px] font-mono">
                  <span className="text-gray-500 dark:text-gray-400">Chỉ số nhiệt độ:</span>
                  <span className="font-bold text-gray-900 dark:text-gray-200">{zone.riskScore}/100</span>
                </div>
                <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-800 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${
                      zone.riskScore > 75
                        ? 'bg-rose-500'
                        : zone.riskScore > 50
                        ? 'bg-amber-500'
                        : zone.riskScore > 25
                        ? 'bg-blue-500'
                        : 'bg-emerald-500'
                    }`}
                    style={{ width: `${zone.riskScore}%` }}
                  />
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Map mặt bằng + Chi tiết vùng */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 min-h-[420px]">
        {/* Bản đồ nhiệt mặt bằng 2D tương tác */}
        <section className="lg:col-span-7 flex flex-col rounded-2xl border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="flex items-center gap-2 text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider">
              <Building2 className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              Sơ đồ mặt bằng tòa nhà (Floorplan Heatmap)
            </h2>
            <div className="flex items-center gap-3 text-[11px] font-mono text-gray-500">
              <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-rose-500" /> Nguy hiểm</span>
              <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-amber-500" /> Rủi ro</span>
              <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-500" /> An toàn</span>
            </div>
          </div>

          <div className="relative flex-1 min-h-[300px] w-full rounded-xl border border-gray-200 dark:border-gray-800 bg-slate-100 dark:bg-gray-950 overflow-hidden">
            {/* Grid đường kẻ sơ đồ */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:20px_20px]" />

            {/* Các vùng tương tác */}
            {ZONES.map((zone) => {
              const isSelected = zone.id === selectedZoneId;
              const style = ZONE_STATUS_STYLE[zone.status];
              return (
                <button
                  key={zone.id}
                  onClick={() => setSelectedZoneId(zone.id)}
                  style={{
                    left: `${zone.coordinates.x}%`,
                    top: `${zone.coordinates.y}%`,
                    width: `${zone.coordinates.width}%`,
                    height: `${zone.coordinates.height}%`,
                  }}
                  className={`absolute rounded-xl border-2 transition-all p-3 flex flex-col justify-between text-left ${style.bg} ${style.border} ${
                    isSelected ? 'ring-4 ring-blue-500/50 scale-[1.01] z-10 shadow-lg' : 'opacity-85 hover:opacity-100'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-extrabold text-gray-900 dark:text-white bg-white/80 dark:bg-gray-900/80 px-2 py-0.5 rounded shadow-sm">
                      {zone.code}
                    </span>
                    <span className="font-mono text-[11px] font-bold text-gray-800 dark:text-gray-200">
                      {zone.riskScore}°C
                    </span>
                  </div>
                  <div>
                    <p className="text-xs font-bold text-gray-900 dark:text-gray-100 truncate">{zone.name}</p>
                    <p className="text-[10px] text-gray-600 dark:text-gray-400 font-mono mt-0.5">
                      {zone.cameraCount} camera · {zone.activeIncidents} cảnh báo
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        {/* Thông tin vùng được chọn */}
        <section className="lg:col-span-5 flex flex-col rounded-2xl border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 p-5 shadow-sm">
          <header className="border-b border-gray-200 dark:border-gray-800 pb-3 mb-4">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-blue-600 dark:text-blue-400 uppercase">
                {selectedZone.code}
              </span>
              <span className={`inline-flex items-center gap-1 rounded-md px-2.5 py-0.5 text-[10px] font-bold border ${ZONE_STATUS_STYLE[selectedZone.status].badge}`}>
                Mức {selectedZone.status}
              </span>
            </div>
            <h2 className="text-base font-bold text-gray-900 dark:text-white mt-1">
              {selectedZone.name}
            </h2>
          </header>

          <div className="space-y-4 flex-1">
            {/* Camera theo vùng */}
            <div>
              <h3 className="flex items-center gap-1.5 font-mono text-xs font-bold uppercase text-gray-700 dark:text-gray-400 mb-2">
                <CameraIcon className="h-3.5 w-3.5 text-blue-500" />
                Camera gán theo vùng ({selectedZoneCameras.length})
              </h3>
              <div className="space-y-2">
                {selectedZoneCameras.map((cam) => (
                  <div
                    key={cam.id}
                    className="flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-800 bg-slate-50 dark:bg-gray-950/70 p-3 shadow-sm"
                  >
                    <div>
                      <h4 className="text-xs font-bold text-gray-900 dark:text-gray-200">{cam.name}</h4>
                      <p className="text-[11px] text-gray-500">{cam.location}</p>
                    </div>
                    <HealthDot health={cam.health} />
                  </div>
                ))}
              </div>
            </div>

            {/* Sự cố mới nhất thuộc vùng */}
            <div>
              <h3 className="flex items-center gap-1.5 font-mono text-xs font-bold uppercase text-gray-700 dark:text-gray-400 mb-2">
                <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                Sự cố đang phát hiện ({selectedZoneEvents.length})
              </h3>
              {selectedZoneEvents.length === 0 ? (
                <div className="rounded-xl border border-emerald-200 dark:border-emerald-900/40 bg-emerald-50/50 dark:bg-emerald-950/20 p-4 text-center">
                  <ShieldCheck className="h-6 w-6 text-emerald-600 dark:text-emerald-400 mx-auto mb-1" />
                  <p className="text-xs font-bold text-emerald-800 dark:text-emerald-300">Vùng an toàn</p>
                  <p className="text-[11px] text-emerald-600 dark:text-emerald-400">Chưa ghi nhận sự cố bất thường.</p>
                </div>
              ) : (
                <ul className="space-y-2">
                  {selectedZoneEvents.map((evt) => (
                    <li
                      key={evt.id}
                      className="rounded-xl border border-gray-200 dark:border-gray-800 bg-slate-50 dark:bg-gray-950/70 p-3"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <SeverityBadge severity={evt.effectiveSeverity} />
                        <StateBadge state={evt.state} />
                      </div>
                      <p className="text-xs font-medium text-gray-800 dark:text-gray-200">{evt.description}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
