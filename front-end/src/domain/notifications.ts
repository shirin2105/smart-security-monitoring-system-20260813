/**
 * Định nghĩa "thông báo quan trọng" cho Quản lý an ninh.
 *
 * Quản lý đi trực trên điện thoại nên không thể nhận mọi cảnh báo — nhận hết
 * thì sẽ bỏ sót đúng cái cần duyệt. Chỉ hai nhóm dưới đây được coi là quan
 * trọng, bám theo PRD §8.2 và §8.4:
 *
 *   1. Sự cố mức HIGH/CRITICAL chưa đóng — chỉ Quản lý mới xác nhận được.
 *   2. Escalation đang chờ duyệt — Bảo vệ đã xin ý kiến, không ai khác quyết thay.
 *
 * Nhóm 2 không phụ thuộc mức độ: Bảo vệ có quyền xin ý kiến trên cả sự cố nhẹ,
 * và một khi đã xin thì Quản lý bắt buộc phải trả lời.
 */

import { SecurityEvent, isSevere, isTerminal } from './types';

export function isManagerAlert(event: SecurityEvent): boolean {
  if (isTerminal(event.state)) return false;
  if (event.escalation === 'REQUESTED') return true;
  return isSevere(event.effectiveSeverity);
}

/** Việc còn phải xử lý — dùng cho badge đếm trên thanh điều hướng. */
export function needsManagerDecision(event: SecurityEvent): boolean {
  if (isTerminal(event.state)) return false;
  if (event.escalation === 'REQUESTED') return true;
  return isSevere(event.effectiveSeverity) && event.state === 'PENDING_REVIEW';
}

/**
 * Thứ tự trong hộp thư: việc cần quyết trước, rồi mới tới việc đang theo dõi;
 * trong cùng nhóm thì mới nhất lên đầu.
 */
export function selectManagerAlerts(events: SecurityEvent[]): SecurityEvent[] {
  return events
    .filter(isManagerAlert)
    .sort((a, b) => {
      const priority = Number(needsManagerDecision(b)) - Number(needsManagerDecision(a));
      if (priority !== 0) return priority;
      return new Date(b.detectedAt).getTime() - new Date(a.detectedAt).getTime();
    });
}

/** Câu mô tả ngắn hiển thị trên thông báo hệ thống. */
export function alertHeadline(event: SecurityEvent): string {
  if (event.escalation === 'REQUESTED') {
    return `Chờ bạn duyệt · ${event.cameraName}`;
  }
  return `${event.effectiveSeverity === 'CRITICAL' ? 'Khẩn cấp' : 'Nghiêm trọng'} · ${event.cameraName}`;
}
