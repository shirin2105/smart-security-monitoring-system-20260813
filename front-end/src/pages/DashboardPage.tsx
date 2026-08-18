import { api } from '../api';
import { AlertSidebar } from '../components/alerts/AlertSidebar';
import { CameraGrid } from '../components/camera/CameraGrid';
import { ErrorState, LoadingState } from '../components/common/States';
import { useAsync } from '../hooks/useAsync';
import { useEvents } from '../realtime/EventsProvider';
import { Layout, LayoutContent, LayoutPanel } from '@astryxdesign/core/Layout';

/**
 * Màn trực ban: lưới camera trong LayoutContent + hàng chờ cảnh báo realtime trong LayoutPanel.
 */
export function DashboardPage() {
  const { events, loading, error, reload } = useEvents();
  const cameras = useAsync(() => api.getCameras(), []);

  return (
    <Layout
      height="fill"
      content={
        <LayoutContent isScrollable padding={3}>
          {cameras.loading ? (
            <LoadingState label="Đang tải danh sách camera…" />
          ) : cameras.error != null ? (
            <ErrorState error={cameras.error} onRetry={cameras.reload} />
          ) : (
            <CameraGrid cameras={cameras.data ?? []} events={events} />
          )}
        </LayoutContent>
      }
      end={
        <LayoutPanel width={420} isScrollable={false} padding={0} hasDivider>
          <AlertSidebar events={events} loading={loading} error={error} onRetry={reload} />
        </LayoutPanel>
      }
    />
  );
}
