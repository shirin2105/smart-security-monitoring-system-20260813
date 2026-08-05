import { ReactNode } from 'react';
import { Route, Routes } from 'react-router-dom';

import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { AppLayout } from './components/layout/AppLayout';
import { MobileLayout } from './components/mobile/MobileLayout';
import { NotificationCenter } from './notifications/NotificationCenter';
import { EventsProvider } from './realtime/EventsProvider';
import { AuditPage } from './pages/AuditPage';
import { DashboardPage } from './pages/DashboardPage';
import { HeatmapPage } from './pages/HeatmapPage';
import { IncidentDetailPage } from './pages/IncidentDetailPage';
import { IncidentsPage } from './pages/IncidentsPage';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { ManagerInboxPage } from './pages/mobile/ManagerInboxPage';
import { MobileAuditPage } from './pages/mobile/MobileAuditPage';
import { MobileIncidentPage } from './pages/mobile/MobileIncidentPage';
import { Role } from './domain/types';

/**
 * Vỏ chung cho mọi khu vực đã đăng nhập: kênh realtime mở một lần và không bị
 * đóng/mở lại khi chuyển trang, thông báo quan trọng chạy đè lên đó.
 *
 * `basePath` cho trung tâm thông báo biết cần điều hướng tới bản desktop hay
 * bản điện thoại khi người dùng chạm vào một cảnh báo.
 */
function AuthedArea({
  children,
  basePath = '',
  allowRoles,
}: {
  children: ReactNode;
  basePath?: string;
  allowRoles?: Role[];
}) {
  return (
    <ProtectedRoute allowRoles={allowRoles}>
      <EventsProvider>
        <NotificationCenter basePath={basePath}>{children}</NotificationCenter>
      </EventsProvider>
    </ProtectedRoute>
  );
}

export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Bản desktop — trạm trực ban */}
        <Route
          element={
            <AuthedArea>
              <AppLayout />
            </AuthedArea>
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

        {/* Bản điện thoại — Quản lý an ninh trực từ xa */}
        <Route
          path="/m"
          element={
            <AuthedArea basePath="/m" allowRoles={['MANAGER']}>
              <MobileLayout />
            </AuthedArea>
          }
        >
          <Route index element={<ManagerInboxPage />} />
          <Route path="incidents/:id" element={<MobileIncidentPage />} />
          <Route path="audit" element={<MobileAuditPage />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}

export default App;
