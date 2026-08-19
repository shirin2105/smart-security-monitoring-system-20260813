import { Component, ErrorInfo, ReactNode } from 'react';
import { RefreshCw, RotateCcw } from 'lucide-react';
import { Banner } from '@astryxdesign/core/Banner';
import { Center } from '@astryxdesign/core/Center';
import { VStack, HStack } from '@astryxdesign/core/Stack';
import { Button } from '@astryxdesign/core/Button';
import { Text } from '@astryxdesign/core/Text';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: undefined });
  };

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <Center padding={6} minHeight={300}>
          <VStack gap={4} hAlign="center" maxWidth={500} width="100%">
            <Banner
              status="error"
              container="card"
              title="Đã xảy ra sự cố không mong muốn"
              description={this.state.error?.message || 'Có lỗi xảy ra trong quá trình hiển thị giao diện.'}
            >
              <VStack gap={3} padding={3}>
                <Text type="supporting" color="secondary" size="xsm">
                  Vui lòng thử lại hoặc tải lại toàn bộ trang nếu lỗi vẫn tiếp diễn.
                </Text>
                <HStack gap={2}>
                  <Button
                    label="Thử lại"
                    variant="primary"
                    size="sm"
                    icon={<RefreshCw size={14} />}
                    onClick={this.handleReset}
                  />
                  <Button
                    label="Tải lại trang"
                    variant="secondary"
                    size="sm"
                    icon={<RotateCcw size={14} />}
                    onClick={this.handleReload}
                  />
                </HStack>
              </VStack>
            </Banner>
          </VStack>
        </Center>
      );
    }

    return this.props.children;
  }
}
