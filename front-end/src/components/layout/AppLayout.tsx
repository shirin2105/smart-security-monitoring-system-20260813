import { Outlet } from 'react-router-dom';

import { ToastStack } from '../../notifications/ToastStack';
import { useEvents } from '../../realtime/EventsProvider';
import { Navbar } from './Navbar';

/** Khung chung cho mọi trang đã đăng nhập. */
export function AppLayout() {
  const { streamStatus, triggerSimulation } = useEvents();

  return (
    <div className="flex min-h-screen flex-col bg-[#0B0F19] font-sans text-gray-100">
      <ToastStack />
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-blue-600 focus:px-4 focus:py-2 focus:text-sm focus:text-white"
      >
        Bỏ qua điều hướng
      </a>

      <Navbar
        streamStatus={streamStatus}
        onTriggerSimulation={() => void triggerSimulation()}
      />

      {/* min-h-0 để pane con được phép co lại và tự cuộn thay vì đẩy tràn trang. */}
      <main
        id="main-content"
        className="mx-auto flex w-full min-h-0 max-w-[1920px] flex-1 flex-col"
      >
        <Outlet />
      </main>
    </div>
  );
}
