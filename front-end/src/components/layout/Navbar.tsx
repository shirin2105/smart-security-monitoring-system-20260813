import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  AlertTriangle,
  Clock,
  FlaskConical,
  History,
  LayoutGrid,
  ListFilter,
  LogOut,
  Map as MapIcon,
  Moon,
  Shield,
  Sun,
  User as UserIcon,
  Wifi,
  WifiOff,
} from 'lucide-react';

import { isMockMode } from '../../api';
import { useAuth } from '../../auth/AuthContext';
import { ROLE_LABEL, Role } from '../../domain/types';
import { StreamStatus } from '../../realtime/useAlertStream';
import { useTheme } from '../../theme/useTheme';

interface NavbarProps {
  streamStatus: StreamStatus;
  onTriggerSimulation: () => void;
}

interface NavItem {
  to: string;
  label: string;
  icon: typeof LayoutGrid;
  allowRoles?: Role[];
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Giám sát', icon: LayoutGrid },
  { to: '/incidents', label: 'Sự cố', icon: ListFilter },
  { to: '/audit', label: 'Nhật ký', icon: History },
  { to: '/heatmap', label: 'Điểm nóng', icon: MapIcon, allowRoles: ['MANAGER'] },
];

const STREAM_VIEW: Record<StreamStatus, { text: string; className: string }> = {
  open: {
    text: 'Realtime: đang kết nối',
    className:
      'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30',
  },
  connecting: {
    text: 'Realtime: đang mở kênh…',
    className: 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/30',
  },
  reconnecting: {
    text: 'Realtime: đang kết nối lại…',
    className: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30',
  },
  offline: {
    text: 'Realtime: mất kết nối',
    className: 'bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/30',
  },
};

export function Navbar({ streamStatus, onTriggerSimulation }: NavbarProps) {
  const { user, logout } = useAuth();
  const { setTheme, actualTheme } = useTheme();
  const [time, setTime] = useState('');

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(
        `${now.toLocaleTimeString('vi-VN', { hour12: false })} · ${now.toLocaleDateString('vi-VN')}`,
      );
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, []);

  const stream = STREAM_VIEW[streamStatus];
  const visibleNav = NAV_ITEMS.filter(
    (item) => !item.allowRoles || (user && item.allowRoles.includes(user.role)),
  );

  const toggleTheme = () => {
    if (actualTheme === 'dark') {
      setTheme('light');
    } else {
      setTheme('dark');
    }
  };

  return (
    <header className="glass-panel sticky top-0 z-40 border-b border-gray-200 dark:border-gray-800 px-4 py-3 md:px-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Thương hiệu */}
        <div className="flex items-center gap-3">
          <div className="rounded-xl border border-blue-500/40 bg-blue-600/10 dark:bg-blue-600/20 p-2 text-blue-600 dark:text-blue-400 shadow-sm">
            <Shield className="h-5 w-5" aria-hidden />
          </div>
          <div>
            <h1 className="flex items-center gap-2 text-base font-bold tracking-wide text-gray-900 dark:text-white">
              TRUNG TÂM GIÁM SÁT AN NINH
              {isMockMode && (
                <span className="flex items-center gap-1 rounded-md border border-violet-500/40 bg-violet-500/10 dark:bg-violet-500/20 px-2 py-0.5 font-mono text-[10px] font-semibold text-violet-700 dark:text-violet-300">
                  <FlaskConical className="h-3 w-3" aria-hidden />
                  DỮ LIỆU GIẢ LẬP
                </span>
              )}
            </h1>
            <p className="text-[11px] text-gray-500 dark:text-gray-400">
              Cảnh báo realtime · Xác nhận bởi người trực (HITL)
            </p>
          </div>
        </div>

        {/* Điều hướng */}
        <nav aria-label="Điều hướng chính" className="order-3 w-full lg:order-none lg:w-auto">
          <ul className="flex items-center gap-1">
            {visibleNav.map(({ to, label, icon: Icon }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    `flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                      isActive
                        ? 'border border-blue-500/40 bg-blue-50 dark:bg-blue-600/25 text-blue-700 dark:text-blue-200 shadow-sm'
                        : 'border border-transparent text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/70 hover:text-gray-900 dark:hover:text-gray-100'
                    }`
                  }
                >
                  <Icon className="h-3.5 w-3.5" aria-hidden />
                  <span>{label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* Trạng thái + tài khoản + Theme Switcher */}
        <div className="flex items-center gap-2">
          {/* Clock */}
          <div className="hidden items-center gap-1.5 rounded-lg border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 px-3 py-1.5 font-mono text-xs text-gray-700 dark:text-gray-300 shadow-sm xl:flex">
            <Clock className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" aria-hidden />
            <span>{time}</span>
          </div>

          {/* Theme Switcher button */}
          <button
            onClick={toggleTheme}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 shadow-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            title={`Chuyển sang giao diện ${actualTheme === 'dark' ? 'Sáng' : 'Tối'}`}
            aria-label="Đổi giao diện"
          >
            {actualTheme === 'dark' ? (
              <Sun className="h-4 w-4 text-amber-400" />
            ) : (
              <Moon className="h-4 w-4 text-slate-700" />
            )}
          </button>

          {/* Realtime Status Indicator */}
          <div
            role="status"
            aria-live="polite"
            className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-semibold ${stream.className}`}
          >
            {streamStatus === 'open' ? (
              <Wifi className="h-3.5 w-3.5" aria-hidden />
            ) : (
              <WifiOff className="h-3.5 w-3.5" aria-hidden />
            )}
            <span className="hidden sm:inline">{stream.text}</span>
          </div>

          {/* Simulation button */}
          <button
            onClick={onTriggerSimulation}
            className="flex items-center gap-1.5 rounded-lg border border-amber-500/40 bg-amber-500/10 dark:bg-amber-600/20 px-3 py-1.5 text-xs font-semibold text-amber-700 dark:text-amber-300 transition-all hover:bg-amber-500/20 dark:hover:bg-amber-600/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 active:scale-95 shadow-sm"
            title="Sinh một sự cố giả lập để thử luồng cảnh báo realtime"
          >
            <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
            <span className="hidden md:inline">Giả lập cảnh báo</span>
          </button>

          {/* User badge */}
          {user && (
            <div className="flex items-center gap-2 border-l border-gray-200 dark:border-gray-800 pl-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full border border-blue-500/50 bg-blue-600/10 dark:bg-blue-600/30 text-blue-600 dark:text-blue-300 font-semibold shadow-sm">
                <UserIcon className="h-4 w-4" aria-hidden />
              </div>
              <div className="hidden text-left lg:block">
                <div className="text-xs font-semibold text-gray-900 dark:text-white">
                  {user.fullName}
                </div>
                <div className="font-mono text-[10px] uppercase text-gray-500 dark:text-gray-400">
                  {ROLE_LABEL[user.role]}
                </div>
              </div>
              <button
                onClick={logout}
                className="rounded-lg p-2 text-gray-500 dark:text-gray-400 transition-colors hover:bg-red-50 dark:hover:bg-red-500/10 hover:text-red-600 dark:hover:text-red-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
                title="Đăng xuất"
                aria-label="Đăng xuất"
              >
                <LogOut className="h-4 w-4" aria-hidden />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
