import { FormEvent, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AlertCircle, KeyRound, Lock, ShieldCheck, Sun, Moon, User as UserIcon } from 'lucide-react';

import { isMockMode } from '../api';
import { useAuth } from '../auth/AuthContext';
import { InlineError, LoadingState } from '../components/common/States';
import { useTheme } from '../theme/useTheme';

const DEMO_ACCOUNTS = [
  { username: 'guard', password: 'guard123', label: 'Bảo vệ trực', tone: 'text-blue-600 dark:text-blue-400' },
  {
    username: 'manager',
    password: 'manager123',
    label: 'Quản lý an ninh',
    tone: 'text-indigo-600 dark:text-indigo-400',
  },
];

export function LoginPage() {
  const { user, restoring, sessionExpired, login } = useAuth();
  const { actualTheme, setTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState('guard');
  const [password, setPassword] = useState('guard123');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<unknown>(null);

  if (restoring) return <LoadingState label="Đang kiểm tra phiên đăng nhập…" />;

  if (user) {
    const from = (location.state as { from?: string } | null)?.from ?? '/';
    return <Navigate to={from} replace />;
  }

  const toggleTheme = () => {
    setTheme(actualTheme === 'dark' ? 'light' : 'dark');
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (submitting) return;

    setSubmitting(true);
    setError(null);
    try {
      await login(username, password);
      const from = (location.state as { from?: string } | null)?.from ?? '/';
      navigate(from, { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="relative flex min-h-screen items-center justify-center bg-slate-100 dark:bg-[#0B0F19] p-4 transition-colors duration-200">
      {/* Theme toggle button on top right */}
      <button
        onClick={toggleTheme}
        className="absolute top-4 right-4 flex h-10 w-10 items-center justify-center rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 shadow-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-all focus:outline-none"
        title="Đổi giao diện"
      >
        {actualTheme === 'dark' ? <Sun className="h-5 w-5 text-amber-400" /> : <Moon className="h-5 w-5 text-slate-700" />}
      </button>

      <div className="glass-panel w-full max-w-md overflow-hidden rounded-3xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-2xl">
        <div className="border-b border-gray-200 dark:border-gray-800 bg-gradient-to-r from-blue-500/10 via-slate-50 to-indigo-500/10 dark:from-blue-900/40 dark:via-gray-900 dark:to-indigo-900/40 p-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-blue-500/40 bg-blue-600/10 dark:bg-blue-600/20 text-blue-600 dark:text-blue-400 shadow-sm">
            <ShieldCheck className="h-9 w-9" aria-hidden />
          </div>
          <h1 className="text-xl font-extrabold tracking-wide text-gray-900 dark:text-white">
            TRUNG TÂM GIÁM SÁT AN NINH
          </h1>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Cảnh báo realtime · Xác nhận bởi người trực (HITL)
          </p>
          {isMockMode && (
            <p className="mt-3 inline-block rounded-md border border-violet-300 dark:border-violet-500/40 bg-violet-50 dark:bg-violet-500/20 px-2.5 py-1 font-mono text-[10px] font-bold text-violet-700 dark:text-violet-300">
              CHẾ ĐỘ DỮ LIỆU GIẢ LẬP — KHÔNG CẦN BACKEND
            </p>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-8" noValidate>
          {sessionExpired && (
            <div
              role="status"
              className="flex items-start gap-2 rounded-xl border border-amber-300 dark:border-amber-500/30 bg-amber-50 dark:bg-amber-500/10 p-3.5 text-xs text-amber-800 dark:text-amber-300"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden />
              <span>Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại để tiếp tục.</span>
            </div>
          )}

          {error != null && <InlineError error={error} />}

          <div>
            <label
              htmlFor="username"
              className="mb-1.5 block font-mono text-xs font-bold uppercase text-gray-700 dark:text-gray-300"
            >
              Tên tài khoản
            </label>
            <div className="relative">
              <UserIcon
                className="pointer-events-none absolute inset-y-0 left-3.5 my-auto h-4 w-4 text-gray-400 dark:text-gray-500"
                aria-hidden
              />
              <input
                id="username"
                name="username"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
                className="w-full rounded-xl border border-gray-300 dark:border-gray-800 bg-slate-50 dark:bg-gray-950 py-3 pl-10 pr-4 text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm"
                placeholder="guard / manager"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-1.5 block font-mono text-xs font-bold uppercase text-gray-700 dark:text-gray-300"
            >
              Mật khẩu
            </label>
            <div className="relative">
              <Lock
                className="pointer-events-none absolute inset-y-0 left-3.5 my-auto h-4 w-4 text-gray-400 dark:text-gray-500"
                aria-hidden
              />
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                className="w-full rounded-xl border border-gray-300 dark:border-gray-800 bg-slate-50 dark:bg-gray-950 py-3 pl-10 pr-4 text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 py-3.5 text-sm font-bold text-white transition-all hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 shadow-lg active:scale-98"
          >
            {submitting ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              <>
                <KeyRound className="h-4 w-4" aria-hidden />
                <span>Đăng nhập hệ thống</span>
              </>
            )}
          </button>
        </form>

        <div className="border-t border-gray-200 dark:border-gray-800/80 bg-slate-50 dark:bg-gray-950/60 px-8 py-5 text-xs text-gray-500 dark:text-gray-400">
          <p className="mb-2.5 font-bold text-gray-700 dark:text-gray-300">Tài khoản mẫu dùng thử:</p>
          <div className="grid grid-cols-2 gap-2.5 font-mono">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.username}
                type="button"
                onClick={() => {
                  setUsername(account.username);
                  setPassword(account.password);
                }}
                className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-2.5 text-left text-[11px] transition-all hover:border-blue-400 dark:hover:border-blue-500/50 hover:bg-slate-50 dark:hover:bg-gray-800/60 shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <div className={`font-bold ${account.tone}`}>{account.label}</div>
                <div className="mt-0.5 text-gray-600 dark:text-gray-300 font-semibold">
                  {account.username} / {account.password}
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
