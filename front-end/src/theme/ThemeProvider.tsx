import React, { createContext, useContext, useEffect, useState } from 'react';
import { Theme as AstryxTheme } from '@astryxdesign/core/theme';
import { neutralTheme } from '../themes/neutral/neutralTheme';

export type ThemeMode = 'light' | 'dark' | 'system';

interface ThemeContextType {
  theme: ThemeMode;
  setTheme: (theme: ThemeMode) => void;
  actualTheme: 'light' | 'dark';
}

const THEME_STORAGE_KEY = 'vinai_theme_preference';

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>(() => {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const saved = window.localStorage.getItem(THEME_STORAGE_KEY) as ThemeMode;
        if (saved && ['light', 'dark', 'system'].includes(saved)) {
          return saved;
        }
      }
    } catch {
      // Ignore storage errors in restricted contexts
    }
    return 'dark'; // Security/surveillance vibe defaults to dark
  });

  const [actualTheme, setActualTheme] = useState<'light' | 'dark'>('dark');

  const setTheme = (newTheme: ThemeMode) => {
    setThemeState(newTheme);
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem(THEME_STORAGE_KEY, newTheme);
      }
    } catch {
      // Ignore storage errors
    }
  };

  useEffect(() => {
    const resolveTheme = (t: ThemeMode): 'light' | 'dark' => {
      if (t === 'system') {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }
      return t;
    };

    const computed = resolveTheme(theme);
    setActualTheme(computed);

    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = () => {
        setActualTheme(mediaQuery.matches ? 'dark' : 'light');
      };
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, actualTheme }}>
      <AstryxTheme theme={neutralTheme} mode={theme}>
        {children}
      </AstryxTheme>
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextType {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
