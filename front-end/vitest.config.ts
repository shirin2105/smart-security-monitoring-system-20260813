import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: false,
    // Smoke test chạy trên transport mock để không cần backend.
    env: { VITE_USE_MOCK: 'true' },
  },
});
