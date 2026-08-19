import { RotateCcw } from 'lucide-react';

import { Card } from '@astryxdesign/core/Card';
import { Grid } from '@astryxdesign/core/Grid';
import { TextInput } from '@astryxdesign/core/TextInput';
import { Selector } from '@astryxdesign/core/Selector';
import { Button } from '@astryxdesign/core/Button';

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

export function IncidentFilters({
  query,
  cameras,
  onChange,
  onReset,
}: IncidentFiltersProps) {
  const patch = (value: Partial<IncidentQuery>) => onChange({ ...value, page: 1 });

  return (
    <Card elevation="low" padding={3}>
      <Grid columns={{ minWidth: 150, max: 6 }} gap={2} align="end">
        {/* Search */}
        <TextInput
          label="Tìm kiếm"
          value={query.search ?? ''}
          onChange={(val) => patch({ search: val || undefined })}
          placeholder="Mô tả hoặc tên camera…"
          size="sm"
        />

        {/* Camera Selector */}
        <Selector
          label="Camera"
          value={query.cameraId != null ? String(query.cameraId) : ''}
          onChange={(val) => patch({ cameraId: val ? Number(val) : undefined })}
          size="sm"
          options={[
            { value: '', label: 'Tất cả camera' },
            ...cameras.map((c) => ({ value: String(c.id), label: c.name })),
          ]}
        />

        {/* Event Type Selector */}
        <Selector
          label="Loại sự kiện"
          value={query.eventType ?? ''}
          onChange={(val) => patch({ eventType: (val as EventType) || undefined })}
          size="sm"
          options={[
            { value: '', label: 'Tất cả loại sự kiện' },
            ...EVENT_TYPES.map((t) => ({ value: t, label: EVENT_TYPE_LABEL[t] })),
          ]}
        />

        {/* Severity Selector */}
        <Selector
          label="Mức độ"
          value={query.severity ?? ''}
          onChange={(val) => patch({ severity: (val as Severity) || undefined })}
          size="sm"
          options={[
            { value: '', label: 'Tất cả mức độ' },
            ...SEVERITIES.map((s) => ({ value: s, label: SEVERITY_LABEL[s] })),
          ]}
        />

        {/* State Selector */}
        <Selector
          label="Trạng thái"
          value={query.state ?? ''}
          onChange={(val) => patch({ state: (val as EventState) || undefined })}
          size="sm"
          options={[
            { value: '', label: 'Tất cả trạng thái' },
            ...STATES.map((st) => ({ value: st, label: STATE_LABEL[st] })),
          ]}
        />

        {/* Reset button */}
        <Button
          label="Xóa bộ lọc"
          variant="secondary"
          size="sm"
          width="100%"
          icon={<RotateCcw size={14} />}
          onClick={onReset}
        />
      </Grid>
    </Card>
  );
}

