/**
 * Smoke test cây component.
 *
 * Mục tiêu không phải phủ hết UI mà là bắt sớm những lỗi `tsc` không thấy:
 * sai thứ tự provider, dùng hook router ngoài <BrowserRouter>, import vòng,
 * hoặc route bảo vệ không chuyển hướng.
 */

import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { App } from './App';
import { TOKEN_STORAGE_KEY, USER_STORAGE_KEY } from './api/config';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  localStorage.clear();
});

afterEach(cleanup);

describe('Điều hướng và phân quyền', () => {
  it('chưa đăng nhập thì mọi route được bảo vệ đều đẩy về trang đăng nhập', async () => {
    renderAt('/');
    expect(
      await screen.findByRole('heading', { name: /TRUNG TÂM GIÁM SÁT AN NINH/i }),
    ).toBeDefined();
    expect(screen.getByLabelText(/Tên tài khoản/i)).toBeDefined();
  });

  it('Bảo vệ đăng nhập rồi thì vào được màn giám sát', async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, 'mock-token-guard');
    localStorage.setItem(
      USER_STORAGE_KEY,
      JSON.stringify({
        id: 1,
        username: 'guard',
        fullName: 'Bảo Vệ Nguyễn Văn A',
        role: 'GUARD',
        cameraScope: [],
      }),
    );

    renderAt('/');

    await waitFor(() =>
      expect(screen.getByRole('navigation', { name: /Điều hướng chính/i })).toBeDefined(),
    );
    // Lưới camera nạp từ transport mock.
    await waitFor(() =>
      expect(screen.getByRole('region', { name: /Lưới camera giám sát/i })).toBeDefined(),
    );
  });

  it('Bảo vệ không thấy mục Điểm nóng và bị chặn khi vào thẳng URL', async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, 'mock-token-guard');
    localStorage.setItem(
      USER_STORAGE_KEY,
      JSON.stringify({
        id: 1,
        username: 'guard',
        fullName: 'Bảo Vệ Nguyễn Văn A',
        role: 'GUARD',
        cameraScope: [],
      }),
    );

    renderAt('/heatmap');

    expect(await screen.findByText(/Không đủ quyền truy cập/i)).toBeDefined();
    expect(screen.queryByRole('link', { name: /Điểm nóng/i })).toBeNull();
  });

  it('Quản lý thấy mục Điểm nóng và mở được trang', async () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, 'mock-token-manager');
    localStorage.setItem(
      USER_STORAGE_KEY,
      JSON.stringify({
        id: 2,
        username: 'manager',
        fullName: 'Quản Lý Trần Văn B',
        role: 'MANAGER',
        cameraScope: [],
      }),
    );

    renderAt('/heatmap');

    expect(
      await screen.findByRole('heading', { name: /BẢN ĐỒ ĐIỂM NÓNG AN NINH/i }),
    ).toBeDefined();
    expect(screen.getByRole('link', { name: /Điểm nóng/i })).toBeDefined();
  });
});

describe('Danh sách sự cố', () => {
  beforeEach(() => {
    localStorage.setItem(TOKEN_STORAGE_KEY, 'mock-token-manager');
    localStorage.setItem(
      USER_STORAGE_KEY,
      JSON.stringify({
        id: 2,
        username: 'manager',
        fullName: 'Quản Lý Trần Văn B',
        role: 'MANAGER',
        cameraScope: [],
      }),
    );
  });

  it('hiển thị được bảng sự cố kèm phân trang', async () => {
    renderAt('/incidents');

    expect(await screen.findByRole('table')).toBeDefined();
    expect(
      screen.getByRole('navigation', { name: /Phân trang danh sách sự cố/i }),
    ).toBeDefined();
  });
});
