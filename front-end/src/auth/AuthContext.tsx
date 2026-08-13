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

import { api, bindAuth } from '../api';
import { TOKEN_STORAGE_KEY, USER_STORAGE_KEY } from '../api/config';
import { ApiError } from '../api/errors';
import { Role, User } from '../domain/types';

interface AuthContextValue {
  user: User | null;
  token: string | null;
  /** Đang khôi phục phiên từ localStorage. */
  restoring: boolean;
  /** Phiên vừa hết hạn — LoginPage hiển thị thông báo tương ứng. */
  sessionExpired: boolean;
  login(username: string, password: string): Promise<void>;
  logout(): void;
  /** Gọi khi bắt được lỗi API; tự đăng xuất nếu là 401. */
  reportApiError(error: unknown): void;
  hasRole(role: Role): boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredUser(): User | null {
  const raw = localStorage.getItem(USER_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    localStorage.removeItem(USER_STORAGE_KEY);
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);

  // Ref để `bindAuth` luôn đọc được giá trị mới nhất mà không phải rebind.
  const userRef = useRef<User | null>(null);
  const tokenRef = useRef<string | null>(null);
  userRef.current = user;
  tokenRef.current = token;

  useEffect(() => {
    bindAuth(
      () => tokenRef.current,
      () => userRef.current,
    );
  }, []);

  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
    const storedUser = readStoredUser();
    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(storedUser);
    }
    setRestoring(false);
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const result = await api.login(username, password);
    localStorage.setItem(TOKEN_STORAGE_KEY, result.token);
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(result.user));
    // Cập nhật ref ngay để request phát sinh trong cùng tick đã có token.
    tokenRef.current = result.token;
    userRef.current = result.user;
    setToken(result.token);
    setUser(result.user);
    setSessionExpired(false);
  }, []);

  const reportApiError = useCallback(
    (error: unknown) => {
      if (error instanceof ApiError && error.kind === 'UNAUTHORIZED') {
        logout();
        setSessionExpired(true);
      }
    },
    [logout],
  );

  const hasRole = useCallback((role: Role) => user?.role === role, [user]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      restoring,
      sessionExpired,
      login,
      logout,
      reportApiError,
      hasRole,
    }),
    [user, token, restoring, sessionExpired, login, logout, reportApiError, hasRole],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth phải được dùng bên trong <AuthProvider>');
  return ctx;
}
