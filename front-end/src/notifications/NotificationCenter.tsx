/**
 * Trung tâm thông báo cho Quản lý an ninh — "Nhận thông báo quan trọng".
 *
 * Hai kênh song song, vì không kênh nào đủ một mình:
 *   - Thông báo hệ thống: tới được cả khi trình duyệt đang ở tab khác hoặc bị
 *     thu nhỏ. Cần quyền, và chỉ chạy trên HTTPS/localhost.
 *   - Thông báo trong ứng dụng: luôn hiện, không cần quyền, nhưng chỉ thấy khi
 *     đang mở app.
 *
 * Chống trùng theo khóa `id:loại`, nên một sự cố nghiêm trọng báo một lần, và
 * khi Bảo vệ xin ý kiến trên chính sự cố đó thì báo thêm một lần nữa — đó là
 * hai việc khác nhau cần Quản lý biết.
 */

import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { alertHeadline, isManagerAlert } from '../domain/notifications';
import { SecurityEvent } from '../domain/types';
import { useEvents } from '../realtime/EventsProvider';
import {
  NotificationPermissionState,
  useNotificationPermission,
} from './useNotificationPermission';

export interface InAppToast {
  key: string;
  event: SecurityEvent;
  headline: string;
}

interface NotificationContextValue {
  toasts: InAppToast[];
  dismiss: (key: string) => void;
  /** Tiền tố route để mở sự cố — '' cho desktop, '/m' cho điện thoại. */
  basePath: string;
  permission: NotificationPermissionState;
  muted: boolean;
  canNotify: boolean;
  shouldPrompt: boolean;
  request: () => Promise<void>;
  toggleMuted: () => void;
}

const NotificationContext = createContext<NotificationContextValue | null>(null);

/** Thông báo trong app tự ẩn sau khoảng này. */
const TOAST_TTL_MS = 10_000;

/** Khóa chống trùng: tách "sự cố nghiêm trọng" và "xin ý kiến" thành 2 việc. */
function alertKey(event: SecurityEvent): string {
  return `${event.id}:${event.escalation === 'REQUESTED' ? 'esc' : 'sev'}`;
}

export function NotificationCenter({
  children,
  basePath = '',
}: {
  children: ReactNode;
  basePath?: string;
}) {
  const { user } = useAuth();
  const { subscribe } = useEvents();
  const permissionApi = useNotificationPermission();
  const navigate = useNavigate();

  const [toasts, setToasts] = useState<InAppToast[]>([]);

  const seenRef = useRef<Set<string>>(new Set());
  const canNotifyRef = useRef(permissionApi.canNotify);
  canNotifyRef.current = permissionApi.canNotify;

  const dismiss = useCallback((key: string) => {
    setToasts((list) => list.filter((toast) => toast.key !== key));
  }, []);

  const emit = useCallback((event: SecurityEvent) => {
    const headline = alertHeadline(event);
    const key = alertKey(event);

    setToasts((list) => [{ key, event, headline }, ...list].slice(0, 3));
    setTimeout(() => dismiss(key), TOAST_TTL_MS);

    if (!canNotifyRef.current) return;

    try {
      const notification = new Notification(headline, {
        body: event.description,
        // `tag` để hệ điều hành gộp thay vì xếp chồng cùng một sự cố.
        tag: key,
        requireInteraction: event.effectiveSeverity === 'CRITICAL',
      });
      notification.onclick = () => {
        window.focus();
        navigate(`${basePath}/incidents/${event.id}`);
        notification.close();
      };
    } catch {
      // Một số trình duyệt chặn constructor Notification; toast vẫn còn.
    }
  }, [dismiss, navigate, basePath]);

  useEffect(() => {
    // Chỉ Quản lý mới nhận nhóm thông báo này.
    if (user?.role !== 'MANAGER') return;

    return subscribe((event) => {
      if (!isManagerAlert(event)) return;

      const key = alertKey(event);
      if (seenRef.current.has(key)) return;
      seenRef.current.add(key);
      emit(event);
    });
  }, [subscribe, user?.role, emit]);

  const value = useMemo<NotificationContextValue>(
    () => ({ toasts, dismiss, basePath, ...permissionApi }),
    [toasts, dismiss, basePath, permissionApi],
  );

  return (
    <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>
  );
}

export function useNotifications(): NotificationContextValue {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    throw new Error('useNotifications phải được dùng bên trong <NotificationCenter>');
  }
  return ctx;
}
