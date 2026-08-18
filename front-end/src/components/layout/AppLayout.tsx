import { Outlet } from 'react-router-dom';
import { AppShell } from '@astryxdesign/core/AppShell';

import { useEvents } from '../../realtime/EventsProvider';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { Navbar } from './Navbar';

/**
 * Khung layout chính theo chuẩn Astryx AppShell.
 */
export function AppLayout() {
  const { streamStatus, triggerSimulation } = useEvents();

  return (
    <AppShell
      height="fill"
      variant="elevated"
      contentPadding={0}
      topNav={
        <Navbar
          streamStatus={streamStatus}
          onTriggerSimulation={() => void triggerSimulation()}
        />
      }
    >
      <ErrorBoundary>
        <Outlet />
      </ErrorBoundary>
    </AppShell>
  );
}
