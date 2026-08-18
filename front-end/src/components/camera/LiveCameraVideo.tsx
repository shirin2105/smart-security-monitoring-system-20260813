import { useEffect, useRef, useState } from 'react';

import { api } from '../../api';
import { StreamClockEntry } from '../../api/types';

interface LiveCameraVideoProps {
  cameraId: number;
  src: string;
  className: string;
}

const SYNC_INTERVAL_MS = 10_000;
const CLOCK_REFRESH_MS = 20_000;
const MAX_DRIFT_S = 1.5;

/**
 * Video camera giả lập một luồng trực tiếp liên tục.
 *
 * CV producer đăng ký `epoch` (wall-clock lúc vòng lặp bắt đầu) + `duration` của
 * nguồn video. Playhead được tính chung từ wall-clock: `(now - epoch) % duration`,
 * nên mọi surface (tile, modal) cùng xem đúng vị trí model đang nhận diện — thay
 * vì mỗi element mở ra lại phát lại từ giây 0.
 */
export function LiveCameraVideo({ cameraId, src, className }: LiveCameraVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [clock, setClock] = useState<StreamClockEntry | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      api
        .getStreamClock()
        .then((clocks) => {
          if (!cancelled) {
            setClock(clocks.find((entry) => entry.camera_id === cameraId) ?? null);
          }
        })
        .catch(() => {
          if (!cancelled) setClock(null);
        });
    };
    load();
    // Mỗi pass mới CV đăng ký epoch mới — refresh để playhead không lệch.
    const timer = setInterval(load, CLOCK_REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [cameraId, src]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !clock) return;

    const playheadAt = () => {
      const duration = clock.duration || 1;
      const raw = (Date.now() / 1000 - clock.epoch) % duration;
      return ((raw % duration) + duration) % duration;
    };

    const sync = () => {
      if (!video) return;
      const target = playheadAt();
      if (Number.isFinite(target) && Math.abs(video.currentTime - target) > MAX_DRIFT_S) {
        video.currentTime = target;
      }
    };

    // Bắt đầu đúng vị trí live, không phát từ đầu.
    const onMetadata = () => {
      const target = playheadAt();
      if (Number.isFinite(target)) video.currentTime = target;
    };
    video.addEventListener('loadedmetadata', onMetadata);
    // Hiệu chỉnh trôi nhịp theo thời gian (bỏ qua nếu người xem đang tương tác).
    const timer = setInterval(sync, SYNC_INTERVAL_MS);
    onMetadata();
    return () => {
      video.removeEventListener('loadedmetadata', onMetadata);
      clearInterval(timer);
    };
  }, [clock]);

  return (
    <video
      ref={videoRef}
      src={src}
      autoPlay
      muted
      loop
      playsInline
      className={className}
    />
  );
}