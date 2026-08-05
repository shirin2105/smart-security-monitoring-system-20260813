import { NavLink, Outlet } from 'react-router-dom';
import { Inbox, LogOut, ScrollText, Shield, Wifi, WifiOff } from 'lucide-react';

import { useAuth } from '../../auth/AuthContext';
import { needsManagerDecision } from '../../domain/notifications';
import { ROLE_LABEL, Role } from '../../domain/types';
import { ToastStack } from '../../notifications/ToastStack';
import { useEvents } from '../../realtime/EventsProvider';

interface MobileNavItem {
  to: string;
  label: string;
  icon: typeof Inbox;
  allowRoles: Role[];
  /** Đếm việc còn phải xử lý để hiện badge. */
  badge?: 'managerDecisions';
}

const NAV_ITEMS: MobileNavItem[] = [
  {
    to: '/m',
    label: 'Cần duyệt',
    icon: Inbox,
    allowRoles: ['MANAGER'],
    badge: 'managerDecisions',
  },
  { to: '/m/audit', label: 'Nhật ký', icon: ScrollText, allowRoles: ['MANAGER'] },
];

/**
 * Khung giao diện cho người trực dùng điện thoại.
 *
 * Khác hẳn bản desktop ở chỗ điều hướng nằm ở CẠNH DƯỚI màn hình — vùng ngón
 * cái với tới được khi cầm một tay, còn thanh trên cùng của desktop thì không.
 * Có chừa `safe-area-inset` để không bị thanh home của iPhone che mất.
 */
export function MobileLayout() {
  const { user, logout } = useAuth();
  const { events, streamStatus } = useEvents();

  const pendingDecisions = events.filter(needsManagerDecision).length;
  const visibleNav = NAV_ITEMS.filter((item) => user && item.allowRoles.includes(user.role));
  const online = streamStatus === 'open';

  return (
    <div className="flex min-h-screen flex-col bg-[#0B0F19] text-gray-100">
      <ToastStack />

      <header className="sticky top-0 z-40 flex items-center gap-3 border-b border-gray-800 bg-gray-950/95 px-4 py-3 backdrop-blur">
        <Shield className="h-5 w-5 shrink-0 text-blue-400" aria-hidden />

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold text-white">
            {user ? ROLE_LABEL[user.role] : 'Giám sát an ninh'}
          </p>
          <p className="truncate text-[11px] text-gray-400">{user?.fullName}</p>
        </div>

        <span
          role="status"
          aria-label={online ? 'Đang kết nối realtime' : 'Mất kết nối realtime'}
          className={`flex items-center gap-1 rounded-full border px-2 py-1 text-[10px] font-semibold ${
            online
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
              : 'border-amber-500/30 bg-amber-500/10 text-amber-400'
          }`}
        >
          {online ? (
            <Wifi className="h-3 w-3" aria-hidden />
          ) : (
            <WifiOff className="h-3 w-3" aria-hidden />
          )}
        </span>

        <button
          onClick={logout}
          aria-label="Đăng xuất"
          className="shrink-0 rounded-md p-2 text-gray-400 transition-colors hover:bg-red-500/10 hover:text-red-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
        >
          <LogOut className="h-4 w-4" aria-hidden />
        </button>
      </header>

      {/* pb-24 chừa chỗ cho thanh điều hướng dưới, tránh che nội dung cuối trang. */}
      <main className="flex flex-1 flex-col pb-24">
        <Outlet />
      </main>

      <nav
        aria-label="Điều hướng"
        className="fixed inset-x-0 bottom-0 z-40 border-t border-gray-800 bg-gray-950/95 pb-[env(safe-area-inset-bottom)] backdrop-blur"
      >
        <ul className="flex">
          {visibleNav.map(({ to, label, icon: Icon, badge }) => {
            const count = badge === 'managerDecisions' ? pendingDecisions : 0;

            return (
              <li key={to} className="flex-1">
                <NavLink
                  to={to}
                  end={to === '/m'}
                  className={({ isActive }) =>
                    `flex flex-col items-center gap-1 py-3 text-[11px] font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500 ${
                      isActive ? 'text-blue-400' : 'text-gray-500'
                    }`
                  }
                >
                  <span className="relative">
                    <Icon className="h-5 w-5" aria-hidden />
                    {count > 0 && (
                      <span
                        aria-label={`${count} việc cần xử lý`}
                        className="absolute -right-2.5 -top-1.5 min-w-[18px] rounded-full bg-red-500 px-1 text-center text-[10px] font-bold leading-[18px] text-white"
                      >
                        {count > 9 ? '9+' : count}
                      </span>
                    )}
                  </span>
                  <span>{label}</span>
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}
