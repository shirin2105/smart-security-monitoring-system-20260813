/**
 * Allow/deny matrix test — điều kiện PASS của Gate 2 yêu cầu
 * "full state/role/scope action matrix" được unit test.
 *
 * Test này kiểm chứng lớp trình bày. Backend vẫn phải có bộ test tương đương
 * ở phía server, vì UI ẩn nút không phải là biện pháp bảo mật.
 */

import { describe, expect, it } from 'vitest';

import { allowedActions, reasonRequired } from './permissions';
import { ActionType, EventState, EscalationState, SecurityEvent, Severity } from './types';

function makeEvent(
  severity: Severity,
  state: EventState,
  escalation: EscalationState = 'NONE',
  cameraId = 1,
): SecurityEvent {
  return {
    id: 1,
    cameraId,
    cameraName: 'Camera Test',
    eventType: 'ZONE_INTRUSION',
    effectiveSeverity: severity,
    state,
    escalation,
    description: 'test',
    aiGenerated: false,
    sourceType: 'SIMULATED',
    detectedAt: new Date().toISOString(),
    version: 1,
    actions: [],
  };
}

const typesOf = (event: SecurityEvent, role: 'GUARD' | 'MANAGER', scope: number[] = []) =>
  allowedActions(event, role, scope)
    .map((spec) => spec.type)
    .sort();

const sorted = (...types: ActionType[]) => [...types].sort();

describe('Guard — INFO/WARNING', () => {
  it('được tiếp nhận, bỏ qua và xin ý kiến khi event đang OPEN', () => {
    expect(typesOf(makeEvent('WARNING', 'OPEN'), 'GUARD')).toEqual(
      sorted('ACKNOWLEDGE', 'DISMISS', 'REQUEST_ESCALATION'),
    );
  });

  it('được kết thúc hoặc bỏ qua sau khi đã tiếp nhận', () => {
    expect(typesOf(makeEvent('INFO', 'ACKNOWLEDGED'), 'GUARD')).toEqual(
      sorted('RESOLVE', 'DISMISS', 'REQUEST_ESCALATION'),
    );
  });
});

describe('Guard — HIGH/CRITICAL: không được tự quyết', () => {
  it.each<Severity>(['HIGH', 'CRITICAL'])(
    'chỉ được xin ý kiến, không confirm/dismiss với mức %s',
    (severity) => {
      expect(typesOf(makeEvent(severity, 'PENDING_REVIEW'), 'GUARD')).toEqual([
        'REQUEST_ESCALATION',
      ]);
    },
  );

  it('không được resolve event severe đã confirm', () => {
    expect(typesOf(makeEvent('CRITICAL', 'CONFIRMED'), 'GUARD')).toEqual([
      'REQUEST_ESCALATION',
    ]);
  });

  it('không bao giờ được duyệt escalation do chính mình tạo', () => {
    const event = makeEvent('HIGH', 'PENDING_REVIEW', 'REQUESTED');
    expect(typesOf(event, 'GUARD')).toEqual([]);
  });
});

describe('Manager — quyền đầy đủ', () => {
  it('được confirm hoặc dismiss event severe đang chờ duyệt', () => {
    expect(typesOf(makeEvent('CRITICAL', 'PENDING_REVIEW'), 'MANAGER')).toEqual(
      sorted('CONFIRM', 'DISMISS', 'REQUEST_ESCALATION'),
    );
  });

  it('được resolve event severe sau khi đã confirm', () => {
    expect(typesOf(makeEvent('HIGH', 'CONFIRMED'), 'MANAGER')).toContain('RESOLVE');
  });

  it('được phê duyệt hoặc từ chối escalation đang chờ', () => {
    const types = typesOf(makeEvent('HIGH', 'PENDING_REVIEW', 'REQUESTED'), 'MANAGER');
    expect(types).toEqual(sorted('CONFIRM', 'DISMISS', 'APPROVE_ESCALATION', 'DECLINE_ESCALATION'));
  });

  it('vẫn làm được các thao tác cơ bản của Guard', () => {
    expect(typesOf(makeEvent('WARNING', 'OPEN'), 'MANAGER')).toEqual(
      sorted('ACKNOWLEDGE', 'DISMISS', 'REQUEST_ESCALATION'),
    );
  });
});

describe('Trạng thái cuối — không còn hành động nào', () => {
  it.each<EventState>(['RESOLVED', 'DISMISSED', 'EXPIRED'])('state %s', (state) => {
    expect(typesOf(makeEvent('CRITICAL', state), 'MANAGER')).toEqual([]);
    expect(typesOf(makeEvent('WARNING', state), 'GUARD')).toEqual([]);
  });
});

describe('Escalation không lặp lại', () => {
  it('đã APPROVED thì không xin duyệt lại được', () => {
    const types = typesOf(makeEvent('HIGH', 'CONFIRMED', 'APPROVED'), 'MANAGER');
    expect(types).not.toContain('REQUEST_ESCALATION');
    expect(types).not.toContain('APPROVE_ESCALATION');
  });

  it('đã DECLINED thì không duyệt lại được', () => {
    const types = typesOf(makeEvent('HIGH', 'PENDING_REVIEW', 'DECLINED'), 'MANAGER');
    expect(types).not.toContain('APPROVE_ESCALATION');
    expect(types).not.toContain('DECLINE_ESCALATION');
  });
});

describe('Camera scope', () => {
  it('event ngoài scope không có hành động nào, kể cả với Manager', () => {
    const event = makeEvent('WARNING', 'OPEN', 'NONE', 99);
    expect(typesOf(event, 'MANAGER', [1, 2, 3])).toEqual([]);
    expect(typesOf(event, 'GUARD', [1, 2, 3])).toEqual([]);
  });

  it('event trong scope hoạt động bình thường', () => {
    const event = makeEvent('WARNING', 'OPEN', 'NONE', 2);
    expect(typesOf(event, 'GUARD', [1, 2, 3])).toContain('ACKNOWLEDGE');
  });

  it('scope rỗng nghĩa là backend chưa cấp — không chặn ở UI', () => {
    const event = makeEvent('WARNING', 'OPEN', 'NONE', 42);
    expect(typesOf(event, 'GUARD', [])).toContain('ACKNOWLEDGE');
  });
});

describe('Yêu cầu nhập lý do', () => {
  it('luôn bắt buộc khi bỏ qua sự cố', () => {
    expect(reasonRequired('DISMISS', 'INFO')).toBe(true);
  });

  it('bắt buộc khi kết thúc sự cố mức nghiêm trọng', () => {
    expect(reasonRequired('RESOLVE', 'HIGH')).toBe(true);
    expect(reasonRequired('RESOLVE', 'CRITICAL')).toBe(true);
  });

  it('không bắt buộc khi kết thúc sự cố mức thấp', () => {
    expect(reasonRequired('RESOLVE', 'INFO')).toBe(false);
    expect(reasonRequired('RESOLVE', 'WARNING')).toBe(false);
  });

  it('bắt buộc cho mọi quyết định escalation', () => {
    expect(reasonRequired('APPROVE_ESCALATION', 'HIGH')).toBe(true);
    expect(reasonRequired('DECLINE_ESCALATION', 'HIGH')).toBe(true);
  });

  it('không bắt buộc khi chỉ tiếp nhận', () => {
    expect(reasonRequired('ACKNOWLEDGE', 'WARNING')).toBe(false);
  });
});
