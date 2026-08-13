/**
 * Test cho kênh realtime — ba acceptance criteria động của BAC-51:
 *   - alert mới xuất hiện không cần refresh
 *   - có trạng thái mất kết nối và tự reconnect
 *   - không tạo trùng alert sau reconnect
 *
 * Dùng WebSocket giả để lái được các tình huống mất kết nối, gửi lặp và
 * message hỏng — những thứ không dựng lại được bằng thao tác tay.
 */

import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useAlertStream } from './useAlertStream';

// Hook rẽ nhánh sang mock bus khi isMockMode = true; ở đây cần nhánh WS thật.
vi.mock('../api', () => ({ isMockMode: false }));

type Handler = ((event: unknown) => void) | null;

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];

  onopen: Handler = null;
  onmessage: Handler = null;
  onclose: Handler = null;
  onerror: Handler = null;
  closed = false;

  constructor(public url: string) {
    FakeWebSocket.instances.push(this);
  }

  close() {
    this.closed = true;
  }

  /* --- điều khiển từ phía test --- */
  open() {
    this.onopen?.({});
  }

  message(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }

  raw(data: string) {
    this.onmessage?.({ data });
  }

  drop() {
    this.onclose?.({});
  }

  static get latest() {
    return FakeWebSocket.instances[FakeWebSocket.instances.length - 1];
  }
}

const NEW_ALERT = {
  type: 'NEW_ALERT',
  incident: {
    id: 4,
    camera_id: 3,
    camera_name: 'Camera Hàng Rào Tây',
    event_type: 'xam_nhap',
    severity: 'critical',
    description: 'CẢNH BÁO CRITICAL: Phát hiện vượt hàng rào phía Tây!',
    status: 'pending',
    created_at: '2026-08-04T16:38:58.580962',
  },
};

function makeHandlers() {
  return {
    onEventCreated: vi.fn(),
    onEventUpdated: vi.fn(),
    onReconcile: vi.fn(),
  };
}

beforeEach(() => {
  FakeWebSocket.instances = [];
  vi.stubGlobal('WebSocket', FakeWebSocket);
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('Kết nối và nhận cảnh báo', () => {
  it('mở kênh và báo trạng thái open khi kết nối thành công', () => {
    const handlers = makeHandlers();
    const { result } = renderHook(() => useAlertStream(handlers));

    expect(result.current.status).toBe('connecting');
    act(() => FakeWebSocket.latest.open());

    expect(result.current.status).toBe('open');
  });

  it('gọi reconcile qua REST ngay khi kết nối — WS không phải source of truth', () => {
    const handlers = makeHandlers();
    renderHook(() => useAlertStream(handlers));

    act(() => FakeWebSocket.latest.open());
    expect(handlers.onReconcile).toHaveBeenCalledTimes(1);
  });

  it('NEW_ALERT được quy đổi sang domain model và đẩy ra ngoài', () => {
    const handlers = makeHandlers();
    renderHook(() => useAlertStream(handlers));

    act(() => {
      FakeWebSocket.latest.open();
      FakeWebSocket.latest.message(NEW_ALERT);
    });

    expect(handlers.onEventCreated).toHaveBeenCalledTimes(1);
    const event = handlers.onEventCreated.mock.calls[0][0];
    expect(event.id).toBe(4);
    expect(event.eventType).toBe('ZONE_INTRUSION');
    expect(event.effectiveSeverity).toBe('CRITICAL');
    // Timestamp phải được chuẩn hóa về UTC, không lệch múi giờ máy.
    expect(event.detectedAt).toBe('2026-08-04T16:38:58.580962Z');
  });

  it('ALERT_UPDATED chỉ báo id để caller tự tải lại chi tiết', () => {
    const handlers = makeHandlers();
    renderHook(() => useAlertStream(handlers));

    act(() => {
      FakeWebSocket.latest.open();
      FakeWebSocket.latest.message({
        type: 'ALERT_UPDATED',
        incident_id: 4,
        status: 'acknowledged',
        action_by: 'Bảo Vệ Nguyễn Văn A',
      });
    });

    expect(handlers.onEventUpdated).toHaveBeenCalledWith(4);
    expect(handlers.onEventCreated).not.toHaveBeenCalled();
  });

  it('message hỏng không làm sập kênh', () => {
    const handlers = makeHandlers();
    const { result } = renderHook(() => useAlertStream(handlers));

    act(() => {
      FakeWebSocket.latest.open();
      FakeWebSocket.latest.raw('{ khong phai json');
      FakeWebSocket.latest.message(NEW_ALERT);
    });

    expect(result.current.status).toBe('open');
    expect(handlers.onEventCreated).toHaveBeenCalledTimes(1);
  });
});

describe('Chống trùng lặp', () => {
  it('cùng một alert gửi hai lần chỉ được xử lý một lần', () => {
    const handlers = makeHandlers();
    renderHook(() => useAlertStream(handlers));

    act(() => {
      FakeWebSocket.latest.open();
      FakeWebSocket.latest.message(NEW_ALERT);
      FakeWebSocket.latest.message(NEW_ALERT);
      FakeWebSocket.latest.message(NEW_ALERT);
    });

    expect(handlers.onEventCreated).toHaveBeenCalledTimes(1);
  });

  it('alert gửi lại sau khi reconnect không tạo bản trùng', () => {
    const handlers = makeHandlers();
    renderHook(() => useAlertStream(handlers));

    act(() => {
      FakeWebSocket.latest.open();
      FakeWebSocket.latest.message(NEW_ALERT);
    });
    expect(handlers.onEventCreated).toHaveBeenCalledTimes(1);

    // Rớt kết nối rồi kết nối lại, server phát lại đúng message đó.
    act(() => FakeWebSocket.latest.drop());
    act(() => void vi.advanceTimersByTime(2000));
    act(() => {
      FakeWebSocket.latest.open();
      FakeWebSocket.latest.message(NEW_ALERT);
    });

    expect(handlers.onEventCreated).toHaveBeenCalledTimes(1);
  });

  it('alert khác id vẫn được nhận bình thường', () => {
    const handlers = makeHandlers();
    renderHook(() => useAlertStream(handlers));

    act(() => {
      FakeWebSocket.latest.open();
      FakeWebSocket.latest.message(NEW_ALERT);
      FakeWebSocket.latest.message({
        ...NEW_ALERT,
        incident: { ...NEW_ALERT.incident, id: 5 },
      });
    });

    expect(handlers.onEventCreated).toHaveBeenCalledTimes(2);
  });
});

describe('Mất kết nối và tự kết nối lại', () => {
  it('rớt kết nối thì chuyển sang trạng thái báo mất kết nối', () => {
    const handlers = makeHandlers();
    const { result } = renderHook(() => useAlertStream(handlers));

    act(() => FakeWebSocket.latest.open());
    expect(result.current.status).toBe('open');

    act(() => FakeWebSocket.latest.drop());
    expect(result.current.status).toBe('offline');
  });

  it('tự mở kết nối mới sau khoảng chờ', () => {
    const handlers = makeHandlers();
    renderHook(() => useAlertStream(handlers));

    act(() => FakeWebSocket.latest.open());
    expect(FakeWebSocket.instances).toHaveLength(1);

    act(() => FakeWebSocket.latest.drop());
    act(() => void vi.advanceTimersByTime(1000));

    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it('mỗi lần kết nối lại đều reconcile để bù message đã rơi', () => {
    const handlers = makeHandlers();
    renderHook(() => useAlertStream(handlers));

    act(() => FakeWebSocket.latest.open());
    expect(handlers.onReconcile).toHaveBeenCalledTimes(1);

    act(() => FakeWebSocket.latest.drop());
    act(() => void vi.advanceTimersByTime(1000));
    act(() => FakeWebSocket.latest.open());

    expect(handlers.onReconcile).toHaveBeenCalledTimes(2);
  });

  it('khoảng chờ giãn dần chứ không quay vòng liên tục', () => {
    const handlers = makeHandlers();
    renderHook(() => useAlertStream(handlers));

    act(() => FakeWebSocket.latest.open());
    act(() => FakeWebSocket.latest.drop());

    // Lần 1: chờ 1s
    act(() => void vi.advanceTimersByTime(1000));
    expect(FakeWebSocket.instances).toHaveLength(2);

    // Lần 2 phải chờ lâu hơn 1s
    act(() => FakeWebSocket.latest.drop());
    act(() => void vi.advanceTimersByTime(1000));
    expect(FakeWebSocket.instances).toHaveLength(2);

    act(() => void vi.advanceTimersByTime(1000));
    expect(FakeWebSocket.instances).toHaveLength(3);
  });

  it('unmount thì dừng hẳn, không kết nối lại nữa', () => {
    const handlers = makeHandlers();
    const { unmount } = renderHook(() => useAlertStream(handlers));

    act(() => FakeWebSocket.latest.open());
    unmount();

    act(() => void vi.advanceTimersByTime(30_000));
    expect(FakeWebSocket.instances).toHaveLength(1);
  });
});
