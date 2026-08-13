/**
 * Domain model của frontend — bám theo API contract trong PRD §8 và §10.
 *
 * Backend hiện tại (nhánh của Hưng) còn dùng schema cũ (`xam_nhap`, `warning`,
 * `pending`...). Việc quy đổi nằm trọn trong `src/api/adapters.ts`, nên khi
 * BAC-21 khóa contract chỉ cần sửa file adapter, không đụng vào UI.
 */

export type Role = 'GUARD' | 'MANAGER';

export type EventType =
  | 'ZONE_INTRUSION'
  | 'CROWD_THRESHOLD'
  | 'ABANDONED_OBJECT'
  | 'SUSPECTED_FALL'
  | 'COVERAGE_DEGRADED';

export type Severity = 'INFO' | 'WARNING' | 'HIGH' | 'CRITICAL';

/** PRD §8.3 — INFO/WARNING đi nhánh OPEN, HIGH/CRITICAL đi nhánh PENDING_REVIEW. */
export type EventState =
  | 'OPEN'
  | 'ACKNOWLEDGED'
  | 'PENDING_REVIEW'
  | 'CONFIRMED'
  | 'RESOLVED'
  | 'DISMISSED'
  | 'EXPIRED';

/** PRD §8.4 — escalation chỉ tồn tại trong ứng dụng, không gọi ra ngoài. */
export type EscalationState = 'NONE' | 'REQUESTED' | 'APPROVED' | 'DECLINED';

export type CameraHealth = 'HEALTHY' | 'DEGRADED' | 'OFFLINE';

export type SourceType = 'SIMULATED' | 'LIVE';

export type RedactionStatus = 'COMPLETE' | 'PENDING' | 'FAILED';

export type ActionType =
  | 'ACKNOWLEDGE'
  | 'RESOLVE'
  | 'DISMISS'
  | 'CONFIRM'
  | 'REQUEST_ESCALATION'
  | 'APPROVE_ESCALATION'
  | 'DECLINE_ESCALATION';

export interface User {
  id: number;
  username: string;
  fullName: string;
  role: Role;
  /** Scope site/camera do server cấp. Rỗng = chưa được backend trả về. */
  cameraScope: number[];
}

export interface Camera {
  id: number;
  name: string;
  location: string;
  health: CameraHealth;
  sourceType: SourceType;
  previewUrl: string;
}

export interface EventArtifact {
  url: string;
  redactionStatus: RedactionStatus;
}

export interface EventAction {
  id: number;
  actorName: string;
  action: string;
  reason?: string;
  incidentId?: number;
  at: string;
}

export interface SecurityEvent {
  id: number;
  cameraId: number;
  cameraName: string;
  eventType: EventType;
  /** Do policy engine quyết định. Agent chỉ được đề xuất (PRD §8.2). */
  effectiveSeverity: Severity;
  /** Đề xuất của Agent — chỉ để tham khảo, có thể chưa có. */
  recommendedSeverity?: Severity;
  state: EventState;
  escalation: EscalationState;
  description: string;
  /** Nguồn phát hiện: CV pipeline thật hay simulator (PRD §8.1). */
  sourceType: SourceType;
  /** Mô tả do LLM sinh — UI phải gắn nhãn AI-generated (FR-AI-03). */
  aiGenerated: boolean;
  detectedAt: string;
  /** Optimistic concurrency: gửi kèm khi POST action, server stale → 409. */
  version: number;
  artifact?: EventArtifact;
  bbox?: [number, number, number, number];
  actions: EventAction[];
}

export interface TelemetryTrack {
  trackId: number;
  className: string;
  confidence: number;
  bbox: [number, number, number, number];
}

export interface CameraTelemetry {
  cameraId: string;
  numericCameraId: number;
  timestamp: string;
  frameSize?: [number, number];
  videoTime?: number;
  tracks: TelemetryTrack[];
}

/** HIGH/CRITICAL là "severe" — đi nhánh review bắt buộc của Manager. */
export const SEVERE_SEVERITIES: Severity[] = ['HIGH', 'CRITICAL'];

export function isSevere(severity: Severity): boolean {
  return SEVERE_SEVERITIES.includes(severity);
}

/** Trạng thái đã đóng — không còn hành động nào và không cần thông báo nữa. */
export const TERMINAL_STATES: EventState[] = ['RESOLVED', 'DISMISSED', 'EXPIRED'];

export function isTerminal(state: EventState): boolean {
  return TERMINAL_STATES.includes(state);
}

export const EVENT_TYPE_LABEL: Record<EventType, string> = {
  ZONE_INTRUSION: 'Xâm nhập vùng cấm',
  CROWD_THRESHOLD: 'Tụ tập đông người',
  ABANDONED_OBJECT: 'Vật thể bỏ quên',
  SUSPECTED_FALL: 'Nghi ngờ té ngã',
  COVERAGE_DEGRADED: 'Suy giảm giám sát',
};

export const SEVERITY_LABEL: Record<Severity, string> = {
  INFO: 'Thông tin',
  WARNING: 'Cảnh báo',
  HIGH: 'Nghiêm trọng',
  CRITICAL: 'Khẩn cấp',
};

export const STATE_LABEL: Record<EventState, string> = {
  OPEN: 'Chờ tiếp nhận',
  ACKNOWLEDGED: 'Đã tiếp nhận',
  PENDING_REVIEW: 'Chờ Quản lý duyệt',
  CONFIRMED: 'Đã xác nhận',
  RESOLVED: 'Đã xử lý xong',
  DISMISSED: 'Đã bỏ qua',
  EXPIRED: 'Quá hạn duyệt',
};

export const ESCALATION_LABEL: Record<EscalationState, string> = {
  NONE: 'Không',
  REQUESTED: 'Đã yêu cầu duyệt',
  APPROVED: 'Đã phê duyệt',
  DECLINED: 'Đã từ chối',
};

export const CAMERA_HEALTH_LABEL: Record<CameraHealth, string> = {
  HEALTHY: 'Hoạt động',
  DEGRADED: 'Chập chờn',
  OFFLINE: 'Mất kết nối',
};

export const ROLE_LABEL: Record<Role, string> = {
  GUARD: 'Bảo vệ trực',
  MANAGER: 'Quản lý an ninh',
};

export interface CameraZone {
  zoneId: string;
  cameraId: string;
  name: string;
  polygon: [number, number][];
  enabled: boolean;
}

