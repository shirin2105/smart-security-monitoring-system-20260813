import { FormEvent, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { KeyRound, ShieldCheck, Sun, Moon } from 'lucide-react';

import { Card } from '@astryxdesign/core/Card';
import { Center } from '@astryxdesign/core/Center';
import { HStack, VStack } from '@astryxdesign/core/Stack';
import { Text, Heading } from '@astryxdesign/core/Text';
import { TextInput } from '@astryxdesign/core/TextInput';
import { Button } from '@astryxdesign/core/Button';
import { Banner } from '@astryxdesign/core/Banner';
import { Token } from '@astryxdesign/core/Token';
import { Divider } from '@astryxdesign/core/Divider';

import { isMockMode } from '../api';
import { useAuth } from '../auth/AuthContext';
import { InlineError, LoadingState } from '../components/common/States';
import { useTheme } from '../theme/useTheme';

const DEMO_ACCOUNTS = [
  { username: 'guard', password: 'guard123', label: 'Bảo vệ trực', color: 'blue' as const },
  { username: 'manager', password: 'manager123', label: 'Quản lý an ninh', color: 'purple' as const },
];

export function LoginPage() {
  const { user, restoring, sessionExpired, login } = useAuth();
  const { actualTheme, setTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState('guard');
  const [password, setPassword] = useState('guard123');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<unknown>(null);

  if (restoring) return <LoadingState label="Đang kiểm tra phiên đăng nhập…" />;

  if (user) {
    const from = (location.state as { from?: string } | null)?.from ?? '/';
    return <Navigate to={from} replace />;
  }

  const toggleTheme = () => {
    setTheme(actualTheme === 'dark' ? 'light' : 'dark');
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (submitting) return;

    setSubmitting(true);
    setError(null);
    try {
      await login(username, password);
      const from = (location.state as { from?: string } | null)?.from ?? '/';
      navigate(from, { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Center minHeight="100dvh" padding={4}>
      <VStack gap={3} maxWidth={440} width="100%">
        {/* Theme toggle in top bar */}
        <HStack justify="end" width="100%">
          <Button
            variant="secondary"
            size="sm"
            isIconOnly
            label="Đổi giao diện"
            icon={actualTheme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            onClick={toggleTheme}
          />
        </HStack>

        <Card elevation="high" padding={0}>
          {/* Header */}
          <VStack gap={2} hAlign="center" paddingBlock={6} paddingInline={6}>
            <ShieldCheck size={36} color="var(--color-primary)" />
            <Heading level={1}>
              TRUNG TÂM GIÁM SÁT AN NINH
            </Heading>
            <Text type="supporting" color="secondary">
              Hệ thống giám sát an ninh thời gian thực & hỗ trợ ra quyết định (HITL)
            </Text>
            {isMockMode && (
              <Token
                size="sm"
                color="purple"
                label="CHẾ ĐỘ DÙNG THỬ — DỮ LIỆU MẪU"
              />
            )}
          </VStack>

          <Divider />

          {/* Form */}
          <form onSubmit={handleSubmit} noValidate>
            <VStack gap={4} padding={6}>
              {sessionExpired && (
                <Banner
                  status="warning"
                  container="card"
                  title="Phiên làm việc đã hết hạn"
                  description="Vui lòng đăng nhập lại để tiếp tục."
                />
              )}

              {error != null && <InlineError error={error} />}

              <TextInput
                label="Tên tài khoản"
                isRequired
                value={username}
                onChange={(val) => setUsername(val)}
                placeholder="guard / manager"
              />

              <TextInput
                label="Mật khẩu"
                type="password"
                isRequired
                value={password}
                onChange={(val) => setPassword(val)}
                placeholder="••••••••"
              />

              <Button
                label="Đăng nhập hệ thống"
                type="submit"
                variant="primary"
                size="lg"
                width="100%"
                isLoading={submitting}
                icon={<KeyRound size={16} />}
              />
            </VStack>
          </form>

          <Divider />

          {/* Demo accounts footer */}
          <VStack gap={2} paddingInline={6} paddingBlock={4}>
            <Text type="label" size="xsm" weight="bold" color="secondary">
              TÀI KHOẢN MẪU DÙNG THỬ:
            </Text>
            <HStack gap={2} width="100%">
              {DEMO_ACCOUNTS.map((account) => (
                <div key={account.username} style={{ flex: 1 }}>
                  <Button
                    label={`${account.label} (${account.username})`}
                    variant="secondary"
                    size="sm"
                    width="100%"
                    onClick={() => {
                      setUsername(account.username);
                      setPassword(account.password);
                    }}
                  />
                </div>
              ))}
            </HStack>
          </VStack>
        </Card>
      </VStack>
    </Center>
  );
}

