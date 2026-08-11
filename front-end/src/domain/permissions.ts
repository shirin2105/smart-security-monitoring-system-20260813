/**
 * Full state × role action matrix — PRD §8.4 và điều kiện PASS của Gate 2.
 *
 * QUAN TRỌNG: đây là lớp trình bày, KHÔNG phải lớp bảo mật. Backend bắt buộc
 * phải enforce lại toàn bộ matrix này (FR-BE-05: "UI hiding không là security
 * control"). Ẩn nút chỉ để người trực không bấm nhầm.
 *
 * Luật rút gọn:
 *   - Guard   : acknowledge/resolve/dismiss INFO|WARNING + request escalation.
 *   - Manager : mọi quyền của Guard, thêm confirm/dismiss HIGH|CRITICAL,
 *               resolve event đã confirm, và approve/decline escalation.
 *   - Không ai được auto-confirm; escalation quá hạn chỉ EXPIRED, không tự duyệt.
 */

import {
  ActionType,
  Role,
  SecurityEvent,
  Severity,
  isSevere,
  isTerminal,
} from './types';

export interface ActionSpec {
  type: ActionType;
  label: string;
  /** Bắt buộc nhập lý do trước khi gửi (PRD §8.4). */
  requiresReason: boolean;
  tone: 'primary' | 'danger' | 'neutral' | 'warning';
}

export const ACTION_SPECS: Record<ActionType, ActionSpec> = {
  ACKNOWLEDGE: {
    type: 'ACKNOWLEDGE',
    label: 'Tiếp nhận',
    requiresReason: false,
    tone: 'primary',
  },
  RESOLVE: {
    type: 'RESOLVE',
    label: 'Kết thúc xử lý',
    requiresReason: false,
    tone: 'primary',
  },
  DISMISS: {
    type: 'DISMISS',
    label: 'Bỏ qua',
    requiresReason: true,
    tone: 'neutral',
  },
  CONFIRM: {
    type: 'CONFIRM',
    label: 'Xác nhận sự cố',
    requiresReason: false,
    tone: 'danger',
  },
  REQUEST_ESCALATION: {
    type: 'REQUEST_ESCALATION',
    label: 'Xin ý kiến Quản lý',
    requiresReason: false,
    tone: 'warning',
  },
  APPROVE_ESCALATION: {
    type: 'APPROVE_ESCALATION',
    label: 'Phê duyệt',
    requiresReason: true,
    tone: 'danger',
  },
  DECLINE_ESCALATION: {
    type: 'DECLINE_ESCALATION',
    label: 'Từ chối',
    requiresReason: true,
    tone: 'neutral',
  },
};


/** Reason bắt buộc cho severe dismiss/resolve, ngoài các action vốn đã yêu cầu. */
export function reasonRequired(action: ActionType, severity: Severity): boolean {
  if (ACTION_SPECS[action].requiresReason) return true;
  if (isSevere(severity) && (action === 'RESOLVE' || action === 'DISMISS')) return true;
  return false;
}

/** Action hợp lệ theo state + severity, chưa xét role. */
function stateAllowedActions(event: SecurityEvent): ActionType[] {
  if (isTerminal(event.state)) return [];

  const allowed: ActionType[] = [];

  if (isSevere(event.effectiveSeverity)) {
    // Nhánh HIGH/CRITICAL: PENDING_REVIEW → CONFIRMED → RESOLVED | DISMISSED
    if (event.state === 'PENDING_REVIEW') {
      allowed.push('CONFIRM', 'DISMISS');
    } else if (event.state === 'CONFIRMED') {
      allowed.push('RESOLVE');
    }
  } else {
    // Nhánh INFO/WARNING: OPEN → ACKNOWLEDGED → RESOLVED | DISMISSED
    if (event.state === 'OPEN') {
      allowed.push('ACKNOWLEDGE', 'DISMISS');
    } else if (event.state === 'ACKNOWLEDGED') {
      allowed.push('RESOLVE', 'DISMISS');
    }
  }

  // Escalation chạy song song với vòng đời event.
  if (event.escalation === 'NONE') {
    allowed.push('REQUEST_ESCALATION');
  } else if (event.escalation === 'REQUESTED') {
    allowed.push('APPROVE_ESCALATION', 'DECLINE_ESCALATION');
  }

  return allowed;
}

/** Action mà riêng Manager mới được thực hiện. */
const MANAGER_ONLY: ActionType[] = [
  'CONFIRM',
  'APPROVE_ESCALATION',
  'DECLINE_ESCALATION',
];

function roleAllows(action: ActionType, role: Role, event: SecurityEvent): boolean {
  if (role === 'MANAGER') return true;

  // Guard không chạm được vào bất kỳ quyết định nào trên event severe.
  if (MANAGER_ONLY.includes(action)) return false;
  if (isSevere(event.effectiveSeverity) && action !== 'REQUEST_ESCALATION') {
    return false;
  }
  return true;
}

/** Camera scope — scope rỗng nghĩa là backend chưa cấp, không chặn ở UI. */
export function inScope(event: SecurityEvent, scope: number[]): boolean {
  if (!scope.length) return true;
  return scope.includes(event.cameraId);
}

/**
 * Danh sách action một user được phép thấy trên một event.
 * Trả về mảng rỗng nghĩa là chỉ xem, không có hành động nào hợp lệ.
 */
export function allowedActions(
  event: SecurityEvent,
  role: Role,
  scope: number[] = [],
): ActionSpec[] {
  if (!inScope(event, scope)) return [];
  return stateAllowedActions(event)
    .filter((action) => roleAllows(action, role, event))
    .map((action) => ACTION_SPECS[action]);
}

/**
 * Lý do một event severe không có action nào cho Guard — dùng để hiển thị
 * thông báo thay vì để trống, giúp người trực hiểu tại sao không bấm được.
 */
export function blockedReason(event: SecurityEvent, role: Role): string | null {
  if (isTerminal(event.state)) return null;
  if (role !== 'GUARD') return null;
  if (!isSevere(event.effectiveSeverity)) return null;
  return 'Sự cố mức nghiêm trọng — chỉ Quản lý an ninh mới được xác nhận hoặc bỏ qua.';
}
