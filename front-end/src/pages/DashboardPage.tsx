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

  // Dưới lg bố cục xếp dọc và để cả trang cuộn. Chỉ từ lg mới khóa chiều cao
  // để hai pane tự cuộn riêng — nếu khóa ở mọi breakpoint thì trên tablet
  // sidebar sẽ bị cắt và không cuộn tới được.
  return (
    <div className="flex flex-1 flex-col gap-6 p-4 md:p-6 lg:min-h-0 lg:flex-row lg:overflow-hidden">
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
