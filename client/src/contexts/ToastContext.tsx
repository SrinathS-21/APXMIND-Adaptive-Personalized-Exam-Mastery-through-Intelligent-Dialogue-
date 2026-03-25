import { useCallback, useMemo, useRef, useState } from 'react';
import { ActionToast } from '../components/ActionToast';
import { ToastContext, ToastItem, ToastType } from './toastStore';

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timersRef = useRef<Map<string, number>>(new Map());
  const recentToastRef = useRef<Map<string, number>>(new Map());

  const TOAST_DEDUPE_WINDOW_MS = 1500;

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((item) => item.id !== id));
    const timer = timersRef.current.get(id);
    if (timer) {
      window.clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const addToast = useCallback(
    (message: string, type: ToastType = 'info', durationMs = 2600) => {
      const normalizedMessage = message.trim();
      const dedupeKey = `${type}:${normalizedMessage}`;
      const now = Date.now();
      const lastShownAt = recentToastRef.current.get(dedupeKey) ?? 0;

      if (now - lastShownAt < TOAST_DEDUPE_WINDOW_MS) {
        return;
      }

      recentToastRef.current.set(dedupeKey, now);

      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      setToasts((prev) => [...prev, { id, message: normalizedMessage, type }]);

      const timer = window.setTimeout(() => {
        setToasts((prev) => prev.filter((item) => item.id !== id));
        timersRef.current.delete(id);
      }, durationMs);

      timersRef.current.set(id, timer);
    },
    []
  );

  const value = useMemo(() => ({ addToast, removeToast }), [addToast, removeToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ActionToast toasts={toasts} />
    </ToastContext.Provider>
  );
}
