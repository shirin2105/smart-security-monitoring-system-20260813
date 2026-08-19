import { Pagination as AstryxPagination } from '@astryxdesign/core/Pagination';
import { HStack, VStack } from '@astryxdesign/core/Stack';
import { Divider } from '@astryxdesign/core/Divider';
import { Text } from '@astryxdesign/core/Text';

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onChange: (page: number) => void;
}

export function Pagination({ page, pageSize, total, onChange }: PaginationProps) {
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);

  return (
    <VStack gap={2} width="100%">
      <Divider />
      <HStack justify="between" vAlign="center" wrap="wrap" gap={3}>
        <Text type="supporting" size="xsm" color="secondary">
          Hiển thị <strong style={{ color: 'var(--color-text-primary)' }}>{first}</strong>–
          <strong style={{ color: 'var(--color-text-primary)' }}>{last}</strong> trong tổng số{' '}
          <strong style={{ color: 'var(--color-text-primary)' }}>{total}</strong> sự cố
        </Text>

        <AstryxPagination
          label="Phân trang danh sách sự cố"
          page={page}
          totalItems={total}
          pageSize={pageSize}
          onChange={onChange}
          variant="pages"
          size="sm"
        />
      </HStack>
    </VStack>
  );
}

