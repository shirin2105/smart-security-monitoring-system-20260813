/**
 * Kênh cảnh báo realtime — BAC-51.
 *
 * Nguyên tắc theo PRD §7.2: WebSocket KHÔNG phải source of truth. Mỗi lần
 * (re)connect đều gọi `onReconcile` để tải lại qua REST, phòng trường hợp có
 * message rơi trong lúc mất kết nối.
 */

import { useEffect, useRef, useState } from 'react';

import { isMockMode } from '../api';
import { WS_URL } from '../api/config';
import { RawIncident, toEvent } from '../api/adapters';
import { subscribeMockStream } from '../api/mock/mockTransport';
import { CameraTelemetry, SecurityEvent } from '../domain/types';

export type StreamStatus = 'connecting' | 'open' | 'reconnecting' | 'offline';

interface StreamHandlers {
  onEventCreated: (event: SecurityEvent) => void;
  /** Message chỉ báo id thay đổi — caller tự tải lại chi tiết. */
  onEventUpdated: (eventId: number) => void;
  /** Chạy sau mỗi lần kết nối thành công, để đồng bộ lại bằng REST. */
  onReconcile: () => void;
  /** Nhận frame telemetry (bounding box realtime từ CV). */
  onTelemetryReceived?: (telemetry: CameraTelemetry) => void;
}

const MAX_BACKOFF_MS = 15_000;
const BASE_BACKOFF_MS = 1_000;

export function useAlertStream(handlers: StreamHandlers): {
  status: StreamStatus;
  lastMessageAt: string | null;
} {
  const [status, setStatus] = useState<StreamStatus>('connecting');
  const [lastMessageAt, setLastMessageAt] = useState<string | null>(null);

  // Giữ handler trong ref: đổi callback không được làm đứt kết nối đang mở.
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  /** Chống xử lý trùng một (id, version) khi server gửi lặp hoặc sau reconnect. */
  const seenRef = useRef<Map<number, number>>(new Map());

  useEffect(() => {
    const seen = seenRef.current;

    const acceptOnce = (event: SecurityEvent): boolean => {
      if (seen.get(event.id) === event.version) return false;
      seen.set(event.id, event.version);
      return true;
    };

    /* ------------------------------ mock mode ------------------------------ */
    if (isMockMode) {
      setStatus('open');
      handlersRef.current.onReconcile();

      return subscribeMockStream((event, kind) => {
        setLastMessageAt(new Date().toISOString());
        if (kind === 'created') {
          if (acceptOnce(event)) handlersRef.current.onEventCreated(event);
        } else {
          seen.set(event.id, event.version);
          handlersRef.current.onEventUpdated(event.id);
        }
      });
    }

    /* --------------------------- WebSocket thật ---------------------------- */
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;
    let disposed = false;

    const connect = () => {
      if (disposed) return;
      setStatus(attempt === 0 ? 'connecting' : 'reconnecting');

      try {
        socket = new WebSocket(WS_URL);
      } catch {
        scheduleRetry();
        return;
      }

      socket.onopen = () => {
        if (disposed) return;
        attempt = 0;
        setStatus('open');
        // REST reconcile: bù các event phát sinh khi kết nối đang đứt.
        handlersRef.current.onReconcile();
      };

      socket.onmessage = (message) => {
        setLastMessageAt(new Date().toISOString());
        try {
          const payload = JSON.parse(message.data);

          if (payload.type === 'NEW_ALERT' && payload.incident) {
            const event = toEvent(payload.incident as RawIncident);
            if (acceptOnce(event)) handlersRef.current.onEventCreated(event);
          } else if (payload.type === 'ALERT_UPDATED' && payload.incident_id != null) {
            handlersRef.current.onEventUpdated(Number(payload.incident_id));
          } else if (payload.type === 'FRAME_TELEMETRY' && payload.numericCameraId != null) {
            handlersRef.current.onTelemetryReceived?.(payload as CameraTelemetry);
          }
        } catch {
          // Message hỏng không được làm sập kênh — bỏ qua và chờ message sau.
        }
      };

      socket.onclose = () => {
        if (disposed) return;
        scheduleRetry();
      };

      socket.onerror = () => {
        socket?.close();
      };
    };

    const scheduleRetry = () => {
      if (disposed) return;
      setStatus(attempt === 0 ? 'offline' : 'reconnecting');
      const delay = Math.min(BASE_BACKOFF_MS * 2 ** attempt, MAX_BACKOFF_MS);
      attempt += 1;
      retryTimer = setTimeout(connect, delay);
    };

    connect();

    return () => {
      disposed = true;
      if (retryTimer) clearTimeout(retryTimer);
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    };
  }, []);

  return { status, lastMessageAt };
}
