/**
 * Transport in-memory — cho phép chạy và demo toàn bộ UI khi backend chưa sẵn
 * sàng (acceptance criteria của BAC-49).
 *
 * Mock cố tình enforce đúng luật nghiệp vụ: kiểm tra role, bắt buộc reason,
 * bump version và trả 409 khi client gửi `expectedVersion` cũ. Nhờ vậy các
 * nhánh lỗi 403/409 của BAC-53 kiểm chứng được mà không cần backend.
 */

import { ActionType, EventAction, SecurityEvent, User } from '../../domain/types';
import { allowedActions, reasonRequired } from '../../domain/permissions';
import { ApiError } from '../errors';
import { applyQuery } from '../query';
import { ActionPayload, ApiTransport, IncidentQuery, LoginResult } from '../types';
import { MOCK_CAMERAS, MOCK_EVENTS, MOCK_USERS, SIMULATION_TEMPLATES } from './fixtures';

/* --------------------------------- state ------------------------------------ */

let events: SecurityEvent[] = MOCK_EVENTS.map((event) => ({
  ...event,
  actions: [...event.actions],
}));
let nextEventId = 200;
let nextActionId = 10_000;

let actorGetter: () => User | null = () => null;

export function setMockActorGetter(getter: () => User | null): void {
  actorGetter = getter;
}

function currentActor(): User {
  const actor = actorGetter();
  if (!actor) throw ApiError.fromStatus(401);
  return actor;
}

const latency = () => new Promise((resolve) => setTimeout(resolve, 180));

/* ------------------------------- event bus ---------------------------------- */

type Listener = (event: SecurityEvent, kind: 'created' | 'updated') => void;

const listeners = new Set<Listener>();
let simulationTimer: ReturnType<typeof setInterval> | null = null;

function emit(event: SecurityEvent, kind: 'created' | 'updated'): void {
  listeners.forEach((listener) => listener(event, kind));
}

/** Dùng bởi `useAlertStream` khi chạy mock mode thay cho WebSocket thật. */
export function subscribeMockStream(listener: Listener): () => void {
  listeners.add(listener);

  // Tự sinh sự cố mới mỗi 45 giây để demo luồng realtime.
  if (!simulationTimer) {
    simulationTimer = setInterval(() => {
      if (listeners.size > 0) void mockTransport.triggerSimulation();
    }, 45_000);
  }

  return () => {
    listeners.delete(listener);
    if (listeners.size === 0 && simulationTimer) {
      clearInterval(simulationTimer);
      simulationTimer = null;
    }
  };
}

/* ---------------------------- state transitions ------------------------------ */

/** Kết quả của một action lên cặp (state, escalation). */
function applyTransition(event: SecurityEvent, action: ActionType): SecurityEvent {
  const next: SecurityEvent = { ...event };

  switch (action) {
    case 'ACKNOWLEDGE':
      next.state = 'ACKNOWLEDGED';
      break;
    case 'CONFIRM':
      next.state = 'CONFIRMED';
      break;
    case 'RESOLVE':
      next.state = 'RESOLVED';
      break;
    case 'DISMISS':
      next.state = 'DISMISSED';
      break;
    case 'REQUEST_ESCALATION':
      next.escalation = 'REQUESTED';
      break;
    case 'APPROVE_ESCALATION':
      next.escalation = 'APPROVED';
      break;
    case 'DECLINE_ESCALATION':
      next.escalation = 'DECLINED';
      break;
  }
  return next;
}

/* -------------------------------- transport --------------------------------- */

export const mockTransport: ApiTransport = {
  async login(username, password): Promise<LoginResult> {
    await latency();
    const entry = MOCK_USERS[username];
    if (!entry || entry.password !== password) {
      throw ApiError.fromStatus(400, 'Tài khoản hoặc mật khẩu không chính xác');
    }
    return { user: entry.user, token: `mock-token-${username}` };
  },

  async me(): Promise<User> {
    await latency();
    return currentActor();
  },

  async getCameras() {
    await latency();
    return MOCK_CAMERAS;
  },

  async getEvents(query: IncidentQuery) {
    await latency();
    return applyQuery(events, query);
  },

  async getEvent(id: number) {
    await latency();
    const found = events.find((event) => event.id === id);
    if (!found) throw ApiError.fromStatus(404);
    return found;
  },

  async postAction(id: number, payload: ActionPayload) {
    await latency();
    const actor = currentActor();
    const index = events.findIndex((event) => event.id === id);
    if (index < 0) throw ApiError.fromStatus(404);

    const event = events[index];

    // Optimistic concurrency — giống hành vi `expectedVersion` ở PRD §10.2.
    if (payload.expectedVersion !== event.version) {
      throw ApiError.fromStatus(409);
    }

    // Server phải kiểm tra lại matrix, không tin UI đã ẩn nút.
    const permitted = allowedActions(event, actor.role, actor.cameraScope).some(
      (spec) => spec.type === payload.action,
    );
    if (!permitted) throw ApiError.fromStatus(403);

    if (
      reasonRequired(payload.action, event.effectiveSeverity) &&
      !payload.reason?.trim()
    ) {
      throw ApiError.fromStatus(400, 'Thao tác này bắt buộc nhập lý do.');
    }

    const action: EventAction = {
      id: nextActionId++,
      actorName: actor.fullName,
      action: payload.action,
      reason: payload.reason?.trim() || undefined,
      incidentId: event.id,
      at: new Date().toISOString(),
    };

    const updated = applyTransition(event, payload.action);
    updated.version = event.version + 1;
    updated.actions = [...event.actions, action];

    events = [...events.slice(0, index), updated, ...events.slice(index + 1)];
    emit(updated, 'updated');
    return updated;
  },

  async getAuditLog(): Promise<EventAction[]> {
    await latency();
    return events
      .flatMap((event) => event.actions)
      .sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime());
  },

  async triggerSimulation(): Promise<void> {
    const template =
      SIMULATION_TEMPLATES[Math.floor(Math.random() * SIMULATION_TEMPLATES.length)];

    const severe =
      template.effectiveSeverity === 'HIGH' || template.effectiveSeverity === 'CRITICAL';

    const created: SecurityEvent = {
      id: nextEventId++,
      cameraId: template.cameraId,
      cameraName: template.cameraName,
      eventType: template.eventType,
      effectiveSeverity: template.effectiveSeverity,
      state: severe ? 'PENDING_REVIEW' : 'OPEN',
      escalation: 'NONE',
      description: template.description,
      aiGenerated: true,
      detectedAt: new Date().toISOString(),
      version: 1,
      bbox: template.bbox,
      artifact: {
        url: MOCK_CAMERAS.find((cam) => cam.id === template.cameraId)?.previewUrl ?? '',
        redactionStatus: 'COMPLETE',
      },
      actions: [],
    };

    events = [created, ...events];
    emit(created, 'created');
  },
};
