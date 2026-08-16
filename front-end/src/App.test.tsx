/**
 * Smoke test cây component.
 *
 * Mục tiêu không phải phủ hết UI mà là bắt sớm những lỗi `tsc` không thấy:
 * sai thứ tự provider, dùng hook router ngoài <BrowserRouter>, import vòng,
 * hoặc route bảo vệ không chuyển hướng.
 */

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { App } from './App';
import { TOKEN_STORAGE_KEY, USER_STORAGE_KEY } from './api/config';

// Polyfill localStorage safe for Node/jsdom test runner if uninitialized
const createLocalStorageMock = () => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = String(value);
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    get length() {
      return Object.keys(store).length;
    },
    key: (index: number) => Object.keys(store)[index] ?? null,
  };
};

if (typeof window !== 'undefined') {
  try {
    if (!window.localStorage || typeof window.localStorage.clear !== 'function') {
      Object.defineProperty(window, 'localStorage', {
        value: createLocalStorageMock(),
        writable: true,
      });
    }
  } catch {
    // Fallback if property definition is restricted
  }
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  try {
    if (typeof localStorage !== 'undefined' && typeof localStorage.clear === 'function') {
      localStorage.clear();
    }
  } catch {
    // Ignore clear error
  }
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

  it('phát cảnh báo bỏ quên khi Camera 1 tới mốc Phase7C trong video demo', async () => {
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
    await screen.findByRole('region', { name: /Lưới camera giám sát/i });

    const video = document.querySelector<HTMLVideoElement>(
      'video[src="/videos/camera-1-aboda-tracking.h264.mp4"]',
    );
    expect(video).not.toBeNull();
    if (!video) return;

    video.currentTime = 13.8;
    fireEvent.timeUpdate(video);

    expect(await screen.findByText('Cảnh báo vật thể bỏ quên')).toBeDefined();
    expect(
      (await screen.findAllByText(/chủ sở hữu đã rời khỏi khu vực giám sát/i)).length,
    ).toBeGreaterThan(0);
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
    try {
      if (typeof localStorage !== 'undefined' && typeof localStorage.setItem === 'function') {
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
      }
    } catch {
      // Ignore storage error in test runner
    }
  });

  it('hiển thị được bảng sự cố kèm phân trang', async () => {
    renderAt('/incidents');

    expect(await screen.findByRole('table')).toBeDefined();
    expect(
      screen.getByRole('navigation', { name: /Phân trang danh sách sự cố/i }),
    ).toBeDefined();
  });
});
