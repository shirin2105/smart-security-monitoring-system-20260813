import { useNavigate } from 'react-router-dom';
import { Compass } from 'lucide-react';

import { Center } from '@astryxdesign/core/Center';
import { VStack } from '@astryxdesign/core/Stack';
import { Text, Heading } from '@astryxdesign/core/Text';
import { Button } from '@astryxdesign/core/Button';

export function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <Center padding={8} minHeight={400}>
      <VStack gap={3} hAlign="center" vAlign="center" maxWidth={400}>
        <Compass size={48} color="var(--color-text-disabled)" />
        <Heading level={1}>
          Không tìm thấy trang
        </Heading>
        <Text type="supporting" color="secondary" size="xsm" justify="center">
          Đường dẫn bạn truy cập không tồn tại hoặc đã được thay đổi.
        </Text>
        <Button
          label="Về màn hình giám sát"
          variant="primary"
          size="sm"
          onClick={() => navigate('/')}
        />
      </VStack>
    </Center>
  );
}
