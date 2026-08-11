import { RotateCcw, Search } from 'lucide-react';

import { IncidentQuery } from '../../api/types';
import {
  Camera,
  EVENT_TYPE_LABEL,
  EventState,
  EventType,
  STATE_LABEL,
  SEVERITY_LABEL,
  Severity,
} from '../../domain/types';

interface IncidentFiltersProps {
  query: IncidentQuery;
  cameras: Camera[];
  onChange: (patch: Partial<IncidentQuery>) => void;
  onReset: () => void;
}

const EVENT_TYPES: EventType[] = [
  'ZONE_INTRUSION',
  'CROWD_THRESHOLD',
  'ABANDONED_OBJECT',
  'SUSPECTED_FALL',
  'COVERAGE_DEGRADED',
];

const SEVERITIES: Severity[] = ['INFO', 'WARNING', 'HIGH', 'CRITICAL'];

const STATES: EventState[] = [
  'OPEN',
  'ACKNOWLEDGED',
  'PENDING_REVIEW',
  'CONFIRMED',
  'RESOLVED',
  'DISMISSED',
  'EXPIRED',
];

const FIELD =
  'w-full rounded-xl border border-gray-300 dark:border-gray-800 bg-slate-50 dark:bg-gray-950 px-3 py-2 text-xs text-gray-900 dark:text-gray-200 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm';

const LABEL = 'mb-1 block font-mono text-[10px] font-bold uppercase text-gray-600 dark:text-gray-400';

/** Bộ lọc hoạt động độc lập và kết hợp được — acceptance criteria BAC-54. */
export function IncidentFilters({
  query,
  cameras,
  onChange,
  onReset,
}: IncidentFiltersProps) {
  const patch = (value: Partial<IncidentQuery>) => onChange({ ...value, page: 1 });

  return (
    <section
      aria-label="Bộ lọc sự cố"
      className="grid grid-cols-2 gap-3.5 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 p-4.5 md:grid-cols-3 xl:grid-cols-7 shadow-sm"
    >
      <div className="col-span-2 md:col-span-3 xl:col-span-2">
        <label htmlFor="filter-search" className={LABEL}>
          Tìm kiếm
        </label>
        <div className="relative">
          <Search
            className="pointer-events-none absolute inset-y-0 left-3 my-auto h-3.5 w-3.5 text-gray-400 dark:text-gray-500"
            aria-hidden
          />
          <input
            id="filter-search"
            value={query.search ?? ''}
            onChange={(event) => patch({ search: event.target.value || undefined })}
            className={`${FIELD} pl-8`}
            placeholder="Mô tả hoặc tên camera…"
          />
        </div>
      </div>

      <div>
        <label htmlFor="filter-camera" className={LABEL}>
          Camera
        </label>
        <select
          id="filter-camera"
          value={query.cameraId ?? ''}
          onChange={(event) =>
            patch({ cameraId: event.target.value ? Number(event.target.value) : undefined })
          }
          className={FIELD}
        >
          <option value="">Tất cả</option>
          {cameras.map((camera) => (
            <option key={camera.id} value={camera.id}>
              {camera.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="filter-type" className={LABEL}>
          Loại sự kiện
        </label>
        <select
          id="filter-type"
          value={query.eventType ?? ''}
          onChange={(event) =>
            patch({ eventType: (event.target.value as EventType) || undefined })
          }
          className={FIELD}
        >
          <option value="">Tất cả</option>
          {EVENT_TYPES.map((type) => (
            <option key={type} value={type}>
              {EVENT_TYPE_LABEL[type]}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="filter-severity" className={LABEL}>
          Mức độ
        </label>
        <select
          id="filter-severity"
          value={query.severity ?? ''}
          onChange={(event) =>
            patch({ severity: (event.target.value as Severity) || undefined })
          }
          className={FIELD}
        >
          <option value="">Tất cả</option>
          {SEVERITIES.map((severity) => (
            <option key={severity} value={severity}>
              {SEVERITY_LABEL[severity]}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="filter-state" className={LABEL}>
          Trạng thái
        </label>
        <select
          id="filter-state"
          value={query.state ?? ''}
          onChange={(event) =>
            patch({ state: (event.target.value as EventState) || undefined })
          }
          className={FIELD}
        >
          <option value="">Tất cả</option>
          {STATES.map((state) => (
            <option key={state} value={state}>
              {STATE_LABEL[state]}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="filter-from" className={LABEL}>
          Từ thời điểm
        </label>
        <input
          id="filter-from"
          type="datetime-local"
          value={query.from ?? ''}
          onChange={(event) => patch({ from: event.target.value || undefined })}
          className={FIELD}
        />
      </div>

      <div>
        <label htmlFor="filter-to" className={LABEL}>
          Đến thời điểm
        </label>
        <input
          id="filter-to"
          type="datetime-local"
          value={query.to ?? ''}
          onChange={(event) => patch({ to: event.target.value || undefined })}
          className={FIELD}
        />
      </div>

      <div className="col-span-2 flex items-end md:col-span-1">
        <button
          onClick={onReset}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-gray-300 dark:border-gray-700 bg-slate-100 dark:bg-gray-800 px-3 py-2 text-xs font-semibold text-gray-700 dark:text-gray-200 transition-colors hover:bg-slate-200 dark:hover:bg-gray-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 shadow-sm"
        >
          <RotateCcw className="h-3.5 w-3.5" aria-hidden />
          <span>Xóa lọc</span>
        </button>
      </div>
    </section>
  );
}
