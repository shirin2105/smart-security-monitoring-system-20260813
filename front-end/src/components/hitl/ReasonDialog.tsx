import { FormEvent, useState } from 'react';
import { Dialog, DialogHeader } from '@astryxdesign/core/Dialog';
import { HStack, VStack } from '@astryxdesign/core/Stack';
import { Button } from '@astryxdesign/core/Button';
import { TextArea } from '@astryxdesign/core/TextArea';

const MIN_REASON_LENGTH = 10;

interface ReasonDialogProps {
  title: string;
  description: string;
  confirmLabel: string;
  submitting: boolean;
  onCancel: () => void;
  onSubmit: (reason: string) => void;
}

export function ReasonDialog({
  title,
  description,
  confirmLabel,
  submitting,
  onCancel,
  onSubmit,
}: ReasonDialogProps) {
  const [reason, setReason] = useState('');
  const [touched, setTouched] = useState(false);

  const trimmed = reason.trim();
  const tooShort = trimmed.length < MIN_REASON_LENGTH;

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setTouched(true);
    if (tooShort || submitting) return;
    onSubmit(trimmed);
  };

  return (
    <Dialog
      isOpen={true}
      onOpenChange={(isOpen) => {
        if (!isOpen && !submitting) onCancel();
      }}
      width={520}
      purpose="form"
    >
      <DialogHeader
        title={title}
        subtitle={description}
        onOpenChange={(isOpen) => {
          if (!isOpen && !submitting) onCancel();
        }}
      />
      <form onSubmit={handleSubmit}>
        <VStack gap={4} padding={4}>
          <TextArea
            label="Lý do"
            isRequired
            rows={4}
            value={reason}
            onChange={(val) => setReason(val)}
            placeholder="Ghi rõ căn cứ để người sau đọc lại hiểu được quyết định này…"
            description="Lý do được ghi vào audit trail và không thể sửa hay xóa về sau."
            status={
              touched && tooShort
                ? {
                    type: 'error',
                    message: `Vui lòng nhập tối thiểu ${MIN_REASON_LENGTH} ký tự (hiện có ${trimmed.length}).`,
                  }
                : undefined
            }
          />
          <HStack justify="end" gap={2}>
            <Button
              label="Hủy"
              variant="secondary"
              size="sm"
              onClick={onCancel}
              isDisabled={submitting}
            />
            <Button
              label={confirmLabel}
              type="submit"
              variant="primary"
              size="sm"
              isLoading={submitting}
              isDisabled={submitting || tooShort}
            />
          </HStack>
        </VStack>
      </form>
    </Dialog>
  );
}

