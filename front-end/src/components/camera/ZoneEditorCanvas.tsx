import { useState, useRef, MouseEvent } from 'react';
import { Camera, CameraZone } from '../../domain/types';
import { Check, RotateCcw, X, ShieldAlert } from 'lucide-react';

interface ZoneEditorCanvasProps {
  camera: Camera;
  existingZone?: CameraZone;
  onSave: (zone: CameraZone) => Promise<void>;
  onClose: () => void;
}

export function ZoneEditorCanvas({
  camera,
  existingZone,
  onSave,
  onClose,
}: ZoneEditorCanvasProps) {
  const [points, setPoints] = useState<[number, number][]>(
    existingZone?.polygon || []
  );
  const [zoneName, setZoneName] = useState<string>(
    existingZone?.name || `Vùng Intrusion ${camera.name}`
  );
  const [saving, setSaving] = useState(false);
  const svgRef = useRef<SVGSVGElement | null>(null);

  // Thêm điểm vào polygon khi click SVG
  const handleSvgClick = (e: MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const rawX = (e.clientX - rect.left) / rect.width;
    const rawY = (e.clientY - rect.top) / rect.height;

    const x = Math.max(0, Math.min(1280, Math.round(rawX * 1280)));
    const y = Math.max(0, Math.min(720, Math.round(rawY * 720)));

    setPoints((prev) => [...prev, [x, y]]);
  };

  const handleClear = () => {
    setPoints([]);
  };

  const handleSave = async () => {
    if (points.length < 3) return;
    setSaving(true);
    try {
      const cameraKey = camera.id <= 9 ? `cam_0${camera.id}` : `cam_${camera.id}`;
      const zoneId = existingZone?.zoneId || `zone_${cameraKey}`;
      await onSave({
        zoneId,
        cameraId: cameraKey,
        name: zoneName,
        polygon: points,
        enabled: true,
      });
      onClose();
    } catch (err) {
      console.error('Lỗi lưu vùng Intrusion:', err);
    } finally {
      setSaving(false);
    }
  };

  const pointsString = points.map((p) => `${p[0]},${p[1]}`).join(' ');

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
    >
      <div className="flex w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-gray-700 bg-gray-900 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-800 px-6 py-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-amber-500" />
            <h3 className="text-base font-bold text-white">
              Thiết lập vùng Intrusion (Xâm nhập) — {camera.name}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-800 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-1 items-center gap-3">
              <label className="text-xs font-semibold text-gray-300">Tên vùng:</label>
              <input
                type="text"
                value={zoneName}
                onChange={(e) => setZoneName(e.target.value)}
                className="flex-1 rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:border-amber-500 focus:outline-none"
                placeholder="Nhập tên vùng..."
              />
            </div>
            <div className="font-mono text-xs text-amber-400 bg-amber-950/60 border border-amber-800/60 px-3 py-1.5 rounded-lg">
              Số điểm đã chấm: <span className="font-bold text-white">{points.length}</span> (tối thiểu 3 điểm)
            </div>
          </div>

          <p className="text-xs text-gray-400">
            * Click trực tiếp lên video bên dưới để chấm các đỉnh polygon của Vùng Intrusion. Tọa độ sẽ được tự động quy đổi về độ phân giải gốc <code className="text-amber-400">1280x720</code>.
          </p>

          {/* Video Stream + Interactive SVG Overlay */}
          <div className="relative aspect-video w-full overflow-hidden rounded-xl border border-gray-800 bg-black">
            {camera.previewUrl.match(/\.(mp4|webm|avi)(\?.*)?$/i) ? (
              <video
                src={camera.previewUrl}
                autoPlay
                muted
                loop
                playsInline
                className="h-full w-full object-contain pointer-events-none opacity-75"
              />
            ) : (
              <img
                src={camera.previewUrl}
                alt=""
                className="h-full w-full object-contain pointer-events-none opacity-75"
              />
            )}

            {/* Interactive SVG Overlay */}
            <svg
              ref={svgRef}
              onClick={handleSvgClick}
              viewBox="0 0 1280 720"
              preserveAspectRatio="none"
              className="absolute inset-0 h-full w-full cursor-crosshair z-20"
            >
              {/* Drawn Polygon Fill & Stroke */}
              {points.length >= 3 && (
                <polygon
                  points={pointsString}
                  fill="rgba(245, 158, 11, 0.25)"
                  stroke="#f59e0b"
                  strokeWidth="4"
                  strokeDasharray="6 4"
                />
              )}

              {/* Drawn Line Segments before 3 points */}
              {points.length > 1 && (
                <polyline
                  points={pointsString}
                  fill="none"
                  stroke="#f59e0b"
                  strokeWidth="3"
                />
              )}

              {/* Point Markers */}
              {points.map(([px, py], i) => (
                <g key={i}>
                  <circle cx={px} cy={py} r="10" fill="#f59e0b" stroke="#ffffff" strokeWidth="2" />
                  <text
                    x={px}
                    y={py + 4}
                    fill="#000000"
                    fontSize="12"
                    fontWeight="bold"
                    textAnchor="middle"
                    className="pointer-events-none select-none font-mono"
                  >
                    {i + 1}
                  </text>
                </g>
              ))}
            </svg>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between border-t border-gray-800 px-6 py-4 bg-gray-900/60">
          <button
            type="button"
            onClick={handleClear}
            className="flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-800 px-4 py-2 text-xs font-semibold text-gray-300 transition hover:bg-gray-700 hover:text-white"
          >
            <RotateCcw className="h-4 w-4" />
            Xóa / Vẽ lại
          </button>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-700 px-4 py-2 text-xs font-semibold text-gray-300 transition hover:bg-gray-800 hover:text-white"
            >
              Hủy
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={points.length < 3 || saving}
              className="flex items-center gap-2 rounded-lg bg-amber-600 px-5 py-2 text-xs font-bold text-white shadow-md transition hover:bg-amber-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Check className="h-4 w-4" />
              {saving ? 'Đang lưu...' : 'Lưu vùng Intrusion'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
