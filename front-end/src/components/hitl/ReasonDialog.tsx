import { FormEvent, useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';

/** Đủ dài để có giá trị khi audit, đủ ngắn để không cản người trực. */
const MIN_REASON_LENGTH = 10;

interface ReasonDialogProps {
  title: string;
  description: string;
  confirmLabel: string;
  submitting: boolean;
  onCancel: () => void;
  onSubmit: (reason: string) => void;
}

/**
 * Hộp thoại nhập lý do — PRD §8.4 bắt buộc reason cho severe dismiss/resolve và
 * cho mọi quyết định approve/decline escalation.
 */
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
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !submitting) onCancel();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onCancel, submitting]);

  const trimmed = reason.trim();
  const tooShort = trimmed.length < MIN_REASON_LENGTH;

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setTouched(true);
    if (tooShort || submitting) return;
    onSubmit(trimmed);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reason-dialog-title"
    >
      <form
        onSubmit={handleSubmit}
        className="glass-panel w-full max-w-lg overflow-hidden rounded-2xl border border-gray-800 bg-gray-900"
      >
        <div className="flex items-start justify-between border-b border-gray-800 bg-gray-950 px-5 py-4">
          <div>
            <h3 id="reason-dialog-title" className="text-sm font-bold text-white">
              {title}
            </h3>
            <p className="mt-1 text-xs leading-relaxed text-gray-400">{description}</p>
          </div>
          <button
            type="button"
            onClick={onCancel}
            disabled={submitting}
            className="rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-800 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            aria-label="Đóng"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>

        <div className="space-y-2 p-5">
          <label
            htmlFor="hitl-reason"
            className="block font-mono text-xs font-medium uppercase text-gray-300"
          >
            Lý do <span className="text-red-400">*</span>
          </label>
          <textarea
            id="hitl-reason"
            ref={textareaRef}
            rows={4}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            onBlur={() => setTouched(true)}
            aria-invalid={touched && tooShort}
            aria-describedby="hitl-reason-help"
            className="w-full resize-none rounded-lg border border-gray-800 bg-gray-950 px-3 py-2.5 text-sm text-white placeholder-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Ghi rõ căn cứ để người sau đọc lại hiểu được quyết định này…"
          />
          <p id="hitl-reason-help" className="text-[11px] text-gray-500">
            Lý do được ghi vào audit trail và không thể sửa hay xóa về sau.
          </p>
          {touched && tooShort && (
            <p role="alert" className="text-[11px] text-red-400">
              Vui lòng nhập tối thiểu {MIN_REASON_LENGTH} ký tự.
            </p>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-gray-800 bg-gray-950 px-5 py-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={submitting}
            className="rounded-lg border border-gray-700 bg-gray-800 px-4 py-2 text-xs font-medium text-gray-200 transition-colors hover:bg-gray-700 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-500"
          >
            Hủy
          </button>
          <button
            type="submit"
            disabled={submitting || tooShort}
            className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
          >
            {submitting ? 'Đang gửi…' : confirmLabel}
          </button>
        </div>
      </form>
    </div>
  );
}
