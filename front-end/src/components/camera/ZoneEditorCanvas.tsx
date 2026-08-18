import { useState, useRef, MouseEvent } from 'react';
import { Camera, CameraZone } from '../../domain/types';
import { Check, RotateCcw } from 'lucide-react';

import { Dialog, DialogHeader } from '@astryxdesign/core/Dialog';
import { HStack, VStack } from '@astryxdesign/core/Stack';
import { Text } from '@astryxdesign/core/Text';
import { TextInput } from '@astryxdesign/core/TextInput';
import { Button } from '@astryxdesign/core/Button';
import { Token } from '@astryxdesign/core/Token';
import { AspectRatio } from '@astryxdesign/core/AspectRatio';

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
    existingZone?.polygon || [],
  );
  const [zoneName, setZoneName] = useState<string>(
    existingZone?.name || `Vùng Intrusion ${camera.name}`,
  );
  const [saving, setSaving] = useState(false);
  const svgRef = useRef<SVGSVGElement | null>(null);

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
    <Dialog
      isOpen={true}
      onOpenChange={(isOpen) => {
        if (!isOpen && !saving) onClose();
      }}
      width={880}
      purpose="form"
    >
      <DialogHeader
        title={`Thiết lập vùng Intrusion (Xâm nhập) — ${camera.name}`}
        onOpenChange={(isOpen) => {
          if (!isOpen && !saving) onClose();
        }}
      />
      <VStack gap={4} padding={4}>
        <HStack justify="between" vAlign="end" wrap="wrap" gap={3}>
          <HStack gap={2} style={{ flex: 1, minWidth: 240 }}>
            <TextInput
              label="Tên vùng"
              value={zoneName}
              onChange={(val) => setZoneName(val)}
              placeholder="Nhập tên vùng..."
              size="sm"
            />
          </HStack>
          <Token
            size="md"
            color={points.length >= 3 ? 'green' : 'orange'}
            label={`Đã chấm: ${points.length} điểm (tối thiểu 3)`}
          />
        </HStack>

        <Text type="supporting" color="secondary">
          * Click trực tiếp lên khung hình để chấm các đỉnh polygon của Vùng Intrusion. Tọa độ tự động quy đổi về độ phân giải chuẩn 1280x720.
        </Text>

        {/* Video with SVG overlay */}
        <AspectRatio ratio={16 / 9}>
          <div
            style={{
              position: 'relative',
              width: '100%',
              height: '100%',
              backgroundColor: 'var(--color-background-body)',
              borderRadius: 'var(--radius-container)',
              overflow: 'hidden',
              border: '1px solid var(--color-border)',
            }}
          >
            {camera.previewUrl.match(/\.(mp4|webm|avi)(\?.*)?$/i) ? (
              <video
                src={camera.previewUrl}
                autoPlay
                muted
                loop
                playsInline
                style={{ width: '100%', height: '100%', objectFit: 'contain', pointerEvents: 'none', opacity: 0.75 }}
              />
            ) : (
              <img
                src={camera.previewUrl}
                alt=""
                style={{ width: '100%', height: '100%', objectFit: 'contain', pointerEvents: 'none', opacity: 0.75 }}
              />
            )}

            <svg
              ref={svgRef}
              onClick={handleSvgClick}
              viewBox="0 0 1280 720"
              preserveAspectRatio="none"
              style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', cursor: 'crosshair', zIndex: 20 }}
            >
              {points.length >= 3 && (
                <polygon
                  points={pointsString}
                  fill="color-mix(in oklch, var(--color-warning) 25%, transparent)"
                  stroke="var(--color-warning)"
                  strokeWidth="4"
                  strokeDasharray="6 4"
                />
              )}

              {points.length > 1 && (
                <polyline
                  points={pointsString}
                  fill="none"
                  stroke="var(--color-warning)"
                  strokeWidth="3"
                />
              )}

              {points.map(([px, py], i) => (
                <g key={i}>
                  <circle cx={px} cy={py} r="10" fill="var(--color-warning)" stroke="white" strokeWidth="2" />
                  <text
                    x={px}
                    y={py + 4}
                    fill="black"
                    fontSize="12"
                    fontWeight="bold"
                    textAnchor="middle"
                    fontFamily="monospace"
                    style={{ pointerEvents: 'none', userSelect: 'none' }}
                  >
                    {i + 1}
                  </text>
                </g>
              ))}
            </svg>
          </div>
        </AspectRatio>

        <HStack justify="between" vAlign="center">
          <Button
            label="Xóa / Vẽ lại"
            variant="secondary"
            size="sm"
            icon={<RotateCcw size={14} />}
            onClick={handleClear}
          />

          <HStack gap={2}>
            <Button
              label="Hủy"
              variant="secondary"
              size="sm"
              onClick={onClose}
              isDisabled={saving}
            />
            <Button
              label="Lưu vùng Intrusion"
              variant="primary"
              size="sm"
              isLoading={saving}
              isDisabled={points.length < 3 || saving}
              icon={<Check size={14} />}
              onClick={handleSave}
            />
          </HStack>
        </HStack>
      </VStack>
    </Dialog>
  );
}

