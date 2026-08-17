import {
  ActionType,
  Camera,
  EventAction,
  EventState,
  EventType,
  SecurityEvent,
  Severity,
  User,
} from '../domain/types';

export interface IncidentQuery {
  /** ISO date-time, lọc theo `detectedAt`. */
  from?: string;
  to?: string;
  cameraId?: number;
  eventType?: EventType;
  severity?: Severity;
  state?: EventState;
  search?: string;
  page: number;
  pageSize: number;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface ActionPayload {
  action: ActionType;
  reason?: string;
  /** Optimistic concurrency — server stale phải trả 409 (PRD §10.2). */
  expectedVersion: number;
}

export interface LoginResult {
  user: User;
  token: string;
}

/** Live-loop clock đăng ký bởi CV producer — để web đồng bộ playhead camera. */
export interface StreamClockEntry {
  camera_id: number;
  epoch: number;
  duration: number;
}

/**
 * Hợp đồng duy nhất mà UI biết tới. Có hai implementation: HTTP thật và mock
 * in-memory. Nhờ vậy BAC-49→54 phát triển và demo được khi backend chưa xong.
 */
export interface ApiTransport {
  login(username: string, password: string): Promise<LoginResult>;
  me(): Promise<User>;
  getCameras(): Promise<Camera[]>;
  getEvents(query: IncidentQuery): Promise<Page<SecurityEvent>>;
  getEvent(id: number): Promise<SecurityEvent>;
  postAction(id: number, payload: ActionPayload): Promise<SecurityEvent>;
  getAuditLog(): Promise<EventAction[]>;
  triggerSimulation(): Promise<void>;
  getStreamClock(): Promise<StreamClockEntry[]>;
}

export const DEFAULT_PAGE_SIZE = 10;

export const EMPTY_QUERY: IncidentQuery = {
  page: 1,
  pageSize: DEFAULT_PAGE_SIZE,
};
