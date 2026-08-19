import React, { createContext, useCallback, useContext, useState } from 'react';
import { Toast } from '@astryxdesign/core/Toast';
import { VStack } from '@astryxdesign/core/Stack';
import { Text } from '@astryxdesign/core/Text';

export type ToastType = 'success' | 'warning' | 'error' | 'info';

export interface ToastItem {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface ToastContextType {
  toasts: ToastItem[];
  addToast: (toast: Omit<ToastItem, 'id'>) => void;
  removeToast: (id: string) => void;
  toast: {
    success: (title: string, message?: string) => void;
    warning: (title: string, message?: string) => void;
    error: (title: string, message?: string) => void;
    info: (title: string, message?: string) => void;
  };
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    ({ type, title, message, duration = 4000 }: Omit<ToastItem, 'id'>) => {
      const id = Math.random().toString(36).substring(2, 9);
      setToasts((prev) => [...prev.slice(-4), { id, type, title, message, duration }]);
    },
    [],
  );

  const toast = {
    success: useCallback(
      (title: string, message?: string) => addToast({ type: 'success', title, message }),
      [addToast],
    ),
    warning: useCallback(
      (title: string, message?: string) => addToast({ type: 'warning', title, message }),
      [addToast],
    ),
    error: useCallback(
      (title: string, message?: string) => addToast({ type: 'error', title, message }),
      [addToast],
    ),
    info: useCallback(
      (title: string, message?: string) => addToast({ type: 'info', title, message }),
      [addToast],
    ),
  };

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast, toast }}>
      {children}
      {toasts.length > 0 && (
        <div
          style={{
            position: 'fixed',
            bottom: 'var(--spacing-4)',
            right: 'var(--spacing-4)',
            zIndex: 9999,
            pointerEvents: 'none',
            maxWidth: 380,
            width: '100%',
          }}
        >
          <VStack gap={2}>
            {toasts.map((item) => (
              <div key={item.id} style={{ pointerEvents: 'auto', width: '100%' }}>
                <Toast
                  type={item.type === 'error' ? 'error' : 'info'}
                  isAutoHide={true}
                  autoHideDuration={item.duration ?? 4000}
                  onDismiss={() => removeToast(item.id)}
                  body={
                    <VStack gap={0.5}>
                      <Text type="label" weight="bold">
                        {item.title}
                      </Text>
                      {item.message && (
                        <Text type="supporting" size="xsm">
                          {item.message}
                        </Text>
                      )}
                    </VStack>
                  }
                />
              </div>
            ))}
          </VStack>
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToastContext() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToastContext must be used within a ToastProvider');
  }
  return context;
}
