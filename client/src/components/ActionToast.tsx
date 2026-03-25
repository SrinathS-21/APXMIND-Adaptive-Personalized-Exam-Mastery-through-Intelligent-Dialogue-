import { AnimatePresence, motion } from 'framer-motion';
import { AlertCircle, CheckCircle2, Info } from 'lucide-react';

type ToastType = 'success' | 'error' | 'info';

interface ToastItem {
  id: string;
  message: string;
  type: ToastType;
}

interface ActionToastProps {
  toasts: ToastItem[];
}

const typeStyles: Record<ToastType, { icon: JSX.Element; border: string; color: string; bg: string }> = {
  success: {
    icon: <CheckCircle2 className="w-4 h-4" />,
    border: '1px solid var(--green-border)',
    color: 'var(--green)',
    bg: 'var(--green-soft)',
  },
  error: {
    icon: <AlertCircle className="w-4 h-4" />,
    border: '1px solid var(--red-border)',
    color: 'var(--red)',
    bg: 'var(--red-soft)',
  },
  info: {
    icon: <Info className="w-4 h-4" />,
    border: '1px solid var(--accent-border)',
    color: 'var(--accent)',
    bg: 'var(--accent-soft)',
  },
};

export function ActionToast({ toasts }: ActionToastProps) {
  return (
    <div className="fixed top-4 right-4 z-80 pointer-events-none flex flex-col gap-2 max-w-sm w-[calc(100%-2rem)] md:w-90">
      <AnimatePresence>
        {toasts.map((toast) => {
          const style = typeStyles[toast.type];
          return (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: -8, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.98 }}
              transition={{ duration: 0.18 }}
              className="glass"
              style={{
                border: style.border,
                background: style.bg,
                borderRadius: 'var(--r-md)',
                padding: '10px 12px',
              }}
            >
              <div className="flex items-start gap-2" style={{ color: style.color }}>
                <div className="mt-0.5 shrink-0">{style.icon}</div>
                <p style={{ fontSize: 12, lineHeight: 1.35 }}>{toast.message}</p>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
