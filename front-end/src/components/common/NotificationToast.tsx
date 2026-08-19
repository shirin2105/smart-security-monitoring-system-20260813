import { useEffect, useState, useRef } from 'react';
import { Banner } from '@astryxdesign/core/Banner';
import { HStack, VStack } from '@astryxdesign/core/Stack';
import { Text } from '@astryxdesign/core/Text';
import { Token } from '@astryxdesign/core/Token';
import { useEvents } from '../../realtime/EventsProvider';
import { EVENT_TYPE_LABEL, SecurityEvent, SEVERITY_LABEL } from '../../domain/types';

/** Web Audio API Synth Alert Sound */
function playAlertSound(isCritical = false) {
  try {
    const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
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

  const isCritical = activeToast.effectiveSeverity === 'CRITICAL' || activeToast.effectiveSeverity === 'HIGH';

  return (
    <div
      style={{
        position: 'fixed',
        top: 'var(--spacing-4)',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 9999,
        maxWidth: 560,
        width: '90%',
      }}
    >
      <Banner
        status={isCritical ? 'error' : 'warning'}
        container="card"
        elevation="high"
        isDismissable
        onDismiss={() => setActiveToast(null)}
        title={
          <HStack gap={2} vAlign="center" style={{ flexWrap: 'nowrap' }}>
            <Text type="label" weight="bold">
              {EVENT_TYPE_LABEL[activeToast.eventType] || 'CẢNH BÁO TỨC THÌ'}
            </Text>
            <Token
              size="sm"
              color={isCritical ? 'red' : 'yellow'}
              label={SEVERITY_LABEL[activeToast.effectiveSeverity] || activeToast.effectiveSeverity}
            />
            <Text type="code" size="xsm" color="secondary" style={{ flexShrink: 0, whiteSpace: 'nowrap' }}>
              {new Date(activeToast.detectedAt).toLocaleTimeString('vi-VN')}
            </Text>
          </HStack>
        }
        description={
          <VStack gap={1} paddingBlock={1}>
            <Text type="body">
              {activeToast.description}
            </Text>
            <Text type="supporting" color="secondary">
              Camera: {activeToast.cameraName}
            </Text>
          </VStack>
        }
      />
    </div>
  );
}
