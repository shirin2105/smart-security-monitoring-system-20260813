/**
 * Fixture deterministic bám API contract PRD §10.
 *
 * Cố ý phủ đủ các nhánh mà backend hiện chưa sinh ra được, để UI của BAC-53/54
 * kiểm chứng được ngay: cả 3 core event (gồm ABANDONED_OBJECT), đủ 4 mức
 * severity, event đã CONFIRMED, escalation đang REQUESTED, và trạng thái cuối.
 */

import { Camera, SecurityEvent, User } from '../../domain/types';

/** Mốc thời gian cố định theo phút trước hiện tại — demo luôn nhất quán. */
function minutesAgo(minutes: number): string {
  return new Date(Date.now() - minutes * 60_000).toISOString();
}

const PREVIEW = (id: number) =>
  `https://images.unsplash.com/photo-${
    [
      '1557597774-9d273605dfa9',
      '1541888946425-d0fbb186a5b7',
      '1508873696983-2df515122519',
      '1558494949-ef010cbdcc31',
      '1506521781263-d8422e82f27a',
      '1517502884422-41eaead166d4',
    ][id - 1]
  }?w=600&h=337&auto=format&fit=crop`;

export const MOCK_CAMERAS: Camera[] = [
  {
    id: 1,
    name: 'Camera Cổng Chính',
    location: 'Cổng A — Tầng 1',
    health: 'HEALTHY',
    sourceType: 'SIMULATED',
    previewUrl: '/videos/camera-1-aboda-source.h264.mp4#t=40',
  },
  {
    id: 2,
    name: 'Camera Sảnh Chờ',
    location: 'Sảnh Tòa Nhà — Tầng 1',
    health: 'HEALTHY',
    sourceType: 'SIMULATED',
    previewUrl: PREVIEW(2),
  },
  {
    id: 3,
    name: 'Camera Hàng Rào Tây',
    location: 'Khu Vực Hàng Rào — Phía Tây',
    health: 'DEGRADED',
    sourceType: 'SIMULATED',
    previewUrl: PREVIEW(3),
  },
  {
    id: 4,
    name: 'Camera Phòng Server',
    location: 'Khu Kỹ Thuật — Tầng Hầm',
    health: 'HEALTHY',
    sourceType: 'SIMULATED',
    previewUrl: PREVIEW(4),
  },
  {
    id: 5,
    name: 'Camera Bãi Xe B1',
    location: 'Bãi Xe Ô Tô — Tầng B1',
    health: 'OFFLINE',
    sourceType: 'SIMULATED',
    previewUrl: PREVIEW(5),
  },
  {
    id: 6,
    name: 'Camera Hành Lang T4',
    location: 'Hành Lang Văn Phòng — Tầng 4',
    health: 'HEALTHY',
    sourceType: 'SIMULATED',
    previewUrl: PREVIEW(6),
  },
];

export const MOCK_USERS: Record<string, { password: string; user: User }> = {
  guard: {
    password: 'guard123',
    user: {
      id: 1,
      username: 'guard',
      fullName: 'Bảo Vệ Nguyễn Văn A',
      role: 'GUARD',
      cameraScope: [],
    },
  },
  manager: {
    password: 'manager123',
    user: {
      id: 2,
      username: 'manager',
      fullName: 'Quản Lý Trần Văn B',
      role: 'MANAGER',
      cameraScope: [],
    },
  },
};

export const MOCK_EVENTS: SecurityEvent[] = [
  {
    id: 101,
    cameraId: 3,
    cameraName: 'Camera Hàng Rào Tây',
    eventType: 'ZONE_INTRUSION',
    effectiveSeverity: 'CRITICAL',
    recommendedSeverity: 'HIGH',
    state: 'PENDING_REVIEW',
    escalation: 'NONE',
    description:
      'Một người vượt hàng rào phía Tây và ở trong vùng cấm 12 giây, vượt ngưỡng dwell 8 giây.',
    aiGenerated: true,
    sourceType: 'SIMULATED',
    detectedAt: minutesAgo(3),
    version: 1,
    bbox: [120, 80, 240, 260],
    artifact: { url: PREVIEW(3), redactionStatus: 'COMPLETE' },
    actions: [],
  },
  {
    id: 102,
    cameraId: 6,
    cameraName: 'Camera Hành Lang T4',
    eventType: 'CROWD_THRESHOLD',
    effectiveSeverity: 'WARNING',
    state: 'OPEN',
    escalation: 'NONE',
    description: 'Đếm được 7 người trong ROI hành lang, vượt ngưỡng 5 người trong 30 giây.',
    aiGenerated: true,
    sourceType: 'SIMULATED',
    detectedAt: minutesAgo(9),
    version: 1,
    bbox: [200, 150, 450, 320],
    artifact: { url: PREVIEW(6), redactionStatus: 'COMPLETE' },
    actions: [],
  },
  {
    id: 103,
    cameraId: 2,
    cameraName: 'Camera Sảnh Chờ',
    eventType: 'ABANDONED_OBJECT',
    effectiveSeverity: 'HIGH',
    state: 'PENDING_REVIEW',
    escalation: 'REQUESTED',
    description:
      'Một vali đứng yên 4 phút 30 giây, không có người nào trong bán kính 3 mét.',
    aiGenerated: true,
    sourceType: 'SIMULATED',
    detectedAt: minutesAgo(15),
    version: 2,
    artifact: { url: PREVIEW(2), redactionStatus: 'COMPLETE' },
    actions: [
      {
        id: 9001,
        actorName: 'Bảo Vệ Nguyễn Văn A',
        action: 'REQUEST_ESCALATION',
        at: minutesAgo(12),
        incidentId: 103,
      },
    ],
  },
  {
    id: 104,
    cameraId: 1,
    cameraName: 'Camera Cổng Chính',
    eventType: 'ZONE_INTRUSION',
    effectiveSeverity: 'WARNING',
    state: 'ACKNOWLEDGED',
    escalation: 'NONE',
    description: 'Có người di chuyển qua cổng chính ngoài khung giờ quy định.',
    aiGenerated: true,
    sourceType: 'SIMULATED',
    detectedAt: minutesAgo(28),
    version: 2,
    artifact: { url: PREVIEW(1), redactionStatus: 'COMPLETE' },
    actions: [
      {
        id: 9002,
        actorName: 'Bảo Vệ Nguyễn Văn A',
        action: 'ACKNOWLEDGE',
        at: minutesAgo(26),
        incidentId: 104,
      },
    ],
  },
  {
    id: 105,
    cameraId: 4,
    cameraName: 'Camera Phòng Server',
    eventType: 'ZONE_INTRUSION',
    effectiveSeverity: 'CRITICAL',
    state: 'CONFIRMED',
    escalation: 'APPROVED',
    description: 'Phát hiện mở cửa phòng server tầng hầm ngoài lịch bảo trì.',
    aiGenerated: true,
    sourceType: 'SIMULATED',
    detectedAt: minutesAgo(45),
    version: 4,
    artifact: { url: PREVIEW(4), redactionStatus: 'COMPLETE' },
    actions: [
      {
        id: 9003,
        actorName: 'Bảo Vệ Nguyễn Văn A',
        action: 'REQUEST_ESCALATION',
        at: minutesAgo(43),
        incidentId: 105,
      },
      {
        id: 9004,
        actorName: 'Quản Lý Trần Văn B',
        action: 'CONFIRM',
        at: minutesAgo(41),
        incidentId: 105,
      },
      {
        id: 9005,
        actorName: 'Quản Lý Trần Văn B',
        action: 'APPROVE_ESCALATION',
        reason: 'Đã cử tổ tuần tra xuống kiểm tra trực tiếp tầng hầm.',
        at: minutesAgo(40),
        incidentId: 105,
      },
    ],
  },
  {
    id: 106,
    cameraId: 6,
    cameraName: 'Camera Hành Lang T4',
    eventType: 'CROWD_THRESHOLD',
    effectiveSeverity: 'INFO',
    state: 'RESOLVED',
    escalation: 'NONE',
    description: 'Nhóm nhân viên tụ tập ngắn giờ nghỉ trưa, đã tự giải tán.',
    aiGenerated: true,
    sourceType: 'SIMULATED',
    detectedAt: minutesAgo(120),
    version: 3,
    artifact: { url: PREVIEW(6), redactionStatus: 'COMPLETE' },
    actions: [
      {
        id: 9006,
        actorName: 'Bảo Vệ Nguyễn Văn A',
        action: 'ACKNOWLEDGE',
        at: minutesAgo(118),
        incidentId: 106,
      },
      {
        id: 9007,
        actorName: 'Bảo Vệ Nguyễn Văn A',
        action: 'RESOLVE',
        at: minutesAgo(115),
        incidentId: 106,
      },
    ],
  },
  {
    id: 107,
    cameraId: 5,
    cameraName: 'Camera Bãi Xe B1',
    eventType: 'ABANDONED_OBJECT',
    effectiveSeverity: 'WARNING',
    state: 'DISMISSED',
    escalation: 'NONE',
    description: 'Thùng carton để tạm cạnh cột B1, xác minh là hàng của bộ phận kho.',
    aiGenerated: true,
    sourceType: 'SIMULATED',
    detectedAt: minutesAgo(180),
    version: 2,
    // Redaction thất bại → PRD §13 bắt buộc drop artifact, chỉ giữ metadata.
    artifact: { url: '', redactionStatus: 'FAILED' },
    actions: [
      {
        id: 9008,
        actorName: 'Quản Lý Trần Văn B',
        action: 'DISMISS',
        reason: 'Đã xác minh với bộ phận kho, đây là hàng hóa để tạm có phép.',
        at: minutesAgo(170),
        incidentId: 107,
      },
    ],
  },
];

/** Kịch bản để nút "Giả lập cảnh báo" sinh event mới trong mock mode. */
export const SIMULATION_TEMPLATES: Array<
  Pick<
    SecurityEvent,
    'cameraId' | 'cameraName' | 'eventType' | 'effectiveSeverity' | 'description'
  > & { bbox: [number, number, number, number] }
> = [
  {
    cameraId: 3,
    cameraName: 'Camera Hàng Rào Tây',
    eventType: 'ZONE_INTRUSION',
    effectiveSeverity: 'CRITICAL',
    description: 'Phát hiện người vượt hàng rào phía Tây, dwell 10 giây trong vùng cấm.',
    bbox: [120, 80, 240, 260],
  },
  {
    cameraId: 6,
    cameraName: 'Camera Hành Lang T4',
    eventType: 'CROWD_THRESHOLD',
    effectiveSeverity: 'WARNING',
    description: 'Đếm được 6 người trong ROI hành lang tầng 4, giữ trong 25 giây.',
    bbox: [200, 150, 450, 320],
  },
  {
    cameraId: 2,
    cameraName: 'Camera Sảnh Chờ',
    eventType: 'ABANDONED_OBJECT',
    effectiveSeverity: 'HIGH',
    description: 'Balo đứng yên 5 phút tại sảnh chờ, không có người trong bán kính 3 mét.',
    bbox: [180, 200, 300, 340],
  },
];
