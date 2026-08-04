import React, { useState } from 'react';
import { Camera as CameraType, Incident } from '../types';
import { Maximize2, ShieldAlert, Video, Eye } from 'lucide-react';

interface CameraGridProps {
  cameras: CameraType[];
  incidents: Incident[];
  onSelectCamera?: (camera: CameraType) => void;
}

export const CameraGrid: React.FC<CameraGridProps> = ({ cameras, incidents }) => {
  const [selectedCam, setSelectedCam] = useState<CameraType | null>(null);

  // Helper to find pending incident for camera
  const getActiveIncident = (camId: number) => {
    return incidents.find(inc => inc.camera_id === camId && inc.status === 'pending');
  };

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Grid Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Video className="w-5 h-5 text-blue-400" />
          <h2 className="text-sm font-bold tracking-wide uppercase text-gray-200">
            MA TRẬN CAMERA GIÁM SÁT (6 LUỒNG SIMULATION HUD)
          </h2>
        </div>
        <div className="text-xs text-gray-400 font-mono">
          STATUS: <span className="text-emerald-400 font-semibold">ALL FEED STABLE</span>
        </div>
      </div>

      {/* 2x3 Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 flex-1 overflow-y-auto pr-1">
        {cameras.map((cam) => {
          const activeIncident = getActiveIncident(cam.id);
          const isCritical = activeIncident?.severity === 'critical';
          const isWarning = activeIncident?.severity === 'warning' || cam.status === 'warning';

          return (
            <div
              key={cam.id}
              onClick={() => setSelectedCam(cam)}
              className={`relative group rounded-xl overflow-hidden cursor-pointer border transition-all duration-300 ${
                isCritical
                  ? 'border-red-500 shadow-lg shadow-red-500/20 glass-panel-danger ring-2 ring-red-500/50'
                  : isWarning
                  ? 'border-amber-500/60 shadow-lg shadow-amber-500/10 bg-gray-900/90'
                  : 'border-gray-800 hover:border-blue-500/50 bg-gray-900/60'
              }`}
            >
              {/* Top HUD Info bar */}
              <div className="absolute top-0 inset-x-0 z-20 px-3 py-2 bg-gradient-to-b from-black/80 to-transparent flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${
                    isCritical ? 'bg-red-500 animate-ping' : isWarning ? 'bg-amber-400' : 'bg-emerald-400'
                  }`}></span>
                  <span className="text-xs font-mono font-bold text-white tracking-wider">
                    {cam.name.toUpperCase()}
                  </span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-black/60 text-gray-300 border border-gray-700">
                  {cam.location}
                </span>
              </div>

              {/* Video Stream Container */}
              <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden">
                <img
                  src={cam.stream_url}
                  alt={cam.name}
                  className="w-full h-full object-cover opacity-80 group-hover:scale-105 transition-transform duration-500"
                />

                {/* Radar Grid overlay line */}
                <div className="absolute inset-0 pointer-events-none opacity-20 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
                <div className="absolute inset-x-0 h-1 bg-blue-500/30 animate-radar pointer-events-none"></div>

                {/* Active Bounding Box if Incident exists */}
                {activeIncident && (
                  <div
                    className="absolute border-2 border-red-500 bg-red-500/10 animate-bbox flex items-start p-1 pointer-events-none"
                    style={{
                      left: `${(cam.id * 15) % 50 + 10}%`,
                      top: `${(cam.id * 20) % 40 + 15}%`,
                      width: '35%',
                      height: '45%'
                    }}
                  >
                    <span className="bg-red-600 text-white text-[9px] font-mono px-1 py-0.2 rounded font-bold uppercase tracking-wider">
                      {activeIncident.event_type === 'xam_nhap' ? 'AI: XÂM NHẬP' : 'AI: ĐÁM ĐỒNG'}
                    </span>
                  </div>
                )}

                {/* Bottom HUD bar overlay */}
                <div className="absolute bottom-0 inset-x-0 z-20 px-3 py-1.5 bg-gradient-to-t from-black/90 to-transparent flex items-center justify-between text-[11px] font-mono text-gray-400">
                  <div className="flex items-center gap-1 text-emerald-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    <span>LIVE HD 1080P</span>
                  </div>
                  <span>CAM_0{cam.id}_FEED</span>
                </div>

                {/* Hover overlay hint */}
                <div className="absolute inset-0 bg-blue-900/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2 text-white font-medium text-xs z-30 pointer-events-none">
                  <Maximize2 className="w-4 h-4" />
                  <span>Phóng To Luồng Cam</span>
                </div>
              </div>

              {/* Incident Alert Badge if active */}
              {activeIncident && (
                <div className="p-2.5 bg-red-950/80 border-t border-red-500/40 flex items-center justify-between text-xs text-red-300">
                  <div className="flex items-center gap-2 font-medium">
                    <ShieldAlert className="w-4 h-4 text-red-400 animate-bounce" />
                    <span className="truncate">{activeIncident.description}</span>
                  </div>
                  <span className="text-[10px] font-mono uppercase bg-red-900/60 text-red-200 px-1.5 py-0.5 rounded border border-red-500/40 shrink-0">
                    {activeIncident.status}
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Camera Fullscreen / Zoom Modal */}
      {selectedCam && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-md p-4">
          <div className="w-full max-w-4xl bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden glass-panel flex flex-col">
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between bg-gray-950">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-emerald-400 animate-ping"></div>
                <div>
                  <h3 className="font-bold text-white text-base">{selectedCam.name}</h3>
                  <p className="text-xs text-gray-400">{selectedCam.location}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedCam(null)}
                className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs rounded-lg transition-colors"
              >
                Đóng (Esc)
              </button>
            </div>

            <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden">
              <img
                src={selectedCam.stream_url}
                alt={selectedCam.name}
                className="w-full h-full object-cover"
              />
              <div className="absolute top-4 left-4 font-mono text-xs text-emerald-400 bg-black/70 px-3 py-1.5 rounded border border-emerald-500/40">
                REC ● 60FPS // ENCRYPTION ACTIVE
              </div>
            </div>

            <div className="p-4 bg-gray-950 text-xs text-gray-400 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span>RTSP Stream: <strong className="text-gray-200">rtsp://camera-{selectedCam.id}.local/live</strong></span>
                <span>Khung hình AI: <strong className="text-blue-400">YOLOv8 + GroundingDINO</strong></span>
              </div>
              <div className="flex items-center gap-2">
                <Eye className="w-4 h-4 text-blue-400" />
                <span>Bảo vệ đang trực tiếp giám sát</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
