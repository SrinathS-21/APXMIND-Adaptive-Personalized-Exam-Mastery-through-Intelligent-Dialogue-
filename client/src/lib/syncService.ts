import apiClient from './api';

export type SyncOperationType = 'create' | 'update' | 'delete' | 'event';

export interface SyncOperationInput {
  operationType: SyncOperationType;
  entityType: string;
  entityId?: string | null;
  payload?: Record<string, unknown>;
  idempotencyKey?: string;
}

interface SyncQueueItem {
  operation_type: SyncOperationType;
  entity_type: string;
  entity_id?: string | null;
  payload: Record<string, unknown>;
  idempotency_key: string;
  queued_at: string;
  attempts: number;
}

interface SyncBatchResultItem {
  idempotency_key: string;
  status: 'accepted' | 'duplicate' | 'failed';
  retryable?: boolean;
}

interface SyncBatchResponse {
  accepted_count: number;
  duplicate_count: number;
  failed_count: number;
  results: SyncBatchResultItem[];
}

export interface SyncFlushResult {
  sentCount: number;
  remainingCount: number;
  acceptedCount: number;
  duplicateCount: number;
  failedCount: number;
}

export interface SyncRuntimeState {
  queueSize: number;
  isFlushing: boolean;
  isOnline: boolean;
  lastFlushAt?: string;
  lastResult?: SyncFlushResult;
}

const STORAGE_KEY = 'APXMIND_sync_queue_v1';
const MAX_QUEUE_ITEMS = 1000;

let isInitialized = false;
let activeFlush: Promise<SyncFlushResult> | null = null;
const listeners = new Set<(state: SyncRuntimeState) => void>();

function isOnline(): boolean {
  return typeof navigator === 'undefined' ? true : navigator.onLine;
}

let runtimeState: SyncRuntimeState = {
  queueSize: 0,
  isFlushing: false,
  isOnline: isOnline(),
};

function emitState(overrides: Partial<SyncRuntimeState> = {}): void {
  runtimeState = {
    ...runtimeState,
    ...overrides,
    queueSize: getSyncQueueSize(),
    isOnline: isOnline(),
  };

  for (const listener of listeners) {
    listener(runtimeState);
  }
}

function canUseStorage(): boolean {
  return typeof window !== 'undefined' && typeof localStorage !== 'undefined';
}

function readQueue(): SyncQueueItem[] {
  if (!canUseStorage()) {
    return [];
  }

  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw) as SyncQueueItem[];
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((item) => typeof item?.idempotency_key === 'string' && item.idempotency_key.trim().length > 0);
  } catch {
    return [];
  }
}

function writeQueue(items: SyncQueueItem[]): void {
  if (!canUseStorage()) {
    return;
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

function generateIdempotencyKey(prefix: string): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}-${Date.now()}-${crypto.randomUUID()}`;
  }
  const random = Math.random().toString(36).slice(2, 12);
  return `${prefix}-${Date.now()}-${random}`;
}

function buildQueueItem(input: SyncOperationInput): SyncQueueItem {
  const prefix = input.entityType || 'event';
  return {
    operation_type: input.operationType,
    entity_type: input.entityType,
    entity_id: input.entityId ?? null,
    payload: input.payload ?? {},
    idempotency_key: input.idempotencyKey || generateIdempotencyKey(prefix),
    queued_at: new Date().toISOString(),
    attempts: 0,
  };
}

export function getSyncQueueSize(): number {
  return readQueue().length;
}

export function getSyncRuntimeState(): SyncRuntimeState {
  if (runtimeState.queueSize !== getSyncQueueSize()) {
    emitState();
  }
  return runtimeState;
}

export function subscribeSyncRuntimeState(
  listener: (state: SyncRuntimeState) => void
): () => void {
  listeners.add(listener);
  listener(getSyncRuntimeState());

  return () => {
    listeners.delete(listener);
  };
}

export async function enqueueSyncOperation(input: SyncOperationInput): Promise<void> {
  const queue = readQueue();
  queue.push(buildQueueItem(input));

  if (queue.length > MAX_QUEUE_ITEMS) {
    queue.splice(0, queue.length - MAX_QUEUE_ITEMS);
  }

  writeQueue(queue);
  emitState();

  if (typeof navigator !== 'undefined' && navigator.onLine) {
    await flushSyncQueue();
  }
}

export async function flushSyncQueue(maxBatch = 100): Promise<SyncFlushResult> {
  if (activeFlush) {
    return activeFlush;
  }

  emitState({ isFlushing: true });

  activeFlush = (async () => {
    const queue = readQueue();
    if (!queue.length) {
      return {
        sentCount: 0,
        remainingCount: 0,
        acceptedCount: 0,
        duplicateCount: 0,
        failedCount: 0,
      };
    }

    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      return {
        sentCount: 0,
        remainingCount: queue.length,
        acceptedCount: 0,
        duplicateCount: 0,
        failedCount: 0,
      };
    }

    const batch = queue.slice(0, Math.max(1, maxBatch));

    try {
      const response = await apiClient.post<SyncBatchResponse>('/api/sync/batch', {
        operations: batch.map((item) => ({
          operation_type: item.operation_type,
          entity_type: item.entity_type,
          entity_id: item.entity_id,
          payload: item.payload,
          idempotency_key: item.idempotency_key,
        })),
      });

      const byKey = new Map(response.data.results.map((result) => [result.idempotency_key, result]));

      const remaining = queue.filter((item) => {
        const result = byKey.get(item.idempotency_key);
        if (!result) {
          return true;
        }

        if (result.status === 'accepted' || result.status === 'duplicate') {
          return false;
        }

        if (result.status === 'failed' && result.retryable) {
          return true;
        }

        return false;
      });

      for (const item of remaining) {
        if (byKey.has(item.idempotency_key)) {
          item.attempts += 1;
        }
      }

      writeQueue(remaining);
      emitState();

      return {
        sentCount: batch.length,
        remainingCount: remaining.length,
        acceptedCount: response.data.accepted_count ?? 0,
        duplicateCount: response.data.duplicate_count ?? 0,
        failedCount: response.data.failed_count ?? 0,
      };
    } catch {
      return {
        sentCount: 0,
        remainingCount: queue.length,
        acceptedCount: 0,
        duplicateCount: 0,
        failedCount: 0,
      };
    }
  })();

  let result: SyncFlushResult | null = null;
  try {
    result = await activeFlush;
    return result;
  } finally {
    activeFlush = null;
    emitState({
      isFlushing: false,
      lastFlushAt: new Date().toISOString(),
      ...(result ? { lastResult: result } : {}),
    });
  }
}

export function initSyncAutoFlush(): void {
  if (isInitialized || typeof window === 'undefined') {
    return;
  }

  isInitialized = true;
  window.addEventListener('online', () => {
    emitState();
    void flushSyncQueue();
  });
  window.addEventListener('offline', () => {
    emitState();
  });

  emitState();
  void flushSyncQueue();
}
