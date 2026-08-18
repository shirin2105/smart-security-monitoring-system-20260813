import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  Clock,
  FlaskConical,
  History,
  LayoutGrid,
  ListFilter,
  LogOut,
  Map as MapIcon,
  Moon,
  Shield,
  Sun,
} from 'lucide-react';

import { TopNav, TopNavHeading, TopNavItem } from '@astryxdesign/core/TopNav';
import { HStack, VStack } from '@astryxdesign/core/Stack';
import { Text } from '@astryxdesign/core/Text';
import { Button } from '@astryxdesign/core/Button';
import { Token } from '@astryxdesign/core/Token';
import { StatusDot } from '@astryxdesign/core/StatusDot';
import { Avatar } from '@astryxdesign/core/Avatar';

import { isMockMode } from '../../api';
import { useAuth } from '../../auth/AuthContext';
import { ROLE_LABEL, Role } from '../../domain/types';
import { StreamStatus } from '../../realtime/useAlertStream';
import { useTheme } from '../../theme/useTheme';

interface NavbarProps {
  streamStatus: StreamStatus;
  onTriggerSimulation: () => void;
}

interface NavItemDef {
  to: string;
  label: string;
  icon: typeof LayoutGrid;
  allowRoles?: Role[];
}

const NAV_ITEMS: NavItemDef[] = [
  { to: '/', label: 'Giám sát', icon: LayoutGrid },
  { to: '/incidents', label: 'Sự cố', icon: ListFilter },
  { to: '/audit', label: 'Nhật ký', icon: History },
  { to: '/heatmap', label: 'Điểm nóng', icon: MapIcon, allowRoles: ['MANAGER'] },
];

const STREAM_DOT_VARIANT: Record<StreamStatus, 'success' | 'accent' | 'warning' | 'error'> = {
  open: 'success',
  connecting: 'accent',
  reconnecting: 'warning',
  offline: 'error',
};

const STREAM_LABEL: Record<StreamStatus, string> = {
  open: 'Realtime: đã kết nối',
  connecting: 'Realtime: đang mở…',
  reconnecting: 'Realtime: kết nối lại…',
  offline: 'Realtime: ngắt kết nối',
};

export function Navbar({ streamStatus, onTriggerSimulation }: NavbarProps) {
  const { user, logout } = useAuth();
  const { setTheme, actualTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const [time, setTime] = useState('');

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(
        `${now.toLocaleTimeString('vi-VN', { hour12: false })} · ${now.toLocaleDateString('vi-VN')}`,
      );
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, []);

  const visibleNav = NAV_ITEMS.filter(
    (item) => !item.allowRoles || (user && item.allowRoles.includes(user.role)),
  );

  const toggleTheme = () => {
    setTheme(actualTheme === 'dark' ? 'light' : 'dark');
  };

  return (
    <TopNav
      label="Điều hướng chính"
      heading={
        <TopNavHeading
          logo={<Shield size={22} />}
          heading="TRUNG TÂM GIÁM SÁT AN NINH"
          subheading="Cảnh báo realtime · Xác nhận bởi người trực (HITL)"
          headerEndContent={
            isMockMode ? (
              <Token
                color="purple"
                size="sm"
                icon={<FlaskConical size={12} />}
                label="GIẢ LẬP"
              />
            ) : undefined
          }
        />
      }
      startContent={
        <HStack gap={1} vAlign="center" style={{ flexWrap: 'nowrap' }}>
          {visibleNav.map(({ to, label, icon: IconComponent }) => {
            const isSelected = to === '/' ? location.pathname === '/' : location.pathname.startsWith(to);
            return (
              <TopNavItem
                key={to}
                label={label}
                href={to}
                isSelected={isSelected}
                icon={<IconComponent size={16} />}
                onClick={(e) => {
                  e.preventDefault();
                  navigate(to);
                }}
              />
            );
          })}
        </HStack>
      }
      endContent={
        <HStack gap={2} vAlign="center" style={{ flexWrap: 'nowrap' }}>
          {/* Clock */}
          <HStack gap={1} vAlign="center" paddingInline={2} paddingBlock={1} style={{ whiteSpace: 'nowrap' }}>
            <Clock size={14} />
            <Text type="code" size="xsm" color="secondary">
              {time}
            </Text>
          </HStack>

          {/* Realtime stream status */}
          <HStack gap={1.5} vAlign="center" paddingInline={2} paddingBlock={1} style={{ whiteSpace: 'nowrap' }}>
            <StatusDot variant={STREAM_DOT_VARIANT[streamStatus]} label={STREAM_LABEL[streamStatus]} />
            <Text type="label" size="xsm" color="secondary">
              {STREAM_LABEL[streamStatus]}
            </Text>
          </HStack>

          {/* Simulation button */}
          <Button
            label="Giả lập cảnh báo"
            variant="secondary"
            size="sm"
            icon={<AlertTriangle size={14} />}
            onClick={onTriggerSimulation}
          />

          {/* Theme switcher */}
          <Button
            variant="ghost"
            size="sm"
            isIconOnly
            label={`Chuyển sang giao diện ${actualTheme === 'dark' ? 'Sáng' : 'Tối'}`}
            icon={actualTheme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            onClick={toggleTheme}
          />

          {/* User profile */}
          {user && (
            <HStack gap={2} vAlign="center" style={{ whiteSpace: 'nowrap' }}>
              <Avatar name={user.fullName} size="sm" />
              <VStack gap={0}>
                <Text type="label" size="xsm" weight="semibold">
                  {user.fullName}
                </Text>
                <Text type="supporting" color="secondary">
                  {ROLE_LABEL[user.role]}
                </Text>
              </VStack>
              <Button
                variant="ghost"
                size="sm"
                isIconOnly
                label="Đăng xuất"
                icon={<LogOut size={16} />}
                onClick={logout}
              />
            </HStack>
          )}
        </HStack>
      }
    />
  );
}
