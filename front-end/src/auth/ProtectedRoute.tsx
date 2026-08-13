import { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { ShieldOff } from 'lucide-react';

import { ROLE_LABEL, Role } from '../domain/types';
import { useAuth } from './AuthContext';
import { LoadingState } from '../components/common/States';

interface ProtectedRouteProps {
  children: ReactNode;
  /** Bỏ trống = mọi user đã đăng nhập đều vào được. */
  allowRoles?: Role[];
}

/**
 * Chặn route theo đăng nhập + role.
 *
 * Lưu ý: đây chỉ là điều hướng cho đúng trải nghiệm. Quyền thật phải do backend
 * enforce — FR-BE-05 ghi rõ "UI hiding không là security control".
 */
export function ProtectedRoute({ children, allowRoles }: ProtectedRouteProps) {
  const { user, restoring } = useAuth();
  const location = useLocation();

  if (restoring) {
    return <LoadingState label="Đang khôi phục phiên đăng nhập…" />;
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (allowRoles && !allowRoles.includes(user.role)) {
    return (
      <div className="flex flex-1 items-center justify-center p-10">
        <div className="max-w-md rounded-2xl border border-amber-500/40 bg-amber-950/20 p-8 text-center">
          <ShieldOff className="mx-auto mb-4 h-10 w-10 text-amber-400" />
          <h2 className="mb-2 text-base font-bold text-white">
            Không đủ quyền truy cập
          </h2>
          <p className="text-sm leading-relaxed text-gray-300">
            Trang này chỉ dành cho{' '}
            <strong className="text-amber-300">
              {allowRoles.map((role) => ROLE_LABEL[role]).join(', ')}
            </strong>
            . Tài khoản của bạn đang ở vai trò{' '}
            <strong className="text-gray-100">{ROLE_LABEL[user.role]}</strong>.
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
