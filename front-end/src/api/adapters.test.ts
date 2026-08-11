/**
 * Test adapter dùng payload THẬT bắt được từ backend đang chạy trong
 * docker compose (ngày 04/08/2026), không phải dữ liệu tự bịa.
 *
 * Mục đích: khóa lại hành vi quy đổi, để khi backend đổi schema theo BAC-21
 * thì test đỏ ngay thay vì lỗi âm thầm trên UI.
 */

import { describe, expect, it } from 'vitest';

import { RawCamera, RawIncident, normalizeTimestamp, toCamera, toEvent, toUser } from './adapters';

/** Nguyên văn từ GET /api/v1/alerts */
const REAL_CRITICAL: RawIncident = {
  id: 1,
  camera_id: 3,
  camera_name: 'Camera Hàng Rào Tây',
  event_type: 'xam_nhap',
  severity: 'critical',
  description: 'Phát hiện đối tượng xâm nhập hàng rào khu vực Phía Tây',
  status: 'pending',
  created_at: '2026-08-04T16:37:49.598042',
};

/** Nguyên văn từ message WebSocket NEW_ALERT */
const REAL_WS_INCIDENT: RawIncident = {
  id: 4,
  camera_id: 3,
  camera_name: 'Camera Hàng Rào Tây',
  event_type: 'xam_nhap',
  severity: 'critical',
  description: 'CẢNH BÁO CRITICAL: Phát hiện vượt hàng rào phía Tây!',
  status: 'pending',
  created_at: '2026-08-04T16:38:58.580962',
  bbox: [120, 80, 240, 260],
};

const REAL_CAMERA: RawCamera = {
  id: 3,
  name: 'Camera Hàng Rào Tây',
  location: 'Khu Vực Hàng Rào - Phía Tây',
  stream_url: 'https://images.unsplash.com/photo-1508873696983-2df515122519?w=600',
  status: 'warning',
};

describe('normalizeTimestamp — chống lệch múi giờ', () => {
  it('gắn Z vào chuỗi trần vì backend trả UTC nhưng không kèm offset', () => {
    expect(normalizeTimestamp('2026-08-04T16:38:58.580962')).toBe(
      '2026-08-04T16:38:58.580962Z',
    );
  });

  it('chuỗi trần được hiểu đúng là UTC, không phải giờ máy', () => {
    const parsed = new Date(normalizeTimestamp('2026-08-04T16:38:58.580962'));
    expect(parsed.toISOString()).toBe('2026-08-04T16:38:58.580Z');
  });

  it('giữ nguyên khi đã có Z', () => {
    expect(normalizeTimestamp('2026-08-04T16:38:58Z')).toBe('2026-08-04T16:38:58Z');
  });

  it('giữ nguyên khi đã có offset — để backend nâng cấp không làm hỏng', () => {
    expect(normalizeTimestamp('2026-08-04T23:38:58+07:00')).toBe(
      '2026-08-04T23:38:58+07:00',
    );
  });
});

describe('toEvent — payload REST thật', () => {
  const event = toEvent(REAL_CRITICAL);

  it('quy đổi xam_nhap → ZONE_INTRUSION', () => {
    expect(event.eventType).toBe('ZONE_INTRUSION');
  });

  it('quy đổi critical → CRITICAL', () => {
    expect(event.effectiveSeverity).toBe('CRITICAL');
  });

  it('pending + severe → PENDING_REVIEW, không phải OPEN', () => {
    expect(event.state).toBe('PENDING_REVIEW');
    expect(event.escalation).toBe('NONE');
  });

  it('timestamp được chuẩn hóa về UTC', () => {
    expect(event.detectedAt).toBe('2026-08-04T16:37:49.598042Z');
  });

  it('không có version từ backend thì mặc định 1', () => {
    expect(event.version).toBe(1);
  });
});

describe('toEvent — payload WebSocket thật', () => {
  it('đọc được nguyên message NEW_ALERT, giữ bbox', () => {
    const event = toEvent(REAL_WS_INCIDENT);
    expect(event.id).toBe(4);
    expect(event.eventType).toBe('ZONE_INTRUSION');
    expect(event.effectiveSeverity).toBe('CRITICAL');
    expect(event.bbox).toEqual([120, 80, 240, 260]);
  });
});

describe('toEvent — quy đổi trạng thái', () => {
  it('dam_dong + warning + pending → CROWD_THRESHOLD / WARNING / OPEN', () => {
    const event = toEvent({ ...REAL_CRITICAL, event_type: 'dam_dong', severity: 'warning' });
    expect(event.eventType).toBe('CROWD_THRESHOLD');
    expect(event.effectiveSeverity).toBe('WARNING');
    expect(event.state).toBe('OPEN');
  });

  it('acknowledged trên event thường → ACKNOWLEDGED', () => {
    const event = toEvent({ ...REAL_CRITICAL, severity: 'warning', status: 'acknowledged' });
    expect(event.state).toBe('ACKNOWLEDGED');
  });

  it('acknowledged trên event severe → CONFIRMED', () => {
    const event = toEvent({ ...REAL_CRITICAL, status: 'acknowledged' });
    expect(event.state).toBe('CONFIRMED');
  });

  it('escalated được tách thành escalation REQUESTED', () => {
    const event = toEvent({ ...REAL_CRITICAL, status: 'escalated' });
    expect(event.escalation).toBe('REQUESTED');
    expect(event.state).toBe('PENDING_REVIEW');
  });

  it('chấp nhận sẵn giá trị theo PRD để backend nâng cấp không phá UI', () => {
    const event = toEvent({
      ...REAL_CRITICAL,
      event_type: 'ABANDONED_OBJECT',
      severity: 'high',
    });
    expect(event.eventType).toBe('ABANDONED_OBJECT');
    expect(event.effectiveSeverity).toBe('HIGH');
  });
});

describe('toCamera', () => {
  it('status warning → DEGRADED và luôn gắn nhãn nguồn giả lập', () => {
    const camera = toCamera(REAL_CAMERA);
    expect(camera.health).toBe('DEGRADED');
    expect(camera.sourceType).toBe('SIMULATED');
  });

  it('online → HEALTHY, offline → OFFLINE', () => {
    expect(toCamera({ ...REAL_CAMERA, status: 'online' }).health).toBe('HEALTHY');
    expect(toCamera({ ...REAL_CAMERA, status: 'offline' }).health).toBe('OFFLINE');
  });
});

describe('toUser — payload login thật', () => {
  it('bao_ve → GUARD', () => {
    const user = toUser({
      id: 1,
      username: 'guard',
      full_name: 'Bảo Vệ Nguyễn Văn A',
      role: 'bao_ve',
    });
    expect(user.role).toBe('GUARD');
    expect(user.cameraScope).toEqual([]);
  });

  it('quan_ly → MANAGER', () => {
    const user = toUser({
      id: 2,
      username: 'manager',
      full_name: 'Quản Lý Trần Văn B',
      role: 'quan_ly',
    });
    expect(user.role).toBe('MANAGER');
  });
});
