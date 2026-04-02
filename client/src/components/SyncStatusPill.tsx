import { useEffect, useMemo, useRef, useState } from 'react';
import { Chip } from '@heroui/react';
import { CheckCircle2, CloudOff, Clock3, RefreshCw } from 'lucide-react';
import {
  getSyncRuntimeState,
  subscribeSyncRuntimeState,
  type SyncRuntimeState,
} from '../lib/syncService';

function formatLastFlush(iso?: string): string {
  if (!iso) {
    return 'Never';
  }

  const value = new Date(iso);
  if (Number.isNaN(value.getTime())) {
    return 'Unknown';
  }

  return value.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  });
}

function statusText(state: SyncRuntimeState): string {
  if (!state.isOnline) {
    return state.queueSize > 0 ? `Offline • ${state.queueSize} queued` : 'Offline';
  }
  if (state.isFlushing) {
    return state.queueSize > 0 ? `Syncing • ${state.queueSize} queued` : 'Syncing';
  }
  if (state.queueSize > 0) {
    return `${state.queueSize} queued`;
  }
  if (state.lastResult && state.lastResult.sentCount > 0) {
    return 'Synced';
  }
  return 'Sync idle';
}

export function SyncStatusPill() {
  const [state, setState] = useState<SyncRuntimeState>(() => getSyncRuntimeState());
  const [isOpen, setIsOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    return subscribeSyncRuntimeState(setState);
  }, []);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handlePointerDown(event: MouseEvent) {
      const root = rootRef.current;
      if (!root || root.contains(event.target as Node)) {
        return;
      }
      setIsOpen(false);
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen]);

  const isWarning = !state.isOnline || state.queueSize > 0;
  const isSyncing = state.isFlushing;
  const lastFlushLabel = useMemo(() => formatLastFlush(state.lastFlushAt), [state.lastFlushAt]);

  const acceptedCount = state.lastResult?.acceptedCount ?? 0;
  const duplicateCount = state.lastResult?.duplicateCount ?? 0;
  const failedCount = state.lastResult?.failedCount ?? 0;
  const sentCount = state.lastResult?.sentCount ?? 0;

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setIsOpen((value) => !value)}
        className="cursor-pointer bg-transparent border-0 p-0"
        aria-expanded={isOpen}
        aria-label="Toggle sync diagnostics"
      >
        <Chip
          size="sm"
          variant="flat"
          startContent={
            !state.isOnline ? (
              <CloudOff className="w-3 h-3" />
            ) : isSyncing ? (
              <RefreshCw className="w-3 h-3 animate-spin" />
            ) : state.queueSize > 0 ? (
              <Clock3 className="w-3 h-3" />
            ) : (
              <CheckCircle2 className="w-3 h-3" />
            )
          }
          style={{
            borderRadius: 'var(--r-pill)',
            fontSize: 11,
            fontWeight: 600,
            height: 24,
            border: `1px solid ${isWarning ? 'var(--amber-border)' : 'var(--green-border)'}`,
            background: isWarning ? 'var(--amber-soft)' : 'var(--green-soft)',
            color: isWarning ? 'var(--amber)' : 'var(--green)',
          }}
        >
          {statusText(state)}
        </Chip>
      </button>

      {isOpen ? (
        <div
          className="absolute right-0 mt-2 w-60 rounded-lg p-2.5"
          style={{
            background: 'var(--bg-2)',
            border: '1px solid var(--border-default)',
            boxShadow: '0 14px 30px rgba(0, 0, 0, 0.16)',
            zIndex: 60,
          }}
        >
          <p className="text-xs font-semibold" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-heading)' }}>
            Sync diagnostics
          </p>
          <div className="mt-2 space-y-1.5 text-[11px]">
            <div className="flex items-center justify-between">
              <span style={{ color: 'var(--text-muted)' }}>Queued payloads</span>
              <span style={{ color: 'var(--text-primary)' }}>{state.queueSize}</span>
            </div>
            <div className="flex items-center justify-between">
              <span style={{ color: 'var(--text-muted)' }}>Last flush</span>
              <span style={{ color: 'var(--text-primary)' }}>{lastFlushLabel}</span>
            </div>
            <div className="flex items-center justify-between">
              <span style={{ color: 'var(--text-muted)' }}>Accepted</span>
              <span style={{ color: 'var(--green)' }}>{acceptedCount}</span>
            </div>
            <div className="flex items-center justify-between">
              <span style={{ color: 'var(--text-muted)' }}>Duplicate</span>
              <span style={{ color: 'var(--amber)' }}>{duplicateCount}</span>
            </div>
            <div className="flex items-center justify-between">
              <span style={{ color: 'var(--text-muted)' }}>Failed</span>
              <span style={{ color: failedCount > 0 ? 'var(--red)' : 'var(--text-primary)' }}>{failedCount}</span>
            </div>
            <div className="flex items-center justify-between">
              <span style={{ color: 'var(--text-muted)' }}>Last sent batch</span>
              <span style={{ color: 'var(--text-primary)' }}>{sentCount}</span>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
