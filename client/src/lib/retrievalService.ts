import apiClient from './api';
import { enqueueSyncOperation } from './syncService';

export type SpacedReviewResult = 'correct' | 'partial' | 'incorrect';

export interface SpacedReviewItem {
  id: string;
  topic: string;
  subject?: string | null;
  source_type: string;
  source_id: string;
  interval_step: number;
  due_at: string;
  last_result?: string | null;
  streak: number;
}

export interface LessonRecallPayload {
  lesson_id?: number;
  subject?: 'physics' | 'chemistry' | 'biology';
  topic: string;
  response_text: string;
  self_score: number;
  time_taken_sec?: number;
}

export interface LessonRecallResponse {
  score_band: string;
  next_review_due: string;
  spaced_review_id: string;
  gaps: string[];
}

export async function submitLessonRecall(payload: LessonRecallPayload) {
  const response = await apiClient.post<LessonRecallResponse>('/api/retrieval/lesson-recall', payload);
  void enqueueSyncOperation({
    operationType: 'create',
    entityType: 'spaced_review',
    entityId: response.data?.spaced_review_id ?? null,
    payload: {
      subject: payload.subject,
      topic: payload.topic,
      self_score: payload.self_score,
      score_band: response.data?.score_band,
      next_review_due: response.data?.next_review_due,
    },
  });
  return response.data;
}

export async function getSpacedQueue(limit = 10, dueBeforeIso?: string) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (dueBeforeIso) {
    params.set('due_before', dueBeforeIso);
  }
  const response = await apiClient.get<{ due_items: SpacedReviewItem[] }>(
    `/api/retrieval/spaced-queue?${params.toString()}`
  );
  return response.data.due_items ?? [];
}

export async function completeSpacedReview(
  reviewId: string,
  result: SpacedReviewResult,
  confidenceLevel?: number
) {
  const response = await apiClient.post(`/api/retrieval/spaced-queue/${reviewId}/complete`, {
    result,
    confidence_level: confidenceLevel,
  });
  void enqueueSyncOperation({
    operationType: 'update',
    entityType: 'spaced_review',
    entityId: reviewId,
    payload: {
      result,
      confidence_level: confidenceLevel,
      next_due_at: response.data?.next_due_at,
      interval_step: response.data?.interval_step,
      streak: response.data?.streak,
    },
  });
  return response.data as { next_due_at: string; interval_step: number; streak: number };
}
