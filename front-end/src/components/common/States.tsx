/**
 * Empty / loading / error state dùng chung — tuân thủ Astryx Design System.
 */

import { ReactNode } from 'react';
import { RefreshCw } from 'lucide-react';
import { Spinner } from '@astryxdesign/core/Spinner';
import { Center } from '@astryxdesign/core/Center';
import { VStack } from '@astryxdesign/core/Stack';
import { Text } from '@astryxdesign/core/Text';
import { Button } from '@astryxdesign/core/Button';
import { Banner } from '@astryxdesign/core/Banner';

import { ApiError } from '../../api/errors';

export function LoadingState({ label = 'Đang tải dữ liệu…' }: { label?: string }) {
  return (
    <Center padding={8} minHeight={200}>
      <VStack gap={3} hAlign="center" vAlign="center">
        <Spinner size="lg" />
        <Text type="supporting" color="secondary" size="sm">
          {label}
        </Text>
      </VStack>
    </Center>
  );
}

export function EmptyState({
  title,
  hint,
  icon,
}: {
  title: string;
  hint?: string;
  icon?: ReactNode;
}) {
  return (
    <Center padding={8} minHeight={200}>
      <VStack gap={2} hAlign="center" vAlign="center" maxWidth={400}>
        {icon}
        <Text type="body" weight="semibold" color="primary">
          {title}
        </Text>
        {hint && (
          <Text type="supporting" color="secondary" size="xsm" justify="center">
            {hint}
          </Text>
        )}
      </VStack>
    </Center>
  );
}

function describe(error: unknown): { title: string; message: string; status: 'warning' | 'error' | 'info' } {
  if (error instanceof ApiError) {
    switch (error.kind) {
      case 'NETWORK':
        return {
          status: 'warning',
          title: 'Không kết nối được máy chủ',
          message: error.message,
        };
      case 'FORBIDDEN':
        return {
          status: 'warning',
          title: 'Không đủ quyền',
          message: error.message,
        };
      case 'NOT_IMPLEMENTED':
        return {
          status: 'info',
          title: 'Tính năng chưa sẵn sàng ở backend',
          message: error.message,
        };
      default:
        return {
          status: 'error',
          title: 'Đã xảy ra lỗi',
          message: error.message,
        };
    }
  }
  return {
    status: 'error',
    title: 'Đã xảy ra lỗi',
    message: error instanceof Error ? error.message : 'Lỗi không xác định. Vui lòng thử lại.',
  };
}

export function ErrorState({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  const { status, title, message } = describe(error);

  return (
    <Center padding={6} minHeight={200}>
      <VStack gap={4} hAlign="center" maxWidth={480} width="100%">
        <Banner
          status={status}
          title={title}
          description={message}
          container="card"
          endContent={
            onRetry ? (
              <Button
                label="Thử lại"
                variant="secondary"
                size="sm"
                icon={<RefreshCw size={14} />}
                onClick={onRetry}
              />
            ) : undefined
          }
        />
      </VStack>
    </Center>
  );
}

/** Banner lỗi gọn cho thao tác trong form/panel, không chiếm cả màn hình. */
export function InlineError({ error }: { error: unknown }) {
  const { status, title, message } = describe(error);
  return (
    <Banner
      status={status}
      title={title}
      description={message}
      container="card"
    />
  );
}
