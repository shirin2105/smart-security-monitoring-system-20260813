/**
 * Lọc + phân trang phía client.
 *
 * Tạm thời cả HTTP transport lẫn mock đều dùng chung hàm này vì backend chưa có
 * filter/pagination (BAC-47 của Hưng chưa làm). Khi endpoint thật hỗ trợ query
 * params, chỉ cần bỏ lời gọi trong `httpTransport.getEvents` — UI không đổi.
 */

import { SecurityEvent } from '../domain/types';
import { IncidentQuery, Page } from './types';

export function applyQuery(
  all: SecurityEvent[],
  query: IncidentQuery,
): Page<SecurityEvent> {
  const filtered = all.filter((event) => {
    if (query.cameraId != null && event.cameraId !== query.cameraId) return false;
    if (query.eventType && event.eventType !== query.eventType) return false;
    if (query.severity && event.effectiveSeverity !== query.severity) return false;
    if (query.state && event.state !== query.state) return false;

    if (query.from && new Date(event.detectedAt) < new Date(query.from)) return false;
    if (query.to && new Date(event.detectedAt) > new Date(query.to)) return false;

    if (query.search) {
      const needle = query.search.toLowerCase();
      const haystack = `${event.description} ${event.cameraName}`.toLowerCase();
      if (!haystack.includes(needle)) return false;
    }
    return true;
  });

  const sorted = [...filtered].sort(
    (a, b) => new Date(b.detectedAt).getTime() - new Date(a.detectedAt).getTime(),
  );

  const pageSize = Math.max(1, query.pageSize);
  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const page = Math.min(Math.max(1, query.page), totalPages);
  const start = (page - 1) * pageSize;

  return {
    items: sorted.slice(start, start + pageSize),
    total: sorted.length,
    page,
    pageSize,
  };
}
