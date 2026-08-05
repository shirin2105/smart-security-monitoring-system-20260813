import { describe, expect, it } from 'vitest';

import {
  alertHeadline,
  isManagerAlert,
  needsManagerDecision,
  selectManagerAlerts,
} from './notifications';
import { EscalationState, EventState, SecurityEvent, Severity } from './types';

function makeEvent(
  severity: Severity,
  state: EventState,
  escalation: EscalationState = 'NONE',
  overrides: Partial<SecurityEvent> = {},
): SecurityEvent {
  return {
    id: 1,
    cameraId: 1,
    cameraName: 'Camera Cổng Chính',
    eventType: 'ZONE_INTRUSION',
    effectiveSeverity: severity,
    state,
    escalation,
    description: 'test',
    aiGenerated: false,
    detectedAt: '2026-08-05T10:00:00Z',
    version: 1,
    actions: [],
    ...overrides,
  };
}

describe('isManagerAlert — lọc thông báo quan trọng', () => {
  it.each<Severity>(['HIGH', 'CRITICAL'])('sự cố %s chưa đóng là quan trọng', (severity) => {
    expect(isManagerAlert(makeEvent(severity, 'PENDING_REVIEW'))).toBe(true);
  });

  it.each<Severity>(['INFO', 'WARNING'])('sự cố %s bình thường thì không báo', (severity) => {
    expect(isManagerAlert(makeEvent(severity, 'OPEN'))).toBe(false);
  });

  it('sự cố nhẹ nhưng Bảo vệ đã xin ý kiến thì vẫn quan trọng', () => {
    expect(isManagerAlert(makeEvent('WARNING', 'ACKNOWLEDGED', 'REQUESTED'))).toBe(true);
  });

  it.each<EventState>(['RESOLVED', 'DISMISSED', 'EXPIRED'])(
    'sự cố đã đóng ở trạng thái %s thì thôi báo',
    (state) => {
      expect(isManagerAlert(makeEvent('CRITICAL', state))).toBe(false);
    },
  );

  it('escalation đã có quyết định thì không báo lại', () => {
    expect(isManagerAlert(makeEvent('WARNING', 'ACKNOWLEDGED', 'APPROVED'))).toBe(false);
    expect(isManagerAlert(makeEvent('WARNING', 'ACKNOWLEDGED', 'DECLINED'))).toBe(false);
  });
});

describe('needsManagerDecision — việc còn phải quyết', () => {
  it('sự cố nghiêm trọng đang chờ duyệt là việc phải quyết', () => {
    expect(needsManagerDecision(makeEvent('CRITICAL', 'PENDING_REVIEW'))).toBe(true);
  });

  it('sự cố đã xác nhận thì chỉ theo dõi, không còn phải quyết', () => {
    expect(needsManagerDecision(makeEvent('CRITICAL', 'CONFIRMED'))).toBe(false);
  });

  it('escalation đang chờ luôn là việc phải quyết', () => {
    expect(needsManagerDecision(makeEvent('INFO', 'ACKNOWLEDGED', 'REQUESTED'))).toBe(true);
  });
});

describe('selectManagerAlerts — thứ tự hộp thư', () => {
  it('việc phải quyết xếp trên việc chỉ theo dõi', () => {
    const confirmed = makeEvent('CRITICAL', 'CONFIRMED', 'NONE', {
      id: 1,
      detectedAt: '2026-08-05T12:00:00Z',
    });
    const pending = makeEvent('HIGH', 'PENDING_REVIEW', 'NONE', {
      id: 2,
      detectedAt: '2026-08-05T09:00:00Z',
    });

    // `confirmed` mới hơn nhưng `pending` mới là việc cần quyết.
    expect(selectManagerAlerts([confirmed, pending]).map((e) => e.id)).toEqual([2, 1]);
  });

  it('trong cùng nhóm thì mới nhất lên đầu', () => {
    const older = makeEvent('HIGH', 'PENDING_REVIEW', 'NONE', {
      id: 1,
      detectedAt: '2026-08-05T08:00:00Z',
    });
    const newer = makeEvent('HIGH', 'PENDING_REVIEW', 'NONE', {
      id: 2,
      detectedAt: '2026-08-05T11:00:00Z',
    });

    expect(selectManagerAlerts([older, newer]).map((e) => e.id)).toEqual([2, 1]);
  });

  it('loại hết sự cố không liên quan tới Quản lý', () => {
    const noise = makeEvent('WARNING', 'OPEN', 'NONE', { id: 9 });
    const closed = makeEvent('CRITICAL', 'RESOLVED', 'NONE', { id: 8 });
    const real = makeEvent('CRITICAL', 'PENDING_REVIEW', 'NONE', { id: 7 });

    expect(selectManagerAlerts([noise, closed, real]).map((e) => e.id)).toEqual([7]);
  });

  it('không làm thay đổi mảng gốc', () => {
    const list = [
      makeEvent('HIGH', 'PENDING_REVIEW', 'NONE', { id: 1 }),
      makeEvent('CRITICAL', 'PENDING_REVIEW', 'NONE', { id: 2 }),
    ];
    const before = list.map((e) => e.id);
    selectManagerAlerts(list);
    expect(list.map((e) => e.id)).toEqual(before);
  });
});

describe('alertHeadline', () => {
  it('ưu tiên nói rõ đang chờ duyệt', () => {
    expect(alertHeadline(makeEvent('HIGH', 'PENDING_REVIEW', 'REQUESTED'))).toBe(
      'Chờ bạn duyệt · Camera Cổng Chính',
    );
  });

  it('phân biệt khẩn cấp với nghiêm trọng', () => {
    expect(alertHeadline(makeEvent('CRITICAL', 'PENDING_REVIEW'))).toContain('Khẩn cấp');
    expect(alertHeadline(makeEvent('HIGH', 'PENDING_REVIEW'))).toContain('Nghiêm trọng');
  });
});
