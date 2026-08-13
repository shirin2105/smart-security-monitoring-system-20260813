import { DependencyList, useCallback, useEffect, useState } from 'react';

import { useAuth } from '../auth/AuthContext';

interface AsyncState<T> {
  data: T | null;
  error: unknown;
  loading: boolean;
  reload: () => void;
  /** Cập nhật data tại chỗ (ví dụ sau khi POST action thành công). */
  setData: (updater: (previous: T | null) => T | null) => void;
}

/**
 * Gói loading/error/reload cho mọi lời gọi API, và tự báo 401 lên AuthContext
 * để phiên hết hạn được xử lý ở một chỗ duy nhất (BAC-52).
 */
export function useAsync<T>(fn: () => Promise<T>, deps: DependencyList): AsyncState<T> {
  const { reportApiError } = useAuth();
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fn()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (cancelled) return;
        reportApiError(err);
        setError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // `fn` được tạo mới mỗi render nên cố tình không đưa vào deps.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const reload = useCallback(() => setNonce((value) => value + 1), []);

  const patch = useCallback((updater: (previous: T | null) => T | null) => {
    setData((previous) => updater(previous));
  }, []);

  return { data, error, loading, reload, setData: patch };
}
