import { ReactNode } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Center } from '@astryxdesign/core/Center';
import { VStack } from '@astryxdesign/core/Stack';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';

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
  const navigate = useNavigate();

  if (restoring) {
    return <LoadingState label="Đang khôi phục phiên đăng nhập…" />;
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (allowRoles && !allowRoles.includes(user.role)) {
    const requiredRoles = allowRoles.map((role) => ROLE_LABEL[role]).join(', ');
    return (
      <Center padding={8} minHeight={320}>
        <VStack gap={4} hAlign="center" maxWidth={480} width="100%">
          <Banner
            status="warning"
            container="card"
            title="Không đủ quyền truy cập"
            description={`Trang này chỉ dành cho ${requiredRoles}. Tài khoản của bạn đang ở vai trò ${ROLE_LABEL[user.role]}.`}
            endContent={
              <Button
                label="Quay lại giám sát"
                variant="secondary"
                size="sm"
                onClick={() => navigate('/')}
              />
            }
          />
        </VStack>
      </Center>
    );
  }

  return <>{children}</>;
}

