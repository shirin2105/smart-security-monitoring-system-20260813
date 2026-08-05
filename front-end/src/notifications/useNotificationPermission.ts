/**
 * Quản lý quyền gửi thông báo hệ thống.
 *
 * Ba ràng buộc của trình duyệt cần nhớ:
 *   - `Notification.requestPermission()` chỉ được gọi từ thao tác của người
 *     dùng, không tự xin lúc tải trang.
 *   - API chỉ hoạt động trên HTTPS hoặc localhost. Mở dashboard qua IP LAN
 *     (http://192.168.x.x) sẽ không có Notification — lúc đó rơi về thông báo
 *     trong ứng dụng.
 *   - Người dùng từ chối rồi thì không xin lại được, phải vào cài đặt trình duyệt.
 */

import { useCallback, useEffect, useState } from 'react';

export type NotificationPermissionState =
  | 'unsupported'
  | 'default'
  | 'granted'
  | 'denied';

const MUTE_STORAGE_KEY = 'sec_notify_muted';

function readPermission(): NotificationPermissionState {
  if (typeof window === 'undefined' || !('Notification' in window)) {
    return 'unsupported';
  }
  return Notification.permission as NotificationPermissionState;
}

export function useNotificationPermission() {
  const [permission, setPermission] = useState<NotificationPermissionState>(readPermission);
  const [muted, setMuted] = useState(
    () => localStorage.getItem(MUTE_STORAGE_KEY) === 'true',
  );

  // Người dùng có thể đổi quyền trong cài đặt trình duyệt mà không reload.
  useEffect(() => {
    if (permission === 'unsupported' || !navigator.permissions?.query) return;

    let status: PermissionStatus | null = null;
    const sync = () => setPermission(readPermission());

    navigator.permissions
      .query({ name: 'notifications' as PermissionName })
      .then((result) => {
        status = result;
        result.addEventListener('change', sync);
      })
      .catch(() => {
        // Một số trình duyệt không cho query quyền notifications — bỏ qua.
      });

    return () => status?.removeEventListener('change', sync);
  }, [permission]);

  const request = useCallback(async () => {
    if (readPermission() === 'unsupported') return;
    try {
      const result = await Notification.requestPermission();
      setPermission(result as NotificationPermissionState);
    } catch {
      setPermission(readPermission());
    }
  }, []);

  const toggleMuted = useCallback(() => {
    setMuted((previous) => {
      const next = !previous;
      localStorage.setItem(MUTE_STORAGE_KEY, String(next));
      return next;
    });
  }, []);

  return {
    permission,
    muted,
    /** Đủ điều kiện bắn thông báo hệ thống. */
    canNotify: permission === 'granted' && !muted,
    /** Nên hiện lời mời bật thông báo. */
    shouldPrompt: permission === 'default',
    request,
    toggleMuted,
  };
}
