import apiClient from './api';
import { enqueueSyncOperation } from './syncService';

export interface MistakeCardItem {
  id: string;
  subject?: string | null;
  topic?: string | null;
  source_type?: string | null;
  source_id?: string | null;
  error_reason_code: string;
  prompt_snapshot: string;
  correct_explanation?: string | null;
  times_seen: number;
  times_repeated: number;
  last_seen_at: string;
  next_due_at?: string | null;
  status: 'active' | 'resolved';
  created_at: string;
  updated_at: string;
}

export async function getMistakeCards(status: 'active' | 'resolved' = 'active', limit = 10) {
  const params = new URLSearchParams({ status, limit: String(limit) });
  const response = await apiClient.get<{ cards: MistakeCardItem[] }>(
    `/api/errors/mistake-cards?${params.toString()}`
  );
  return response.data.cards ?? [];
}

export async function updateMistakeCardStatus(cardId: string, status: 'active' | 'resolved') {
  const response = await apiClient.patch<{ card: MistakeCardItem }>(`/api/errors/mistake-cards/${cardId}`, { status });
  void enqueueSyncOperation({
    operationType: 'update',
    entityType: 'mistake_card',
    entityId: cardId,
    payload: {
      status,
      times_seen: response.data?.card?.times_seen,
      times_repeated: response.data?.card?.times_repeated,
      next_due_at: response.data?.card?.next_due_at,
    },
  });
  return response.data.card;
}
