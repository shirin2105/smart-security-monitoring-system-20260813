/** Transport thật — gọi FastAPI backend. */

import { EventAction, SecurityEvent, User } from '../domain/types';
import { API_BASE_URL } from './config';
import {
  RawAuditLog,
  RawCamera,
  RawIncident,
  RawUser,
  toAuditAction,
  toCamera,
  toEvent,
  toUser,
} from './adapters';
import { ApiError, notImplemented, toApiError } from './errors';
import { applyQuery } from './query';
import { ActionPayload, ApiTransport, IncidentQuery, LoginResult, Page } from './types';

/** AuthContext nạp getter vào đây để mọi request tự đính token. */
let tokenGetter: () => string | null = () => null;

export function setTokenGetter(getter: () => string | null): void {
  tokenGetter = getter;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = tokenGetter();
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init.headers ?? {}),
      },
    });
  } catch {
    // Lỗi mạng / backend không chạy — fetch reject trước khi có status.
    throw toApiError(null);
  }

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const body = await response.json();
      detail = typeof body?.detail === 'string' ? body.detail : undefined;
    } catch {
      /* body rỗng hoặc không phải JSON — dùng thông điệp mặc định */
    }
    throw ApiError.fromStatus(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** Audit log của backend là nguồn duy nhất cho action history hiện tại. */
async function fetchActionsByIncident(): Promise<Map<number, EventAction[]>> {
  const raw = await request<RawAuditLog[]>('/api/v1/alerts/audit-logs');
  const byIncident = new Map<number, EventAction[]>();
  for (const row of raw) {
    if (row.incident_id == null) continue;
    const action = toAuditAction(row);
    const list = byIncident.get(row.incident_id) ?? [];
    list.push(action);
    byIncident.set(row.incident_id, list);
  }
  return byIncident;
}

async function loadEvents(): Promise<SecurityEvent[]> {
  const [rawIncidents, actionMap] = await Promise.all([
    request<RawIncident[]>('/api/v1/alerts'),
    // Audit log hỏng không được làm hỏng cả danh sách sự cố.
    fetchActionsByIncident().catch(() => new Map<number, EventAction[]>()),
  ]);
  return rawIncidents.map((raw) => toEvent(raw, actionMap.get(raw.id) ?? []));
}

/**
 * Action nào backend đã có endpoint. Những action còn lại vẫn hiển thị đúng
 * theo matrix nhưng khi bấm sẽ báo rõ "backend chưa hỗ trợ" thay vì fail câm.
 */
const ACTION_ENDPOINTS: Partial<Record<ActionPayload['action'], string>> = {
  ACKNOWLEDGE: 'acknowledge',
  REQUEST_ESCALATION: 'escalate',
};

export const httpTransport: ApiTransport = {
  async login(username, password): Promise<LoginResult> {
    const data = await request<{ access_token: string; user: RawUser }>(
      '/api/v1/auth/login',
      { method: 'POST', body: JSON.stringify({ username, password }) },
    );
    return { user: toUser(data.user), token: data.access_token };
  },

  async me(): Promise<User> {
    return toUser(await request<RawUser>('/api/v1/auth/me'));
  },

  async getCameras() {
    const raw = await request<RawCamera[]>('/api/v1/cameras');
    return raw.map(toCamera);
  },

  async getEvents(query: IncidentQuery): Promise<Page<SecurityEvent>> {
    // Lọc/phân trang tạm ở client cho tới khi BAC-47 có query params thật.
    return applyQuery(await loadEvents(), query);
  },

  async getEvent(id: number): Promise<SecurityEvent> {
    const found = (await loadEvents()).find((event) => event.id === id);
    if (!found) throw ApiError.fromStatus(404);
    return found;
  },

  async postAction(id: number, payload: ActionPayload): Promise<SecurityEvent> {
    const endpoint = ACTION_ENDPOINTS[payload.action];
    if (!endpoint) throw notImplemented(payload.action);

    await request(`/api/v1/alerts/${id}/${endpoint}`, {
      method: 'POST',
      body: JSON.stringify({
        reason: payload.reason,
        expected_version: payload.expectedVersion,
      }),
    });
    return this.getEvent(id);
  },

  async getAuditLog(): Promise<EventAction[]> {
    const raw = await request<RawAuditLog[]>('/api/v1/alerts/audit-logs');
    return raw.map(toAuditAction);
  },

  async triggerSimulation(): Promise<void> {
    await request('/api/v1/alerts/simulate', { method: 'POST' });
  },
};
