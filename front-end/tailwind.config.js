/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        security: {
          light: '#F8FAFC',
          lightPanel: '#FFFFFF',
          lightCard: '#F1F5F9',
          lightBorder: '#E2E8F0',
          dark: '#0B0F19',
          panel: '#111827',
          card: '#1F2937',
          border: '#374151',
          accent: '#3B82F6',
          accentHover: '#2563EB',
          danger: '#EF4444',
          warning: '#F59E0B',
          success: '#10B981',
          violet: '#8B5CF6',
          neon: '#00FFCC'
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      }
    },
  },
  plugins: [],
}
