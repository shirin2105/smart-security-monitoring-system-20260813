import { FormEvent, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AlertCircle, KeyRound, Lock, ShieldCheck, User as UserIcon } from 'lucide-react';

import { isMockMode } from '../api';
import { useAuth } from '../auth/AuthContext';
import { InlineError, LoadingState } from '../components/common/States';

const DEMO_ACCOUNTS = [
  { username: 'guard', password: 'guard123', label: 'Bảo vệ trực', tone: 'text-blue-400' },
  {
    username: 'manager',
    password: 'manager123',
    label: 'Quản lý an ninh',
    tone: 'text-indigo-400',
  },
];

export function LoginPage() {
  const { user, restoring, sessionExpired, login } = useAuth();
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
    <main className="flex min-h-screen items-center justify-center bg-[#0B0F19] p-4">
      <div className="glass-panel w-full max-w-md overflow-hidden rounded-2xl border border-gray-800 bg-gray-900 shadow-2xl">
        <div className="border-b border-gray-800 bg-gradient-to-r from-blue-900/40 via-gray-900 to-indigo-900/40 p-6 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl border border-blue-500/50 bg-blue-600/20 text-blue-400">
            <ShieldCheck className="h-8 w-8" aria-hidden />
          </div>
          <h1 className="text-lg font-bold tracking-wide text-white">
            TRUNG TÂM GIÁM SÁT AN NINH
          </h1>
          <p className="mt-1 text-xs text-gray-400">
            Cảnh báo realtime · Xác nhận bởi người trực
          </p>
          {isMockMode && (
            <p className="mt-2 inline-block rounded border border-violet-500/40 bg-violet-500/20 px-2 py-0.5 font-mono text-[10px] text-violet-300">
              CHẾ ĐỘ DỮ LIỆU GIẢ LẬP — KHÔNG CẦN BACKEND
            </p>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-6" noValidate>
          {sessionExpired && (
            <div
              role="status"
              className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
              <span>Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại để tiếp tục.</span>
            </div>
          )}

          {error != null && <InlineError error={error} />}

          <div>
            <label
              htmlFor="username"
              className="mb-1.5 block font-mono text-xs font-medium uppercase text-gray-300"
            >
              Tên tài khoản
            </label>
            <div className="relative">
              <UserIcon
                className="pointer-events-none absolute inset-y-0 left-3 my-auto h-4 w-4 text-gray-500"
                aria-hidden
              />
              <input
                id="username"
                name="username"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
                className="w-full rounded-lg border border-gray-800 bg-gray-950 py-2.5 pl-9 pr-4 text-sm text-white placeholder-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="guard / manager"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-1.5 block font-mono text-xs font-medium uppercase text-gray-300"
            >
              Mật khẩu
            </label>
            <div className="relative">
              <Lock
                className="pointer-events-none absolute inset-y-0 left-3 my-auto h-4 w-4 text-gray-500"
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
                className="w-full rounded-lg border border-gray-800 bg-gray-950 py-2.5 pl-9 pr-4 text-sm text-white placeholder-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-3 text-sm font-medium text-white transition-all hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
          >
            {submitting ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              <>
                <KeyRound className="h-4 w-4" aria-hidden />
                <span>Đăng nhập</span>
              </>
            )}
          </button>
        </form>

        <div className="border-t border-gray-800/80 bg-gray-950/60 px-6 py-4 text-xs text-gray-400">
          <p className="mb-2 font-semibold text-gray-300">Tài khoản thử nghiệm:</p>
          <div className="grid grid-cols-2 gap-2 font-mono">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.username}
                type="button"
                onClick={() => {
                  setUsername(account.username);
                  setPassword(account.password);
                }}
                className="rounded border border-gray-800 bg-gray-900 p-2 text-left text-[11px] transition-all hover:border-blue-500/50 hover:bg-gray-800/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <div className={`font-bold ${account.tone}`}>{account.label}</div>
                <div className="text-gray-300">
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
