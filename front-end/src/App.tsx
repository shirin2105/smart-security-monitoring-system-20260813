import { Route, Routes } from 'react-router-dom';

import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { AppLayout } from './components/layout/AppLayout';
import { ToastProvider } from './components/common/ToastProvider';
import { EventsProvider } from './realtime/EventsProvider';
import { ThemeProvider } from './theme/ThemeProvider';
import { NotificationToast } from './components/common/NotificationToast';
import { AuditPage } from './pages/AuditPage';
import { DashboardPage } from './pages/DashboardPage';
import { HeatmapPage } from './pages/HeatmapPage';
import { IncidentDetailPage } from './pages/IncidentDetailPage';
import { IncidentsPage } from './pages/IncidentsPage';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';

/**
 * Web là màn hình của trạm trực ban: bảo vệ trực ca xem 6 camera và xử lý sự cố.
 */
export function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            {/*
              EventsProvider nằm trong ProtectedRoute nên kênh realtime chỉ mở sau
              khi đăng nhập, và không bị đóng/mở lại khi chuyển trang.
            */}
            <Route
              element={
                <ProtectedRoute>
                  <EventsProvider>
                    <NotificationToast />
                    <AppLayout />
                  </EventsProvider>
                </ProtectedRoute>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="incidents" element={<IncidentsPage />} />
              <Route path="incidents/:id" element={<IncidentDetailPage />} />
              <Route path="audit" element={<AuditPage />} />
              <Route
                path="heatmap"
                element={
                  <ProtectedRoute allowRoles={['MANAGER']}>
                    <HeatmapPage />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
