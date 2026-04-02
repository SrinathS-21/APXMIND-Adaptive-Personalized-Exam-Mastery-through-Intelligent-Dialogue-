import apiClient from './api';

export type RecommendationStatus = 'active' | 'accepted' | 'dismissed' | 'completed';

export interface RecommendationItem {
  id: number;
  rec_type: string;
  subject?: string | null;
  topic?: string | null;
  title: string;
  reason: string;
  priority_score: number;
  status: RecommendationStatus;
  generated_at: string;
  expires_at?: string | null;
}

export async function getRecommendations(options?: {
  status?: RecommendationStatus;
  subject?: string;
  limit?: number;
}) {
  const params = new URLSearchParams();
  if (options?.status) {
    params.set('status', options.status);
  }
  if (options?.subject) {
    params.set('subject', options.subject);
  }
  if (typeof options?.limit === 'number') {
    params.set('limit', String(options.limit));
  }

  const query = params.toString();
  const response = await apiClient.get<{ recommendations: RecommendationItem[] }>(
    `/api/recommendations${query ? `?${query}` : ''}`
  );
  return response.data.recommendations ?? [];
}

export async function updateRecommendationStatus(
  recommendationId: number,
  status: Extract<RecommendationStatus, 'accepted' | 'dismissed' | 'completed'>
) {
  const response = await apiClient.patch<RecommendationItem>(`/api/recommendations/${recommendationId}`, {
    status,
  });
  return response.data;
}

export async function deleteRecommendation(recommendationId: number) {
  await apiClient.delete(`/api/recommendations/${recommendationId}`);
}
