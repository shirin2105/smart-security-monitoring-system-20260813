/**
 * Kho sự kiện dùng chung cho toàn app.
 *
 * Đặt trên router nên WebSocket không bị đóng/mở lại mỗi lần đổi trang, và
 * dashboard lẫn trang danh sách cùng nhìn một nguồn dữ liệu.
 */

import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from 'react';

import { api } from '../api';
import { useAuth } from '../auth/AuthContext';
import { CameraTelemetry, SecurityEvent } from '../domain/types';
import { StreamStatus, useAlertStream } from './useAlertStream';

/** Số event giữ trong feed realtime của dashboard. */
const FEED_SIZE = 50;

interface EventsContextValue {
  events: SecurityEvent[];
  telemetryMap: Record<number, CameraTelemetry>;
  loading: boolean;
  error: unknown;
  streamStatus: StreamStatus;
  /** Tăng mỗi khi có thay đổi — trang khác dùng làm dependency để tải lại. */
  revision: number;
  reload: () => void;
  /** Ghi đè một event sau khi POST action thành công. */
  upsert: (event: SecurityEvent) => void;
  triggerSimulation: () => Promise<void>;
}

const EventsContext = createContext<EventsContextValue | null>(null);

function mergeById(list: SecurityEvent[], incoming: SecurityEvent): SecurityEvent[] {
  const index = list.findIndex((item) => item.id === incoming.id);
  if (index < 0) return [incoming, ...list].slice(0, FEED_SIZE);

  // Bỏ qua bản cũ hơn — tránh message đến trễ ghi đè trạng thái mới.
  if (list[index].version > incoming.version) return list;

  const next = [...list];
  next[index] = incoming;
  return next;
}

export function EventsProvider({ children }: { children: ReactNode }) {
  const { user, reportApiError } = useAuth();
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [telemetryMap, setTelemetryMap] = useState<Record<number, CameraTelemetry>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [revision, setRevision] = useState(0);

  const loadingRef = useRef(false);

  const reload = useCallback(async () => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    setLoading(true);

    try {
      const page = await api.getEvents({ page: 1, pageSize: FEED_SIZE });
      setEvents(page.items);
      setError(null);
    } catch (err) {
      reportApiError(err);
      setError(err);
    } finally {
      setLoading(false);
      loadingRef.current = false;
    }
  }, [reportApiError]);

  const upsert = useCallback((event: SecurityEvent) => {
    setEvents((list) => mergeById(list, event));
    setRevision((value) => value + 1);
  }, []);

  const handleTelemetry = useCallback((telemetry: CameraTelemetry) => {
    setTelemetryMap((prev) => ({
      ...prev,
      [telemetry.numericCameraId]: telemetry,
    }));
  }, []);

  const refetchOne = useCallback(
    async (eventId: number) => {
      try {
        upsert(await api.getEvent(eventId));
      } catch {
        // Không lấy được chi tiết thì đồng bộ lại cả danh sách.
        void reload();
      }
    },
    [upsert, reload],
  );

  // Ref vì `onReconcile` được giữ nguyên qua các lần render của hook stream.
  const userRef = useRef(user);
  userRef.current = user;

  const { status: streamStatus } = useAlertStream({
    onEventCreated: upsert,
    onEventUpdated: refetchOne,
    onTelemetryReceived: handleTelemetry,
    onReconcile: () => {
      // Chỉ tải khi đã đăng nhập — tránh gọi API rồi nhận 401 ở màn login.
      if (userRef.current) void reload();
    },
  });

  const triggerSimulation = useCallback(async () => {
    try {
      await api.triggerSimulation();
    } catch (err) {
      reportApiError(err);
    }
  }, [reportApiError]);

  const value = useMemo<EventsContextValue>(
    () => ({
      events,
      telemetryMap,
      loading,
      error,
      streamStatus,
      revision,
      reload,
      upsert,
      triggerSimulation,
    }),
    [events, telemetryMap, loading, error, streamStatus, revision, reload, upsert, triggerSimulation],
  );

  return <EventsContext.Provider value={value}>{children}</EventsContext.Provider>;
}

export function useEvents(): EventsContextValue {
  const ctx = useContext(EventsContext);
  if (!ctx) throw new Error('useEvents phải được dùng bên trong <EventsProvider>');
  return ctx;
}
