import { useEffect, useState, useRef } from 'react';
import { ShieldAlert, Package, X } from 'lucide-react';
import { useEvents } from '../../realtime/EventsProvider';
import { EVENT_TYPE_LABEL, SecurityEvent, SEVERITY_LABEL } from '../../domain/types';

/** Web Audio API Synth Alert Sound */
function playAlertSound(isCritical = false) {
  try {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    const now = ctx.currentTime;
    osc.type = isCritical ? 'sawtooth' : 'sine';
    
    // Frequency pattern (Alarm melody)
    osc.frequency.setValueAtTime(isCritical ? 880 : 660, now);
    osc.frequency.setValueAtTime(isCritical ? 1100 : 880, now + 0.12);
    osc.frequency.setValueAtTime(isCritical ? 880 : 660, now + 0.25);
    osc.frequency.setValueAtTime(isCritical ? 1100 : 880, now + 0.38);

    gain.gain.setValueAtTime(0.3, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.55);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + 0.55);
  } catch (err) {
    console.warn('Web Audio API notification sound error:', err);
  }
}

export function NotificationToast() {
  const { events } = useEvents();
  const [activeToast, setActiveToast] = useState<SecurityEvent | null>(null);
  const alertedIdsRef = useRef<Set<number>>(new Set());
  const isFirstRender = useRef(true);

  useEffect(() => {
    if (!events || events.length === 0) return;

    // Tránh phát chuông tự động đối với các event có sẵn từ khi mở app lần đầu
    if (isFirstRender.current) {
      events.forEach((ev) => alertedIdsRef.current.add(ev.id));
      isFirstRender.current = false;
      return;
    }

    const latest = events[0];
    if (
      latest &&
      !alertedIdsRef.current.has(latest.id) &&
      (latest.eventType === 'ZONE_INTRUSION' ||
        latest.eventType === 'ABANDONED_OBJECT' ||
        latest.eventType === 'CROWD_THRESHOLD' ||
        (latest.eventType as string) === 'xam_nhap' ||
        (latest.eventType as string) === 'vat_the_bo_quen' ||
        (latest.eventType as string) === 'tu_tap_dong_nguoi')
    ) {
      alertedIdsRef.current.add(latest.id);
      setActiveToast(latest);
      playAlertSound(latest.effectiveSeverity === 'CRITICAL' || latest.effectiveSeverity === 'HIGH');
      const timer = setTimeout(() => {
        setActiveToast((current) => (current?.id === latest.id ? null : current));
      }, 7000);
      return () => clearTimeout(timer);
    }
  }, [events]);

  if (!activeToast) return null;

  const isIntrusion =
    activeToast.eventType === 'ZONE_INTRUSION' || (activeToast.eventType as string) === 'xam_nhap';

  return (
    <div
      role="alert"
      className="fixed top-5 left-1/2 -translate-x-1/2 z-50 flex w-full max-w-lg items-start gap-4 rounded-2xl border border-rose-500/50 bg-gray-900/95 p-4 text-white shadow-2xl backdrop-blur-md animate-bounce-short"
    >
      <div
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
          isIntrusion ? 'bg-rose-600 text-white' : 'bg-amber-600 text-white'
        }`}
      >
        {isIntrusion ? <ShieldAlert className="h-6 w-6" /> : <Package className="h-6 w-6" />}
      </div>

      <div className="flex-1 space-y-1">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm text-rose-400 uppercase tracking-wide">
              {EVENT_TYPE_LABEL[activeToast.eventType] || 'CẢNH BÁO TỨC THÌ'}
            </span>
            <span className="rounded bg-rose-950 px-2 py-0.5 font-mono text-[10px] font-bold text-rose-300 border border-rose-800/60">
              {SEVERITY_LABEL[activeToast.effectiveSeverity] || activeToast.effectiveSeverity}
            </span>
          </div>
          <span className="font-mono text-[11px] text-gray-400">
            {new Date(activeToast.detectedAt).toLocaleTimeString('vi-VN')}
          </span>
        </div>

        <p className="text-xs font-semibold text-gray-200">{activeToast.description}</p>
        <p className="font-mono text-[11px] text-gray-400">
          Camera: <span className="text-white font-bold">{activeToast.cameraName}</span>
        </p>
      </div>

      <button
        onClick={() => setActiveToast(null)}
        className="rounded-lg p-1 text-gray-400 hover:bg-gray-800 hover:text-white"
        aria-label="Đóng thông báo"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
