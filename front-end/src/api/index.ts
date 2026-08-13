/**
 * Điểm vào duy nhất của tầng API. UI chỉ import từ đây, không bao giờ gọi
 * `fetch` trực tiếp — nhờ vậy đổi transport (thật ↔ mock) không đụng component.
 */

import { User } from '../domain/types';
import { USE_MOCK } from './config';
import { httpTransport, setTokenGetter } from './httpTransport';
import { mockTransport, setMockActorGetter } from './mock/mockTransport';
import { ApiTransport } from './types';

export const api: ApiTransport = USE_MOCK ? mockTransport : httpTransport;

export const isMockMode = USE_MOCK;

/** AuthContext gọi một lần khi khởi động để tầng API biết token/actor hiện tại. */
export function bindAuth(
  getToken: () => string | null,
  getUser: () => User | null,
): void {
  setTokenGetter(getToken);
  setMockActorGetter(getUser);
}

export * from './types';
export { ApiError } from './errors';
export { toApiError } from './errors';
export { API_BASE_URL, WS_URL } from './config';
