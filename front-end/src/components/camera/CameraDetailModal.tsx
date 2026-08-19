import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { VideoOff } from 'lucide-react';

import { Dialog, DialogHeader } from '@astryxdesign/core/Dialog';
import { Card } from '@astryxdesign/core/Card';
import { HStack, VStack } from '@astryxdesign/core/Stack';
import { Text } from '@astryxdesign/core/Text';
import { AspectRatio } from '@astryxdesign/core/AspectRatio';

import { Camera, SecurityEvent } from '../../domain/types';
import { EmptyState } from '../common/States';
import { HealthDot, SeverityBadge, SourceBadge, StateBadge } from '../common/Badges';
import { LiveCameraVideo } from './LiveCameraVideo';

interface CameraDetailModalProps {
  camera: Camera;
  events: SecurityEvent[];
  onClose: () => void;
}

export function CameraDetailModal({ camera, events, onClose }: CameraDetailModalProps) {
  const navigate = useNavigate();

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  return (
    <Dialog
      isOpen={true}
      onOpenChange={(isOpen) => {
        if (!isOpen) onClose();
      }}
      width={840}
      maxHeight="90vh"
      purpose="info"
    >
      <DialogHeader
        title={camera.name}
        subtitle={camera.location}
        endContent={
          <HStack gap={3} vAlign="center">
            <HealthDot health={camera.health} />
            <SourceBadge sourceType={camera.sourceType} />
          </HStack>
        }
        onOpenChange={(isOpen) => {
          if (!isOpen) onClose();
        }}
      />
      <VStack gap={4} padding={4}>
        {/* Video Preview */}
        <AspectRatio ratio={16 / 9}>
          <div
            style={{
              position: 'relative',
              width: '100%',
              height: '100%',
              backgroundColor: '#000',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 'var(--radius-container)',
              overflow: 'hidden',
              border: '1px solid var(--color-border)',
            }}
          >
            {camera.health === 'OFFLINE' ? (
              <VStack gap={2} hAlign="center" vAlign="center">
                <VideoOff size={36} />
                <Text type="code" size="xsm" color="secondary">
                  CAMERA MẤT KẾT NỐI
                </Text>
              </VStack>
            ) : camera.previewUrl ? (
              <LiveCameraVideo
                cameraId={camera.id}
                src={camera.previewUrl}
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            ) : (
              <VStack gap={2} hAlign="center" vAlign="center">
                <VideoOff size={36} />
                <Text type="code" size="xsm" color="secondary">
                  KHÔNG CÓ NGUỒN PHÁT
                </Text>
              </VStack>
            )}
          </div>
        </AspectRatio>

        {/* Events list */}
        <VStack gap={3}>
          <Text type="label" weight="bold" color="secondary" size="xsm">
            SỰ CỐ GẦN ĐÂY TRÊN CAMERA NÀY ({events.length})
          </Text>

          {events.length === 0 ? (
            <EmptyState
              title="Chưa ghi nhận sự cố nào"
              hint="Camera đang hoạt động bình thường trong khoảng thời gian đang xem."
            />
          ) : (
            <VStack gap={2}>
              {events.map((event) => (
                <Card
                  key={event.id}
                  elevation="low"
                  padding={3}
                  onClick={() => {
                    onClose();
                    navigate(`/incidents/${event.id}`);
                  }}
                  style={{
                    cursor: 'pointer',
                    borderRadius: 'var(--radius-container)',
                    border: '1px solid var(--color-border)',
                  }}
                >
                  <VStack gap={1}>
                    <HStack justify="between" vAlign="center" gap={2} style={{ flexWrap: 'nowrap' }}>
                      <HStack gap={1.5} vAlign="center">
                        <SeverityBadge severity={event.effectiveSeverity} />
                        <StateBadge state={event.state} />
                      </HStack>
                      <Text type="code" size="xsm" color="secondary" style={{ flexShrink: 0, whiteSpace: 'nowrap' }}>
                        {new Date(event.detectedAt).toLocaleString('vi-VN')}
                      </Text>
                    </HStack>
                    <Text type="body">
                      {event.description}
                    </Text>
                  </VStack>
                </Card>
              ))}
            </VStack>
          )}
        </VStack>
      </VStack>
    </Dialog>
  );
}
