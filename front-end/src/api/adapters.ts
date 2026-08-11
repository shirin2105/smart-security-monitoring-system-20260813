/**
 * Quy đổi giữa payload backend hiện tại và domain model theo PRD.
 *
 * Backend nhánh `2A202601409_NgoTuanHung` còn dùng schema cũ:
 *   event_type : xam_nhap | dam_dong          → PRD: ZONE_INTRUSION | CROWD_THRESHOLD
 *   severity   : warning | critical           → PRD: INFO | WARNING | HIGH | CRITICAL
 *   status     : pending | acknowledged | escalated
 *                                             → PRD: state + escalation tách riêng
 *   role       : bao_ve | quan_ly             → PRD: GUARD | MANAGER
 *
 * Hàm ở đây cũng chấp nhận sẵn giá trị theo PRD, nên khi backend nâng cấp theo
 * BAC-21 thì UI chạy tiếp mà không cần sửa.
 */

import { API_BASE_URL } from './config';
import {
  Camera,
  CameraHealth,
  EscalationState,
  EventAction,
  EventState,
  EventType,
  Role,
  SecurityEvent,
  Severity,
  User,
  isSevere,
} from '../domain/types';

/* ------------------------------- payload backend ------------------------------ */

export interface RawCamera {
  id: number;
  name: string;
  location: string;
  stream_url: string;
  status: string;
  source?: string;
}

export interface RawIncident {
  id: number;
  camera_id: number;
  camera_name?: string;
  event_type: string;
  severity: string;
  description: string;
  status: string;
  source?: string;
  created_at: string;
  bbox?: [number, number, number, number];
  version?: number;
  ai_generated?: boolean;
  recommended_severity?: string;
  artifact_url?: string;
  redaction_status?: string;
}

export interface RawAuditLog {
  id: number;
  user_name: string;
  action: string;
  incident_id?: number | null;
  reason?: string | null;
  timestamp: string;
}

export interface RawUser {
  id: number;
  username: string;
  full_name: string;
  role: string;
  camera_scope?: number[];
}

/* --------------------------------- quy đổi ----------------------------------- */

const EVENT_TYPE_MAP: Record<string, EventType> = {
  xam_nhap: 'ZONE_INTRUSION',
  dam_dong: 'CROWD_THRESHOLD',
  vat_the_bo_quen: 'ABANDONED_OBJECT',
  te_nga: 'SUSPECTED_FALL',
  ZONE_INTRUSION: 'ZONE_INTRUSION',
  CROWD_THRESHOLD: 'CROWD_THRESHOLD',
  ABANDONED_OBJECT: 'ABANDONED_OBJECT',
  SUSPECTED_FALL: 'SUSPECTED_FALL',
  COVERAGE_DEGRADED: 'COVERAGE_DEGRADED',
};

const SEVERITY_MAP: Record<string, Severity> = {
  info: 'INFO',
  warning: 'WARNING',
  high: 'HIGH',
  critical: 'CRITICAL',
};

const HEALTH_MAP: Record<string, CameraHealth> = {
  online: 'HEALTHY',
  healthy: 'HEALTHY',
  warning: 'DEGRADED',
  degraded: 'DEGRADED',
  offline: 'OFFLINE',
};

const ROLE_MAP: Record<string, Role> = {
  bao_ve: 'GUARD',
  guard: 'GUARD',
  GUARD: 'GUARD',
  quan_ly: 'MANAGER',
  manager: 'MANAGER',
  MANAGER: 'MANAGER',
};

/**
 * Chuẩn hóa timestamp về ISO có múi giờ.
 *
 * Backend lưu `datetime.now(timezone.utc)` vào cột `DateTime` không kèm
 * timezone, nên serialize ra chuỗi trần: "2026-08-04T16:38:58.580962".
 * `new Date()` của trình duyệt coi chuỗi không có offset là GIỜ ĐỊA PHƯƠNG,
 * khiến mọi mốc thời gian lệch đúng bằng offset của máy (UTC+7 → sai 7 tiếng).
 *
 * Giá trị đã có `Z` hoặc `+07:00` thì giữ nguyên, để khi backend sửa sang
 * `DateTime(timezone=True)` hàm này vẫn đúng.
 */
export function normalizeTimestamp(raw: string): string {
  if (!raw) return raw;
  if (/([Zz]|[+-]\d{2}:?\d{2})$/.test(raw)) return raw;
  return `${raw}Z`;
}

export function toEventType(raw: string): EventType {
  return EVENT_TYPE_MAP[raw] ?? 'COVERAGE_DEGRADED';
}

export function toSeverity(raw: string): Severity {
  return SEVERITY_MAP[String(raw).toLowerCase()] ?? 'WARNING';
}

export function toRole(raw: string): Role {
  return ROLE_MAP[raw] ?? 'GUARD';
}

/**
 * Backend gộp escalation vào `status`, PRD tách làm hai trục.
 * `escalated` được hiểu là "Guard đã xin ý kiến, chờ Quản lý duyệt".
 */
function toStateAndEscalation(
  rawStatus: string,
  severe: boolean,
): { state: EventState; escalation: EscalationState } {
  switch (rawStatus) {
    case 'acknowledged':
      return { state: severe ? 'CONFIRMED' : 'ACKNOWLEDGED', escalation: 'NONE' };
    case 'escalated':
      return {
        state: severe ? 'PENDING_REVIEW' : 'ACKNOWLEDGED',
        escalation: 'REQUESTED',
      };
    case 'resolved':
      return { state: 'RESOLVED', escalation: 'NONE' };
    case 'dismissed':
      return { state: 'DISMISSED', escalation: 'NONE' };
    case 'pending':
    default:
      return { state: severe ? 'PENDING_REVIEW' : 'OPEN', escalation: 'NONE' };
  }
}

export function toCamera(raw: RawCamera): Camera {
  return {
    id: raw.id,
    name: raw.name,
    location: raw.location,
    health: HEALTH_MAP[String(raw.status).toLowerCase()] ?? 'OFFLINE',
    // Nguồn theo backend: camera chạy CV pipeline thật là LIVE (PRD §8.1).
    sourceType: raw.source === 'CV' ? 'LIVE' : 'SIMULATED',
    // stream_url có thể là path relative (/media/...) — resolve sang backend origin
    previewUrl: raw.stream_url.startsWith('http')
      ? raw.stream_url
      : `${API_BASE_URL}${raw.stream_url}`,
  };
}

export function toEvent(raw: RawIncident, actions: EventAction[] = []): SecurityEvent {
  const effectiveSeverity = toSeverity(raw.severity);
  const { state, escalation } = toStateAndEscalation(
    raw.status,
    isSevere(effectiveSeverity),
  );

  return {
    id: raw.id,
    cameraId: raw.camera_id,
    cameraName: raw.camera_name ?? `Camera #${raw.camera_id}`,
    eventType: toEventType(raw.event_type),
    effectiveSeverity,
    recommendedSeverity: raw.recommended_severity
      ? toSeverity(raw.recommended_severity)
      : undefined,
    state,
    escalation,
    description: raw.description,
    aiGenerated: raw.ai_generated ?? false,
    sourceType: raw.source === 'CV' ? 'LIVE' : 'SIMULATED',
    detectedAt: normalizeTimestamp(raw.created_at),
    version: raw.version ?? 1,
    artifact: raw.artifact_url
      ? {
          url: raw.artifact_url,
          redactionStatus:
            raw.redaction_status === 'COMPLETE' ? 'COMPLETE' : 'PENDING',
        }
      : undefined,
    bbox: raw.bbox,
    actions,
  };
}

export function toAuditAction(raw: RawAuditLog): EventAction {
  return {
    id: raw.id,
    actorName: raw.user_name,
    action: raw.action,
    reason: raw.reason ?? undefined,
    incidentId: raw.incident_id ?? undefined,
    at: normalizeTimestamp(raw.timestamp),
  };
}

export function toUser(raw: RawUser): User {
  return {
    id: raw.id,
    username: raw.username,
    fullName: raw.full_name,
    role: toRole(raw.role),
    cameraScope: raw.camera_scope ?? [],
  };
}
