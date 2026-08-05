/**
 * Smoke test cho giao diện điện thoại của Quản lý an ninh.
 *
 * Kiểm ba thứ mà `tsc` không thấy được: phân quyền route, hộp thư có lọc đúng
 * "thông báo quan trọng" hay không, và cảnh báo mới đến qua kênh realtime có
 * thực sự nổi lên trước mặt người trực hay không.
 */

import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { App } from '../../App';
import { TOKEN_STORAGE_KEY, USER_STORAGE_KEY } from '../../api/config';
import { mockTransport } from '../../api/mock/mockTransport';

const MANAGER = {
  id: 2,
  username: 'manager',
  fullName: 'Quản Lý Trần Văn B',
  role: 'MANAGER',
  cameraScope: [],
};

const GUARD = {
  id: 1,
  username: 'guard',
  fullName: 'Bảo Vệ Nguyễn Văn A',
  role: 'GUARD',
  cameraScope: [],
};

function signIn(user: typeof MANAGER | typeof GUARD) {
  localStorage.setItem(TOKEN_STORAGE_KEY, `mock-token-${user.username}`);
  localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

beforeEach(() => localStorage.clear());
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('Phân quyền khu vực điện thoại', () => {
  it('Quản lý vào được hộp thư', async () => {
    signIn(MANAGER);
    renderAt('/m');

    expect(
      await screen.findByRole('heading', { name: /Thông báo quan trọng/i }),
    ).toBeDefined();
  });

  it('Bảo vệ bị chặn khỏi khu vực của Quản lý', async () => {
    signIn(GUARD);
    renderAt('/m');

    expect(await screen.findByText(/Không đủ quyền truy cập/i)).toBeDefined();
    expect(screen.queryByRole('heading', { name: /Thông báo quan trọng/i })).toBeNull();
  });

  it('chưa đăng nhập thì đẩy về trang đăng nhập', async () => {
    renderAt('/m');
    expect(await screen.findByLabelText(/Tên tài khoản/i)).toBeDefined();
  });

  it('mở được nhật ký thao tác', async () => {
    signIn(MANAGER);
    renderAt('/m/audit');

    expect(await screen.findByRole('heading', { name: /Nhật ký thao tác/i })).toBeDefined();
    expect(screen.getByLabelText(/Tìm trong nhật ký/i)).toBeDefined();
  });
});

describe('Hộp thư chỉ chứa việc của Quản lý', () => {
  beforeEach(() => signIn(MANAGER));

  it('bỏ qua sự cố nhẹ và sự cố đã đóng', async () => {
    renderAt('/m');
    await screen.findByRole('heading', { name: /Thông báo quan trọng/i });

    const list = await screen.findByRole('list', { name: /Danh sách thông báo/i });
    const rows = within(list).getAllByRole('link');

    // Fixture có 7 sự cố; chỉ 3 cái thuộc trách nhiệm Quản lý:
    // CRITICAL chờ duyệt, HIGH đang xin ý kiến, CRITICAL đã xác nhận.
    expect(rows).toHaveLength(3);

    // Sự cố tụ tập mức cảnh báo và các sự cố đã đóng không được lọt vào.
    expect(within(list).queryByText(/Nhóm nhân viên tụ tập/i)).toBeNull();
    expect(within(list).queryByText(/Thùng carton/i)).toBeNull();
  });

  it('đếm đúng số việc đang chờ quyết định', async () => {
    renderAt('/m');

    // 2 việc phải quyết: CRITICAL chờ duyệt + escalation đang chờ.
    // Sự cố đã CONFIRMED chỉ để theo dõi, không tính.
    expect(await screen.findByText(/2 việc/i)).toBeDefined();
    expect(await screen.findByLabelText(/2 việc cần xử lý/i)).toBeDefined();
  });

  it('xếp việc cần quyết lên trước việc chỉ theo dõi', async () => {
    renderAt('/m');
    const list = await screen.findByRole('list', { name: /Danh sách thông báo/i });
    const rows = within(list).getAllByRole('link');

    // Hai dòng đầu là việc phải quyết nên không hiện nhãn trạng thái theo dõi.
    expect(within(rows[0]).queryByText(/Đã xác nhận/i)).toBeNull();
    expect(within(rows[2]).getByText(/Đã xác nhận/i)).toBeDefined();
  });
});

describe('Nhận thông báo quan trọng', () => {
  it('cảnh báo nghiêm trọng mới đến sẽ nổi lên ngay, không cần tải lại', async () => {
    signIn(MANAGER);
    // Kịch bản giả lập chọn ngẫu nhiên — ghim về mục đầu (xâm nhập, CRITICAL).
    vi.spyOn(Math, 'random').mockReturnValue(0);

    renderAt('/m');
    await screen.findByRole('heading', { name: /Thông báo quan trọng/i });

    await act(async () => {
      await mockTransport.triggerSimulation();
    });

    const toastArea = await screen.findByRole('region', { name: /Thông báo quan trọng/i });
    await waitFor(() =>
      expect(within(toastArea).getByText(/Khẩn cấp/i)).toBeDefined(),
    );
    expect(within(toastArea).getByText(/Chạm để xử lý/i)).toBeDefined();
  });

  it('cảnh báo tới lúc trang đang tải lần đầu vẫn được báo, không bị nuốt', async () => {
    signIn(MANAGER);
    vi.spyOn(Math, 'random').mockReturnValue(0);

    renderAt('/m');

    // Cố tình KHÔNG chờ dữ liệu tải xong. Bản trước dựa vào mốc "tải xong" để
    // phân biệt lịch sử với cảnh báo mới, nên cảnh báo rơi vào đúng khoảng này
    // bị xếp nhầm là lịch sử và im lặng luôn.
    await act(async () => {
      await mockTransport.triggerSimulation();
    });

    const toastArea = await screen.findByRole('region', { name: /Thông báo quan trọng/i });
    expect(within(toastArea).getByText(/Khẩn cấp/i)).toBeDefined();
  });

  it('không báo lại lịch sử mỗi lần kết nối lại', async () => {
    signIn(MANAGER);
    renderAt('/m');

    // Chờ tải xong: 3 sự cố quan trọng có sẵn trong dữ liệu mẫu.
    await screen.findByRole('list', { name: /Danh sách thông báo/i });

    // Không có thông báo nào nổi lên vì chúng đến từ REST, không phải realtime.
    expect(screen.queryByRole('region', { name: /Thông báo quan trọng/i })).toBeNull();
  });
});
