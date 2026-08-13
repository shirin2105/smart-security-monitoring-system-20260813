import { api } from '../api';
import { AlertSidebar } from '../components/alerts/AlertSidebar';
import { CameraGrid } from '../components/camera/CameraGrid';
import { ErrorState, LoadingState } from '../components/common/States';
import { useAsync } from '../hooks/useAsync';
import { useEvents } from '../realtime/EventsProvider';

/** Màn trực ban: lưới camera + hàng chờ cảnh báo realtime. */
export function DashboardPage() {
  const { events, loading, error, reload } = useEvents();
  const cameras = useAsync(() => api.getCameras(), []);

  return (
    <div className="flex flex-1 flex-col gap-6 lg:min-h-0 lg:flex-row lg:overflow-hidden">
      {cameras.loading ? (
        <LoadingState label="Đang tải danh sách camera…" />
      ) : cameras.error != null ? (
        <ErrorState error={cameras.error} onRetry={cameras.reload} />
      ) : (
        <CameraGrid cameras={cameras.data ?? []} events={events} />
      )}

      <AlertSidebar events={events} loading={loading} error={error} onRetry={reload} />
    </div>
  );
}
