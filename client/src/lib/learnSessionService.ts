import apiClient from './api';

export interface LearnSession {
  id: string;
  subject: string;
  lesson_id?: number | null;
  started_at: string;
  ended_at?: string | null;
  duration_minutes?: number | null;
}

export interface LearnMessage {
  id: number;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  tier?: string | null;
  created_at: string;
}

interface SessionListResponse {
  success: boolean;
  sessions: LearnSession[];
  total: number;
}

export type LearnSessionStatus = 'active' | 'completed';

export interface LearnSessionListParams {
  subject?: string;
  status?: LearnSessionStatus;
  limit?: number;
  offset?: number;
}

interface MessageListResponse {
  success: boolean;
  messages: LearnMessage[];
  total: number;
}

export async function startLearnSession(subject: string, lessonId?: number) {
  const response = await apiClient.post<LearnSession>('/api/learn/sessions', {
    subject,
    lesson_id: lessonId,
  });
  return response.data;
}

export async function sendLearnMessage(sessionId: string, content: string) {
  const response = await apiClient.post<LearnMessage>(`/api/learn/sessions/${sessionId}/messages`, {
    content,
  });
  return response.data;
}

export async function endLearnSession(sessionId: string) {
  const response = await apiClient.patch<LearnSession>(`/api/learn/sessions/${sessionId}/end`);
  return response.data;
}

export async function listLearnSessionsPaged(params?: LearnSessionListParams) {
  const query = new URLSearchParams({
    limit: String(params?.limit ?? 10),
    offset: String(params?.offset ?? 0),
  });
  if (params?.subject) {
    query.set('subject', params.subject);
  }
  if (params?.status) {
    query.set('status', params.status);
  }

  const response = await apiClient.get<SessionListResponse>(`/api/learn/sessions?${query.toString()}`);
  return {
    sessions: response.data.sessions ?? [],
    total: response.data.total ?? 0,
  };
}

export async function listLearnSessions(subject?: string, limit = 10) {
  const response = await listLearnSessionsPaged({ subject, limit });
  return response.sessions;
}

export async function getLearnSession(sessionId: string) {
  const response = await apiClient.get<LearnSession>(`/api/learn/sessions/${sessionId}`);
  return response.data;
}

export async function getLearnMessages(sessionId: string, limit = 60) {
  const response = await apiClient.get<MessageListResponse>(`/api/learn/sessions/${sessionId}/messages?limit=${limit}`);
  return response.data.messages ?? [];
}

export async function deleteLearnSession(sessionId: string) {
  await apiClient.delete(`/api/learn/sessions/${sessionId}`);
}

export async function deleteLearnMessage(sessionId: string, messageId: number) {
  await apiClient.delete(`/api/learn/sessions/${sessionId}/messages/${messageId}`);
}

export async function clearLearnMessages(sessionId: string) {
  await apiClient.delete(`/api/learn/sessions/${sessionId}/messages`);
}
