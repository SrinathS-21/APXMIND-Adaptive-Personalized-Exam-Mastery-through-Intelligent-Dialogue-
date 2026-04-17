import apiClient from './api';

export type TutorMode = 'guided' | 'revision' | 'drill';
export type NotebookUploadMode = 'quick' | 'full';

export interface LearnSourceCitation {
  source_id: string;
  title: string;
  page?: number | null;
  subject?: string | null;
  snippet?: string | null;
  source?: string | null;
}

export interface LearnMessageMetadata {
  latency_ms?: number;
  mode?: TutorMode;
  source_locked?: boolean;
  retrieval_method?: string;
  output_language?: string;
  uploaded_sources_enabled?: boolean;
  upload_mode?: NotebookUploadMode | null;
  citations?: LearnSourceCitation[];
  [key: string]: unknown;
}

export interface LearnNotebookSource {
  source_id: string;
  file_name: string;
  file_size_bytes: number;
  page_count: number;
  text_characters: number;
  index_mode: NotebookUploadMode;
  indexed: boolean;
  chunk_count: number;
  uploaded_at: string;
}

export interface LearnNotebookUploadResult extends LearnNotebookSource {
  session_id: string;
  upload_summary_markdown?: string | null;
}

interface LearnNotebookSourceListResponse {
  success: boolean;
  session_id: string;
  sources: LearnNotebookSource[];
}

export interface LessonMissionContext {
  lesson_id: number;
  subject: string;
  subject_display_name: string;
  lesson_title: string;
  lesson_description?: string | null;
  difficulty: string;
  estimated_minutes: number;
  focus_topics: string[];
  mission_title: string;
  mission_objectives: string[];
  starter_prompts: Record<string, string>;
  is_completed: boolean;
}

export interface LearnSession {
  id: string;
  subject: string;
  lesson_id?: number | null;
  started_at: string;
  ended_at?: string | null;
  duration_minutes?: number | null;
}

export interface LearnSessionModeState {
  session_id: string;
  mode: TutorMode;
  updated_at: string;
}

export interface LearnSessionSourceLockState {
  session_id: string;
  enabled: boolean;
  updated_at: string;
}

export interface GenerateChapterBriefRequest {
  language?: string;
  source_locked?: boolean;
}

export interface LearnChapterBrief {
  session_id: string;
  language: string;
  markdown: string;
  citations: LearnSourceCitation[];
  generated_at: string;
}

export interface ConvertSessionToNotesRequest {
  language?: string;
  title?: string;
}

export interface LearnSessionNotes {
  session_id: string;
  note_id: string;
  title: string;
  language: string;
  markdown: string;
  created_at: string;
}

export interface GenerateRevisionSheetRequest {
  language?: string;
}

export interface LearnRevisionSheetItem {
  concept_key: string;
  score_percent: number;
  confidence?: number | null;
  priority: 'high' | 'medium' | 'low' | string;
}

export interface LearnRevisionSheet {
  session_id: string;
  language: string;
  markdown: string;
  items: LearnRevisionSheetItem[];
  generated_at: string;
}

export interface LearnSessionSummary {
  session_id: string;
  mode: TutorMode | string;
  source_locked: boolean;
  message_count: number;
  checkpoint_count: number;
  avg_checkpoint_score?: number | null;
  latest_checkpoint_score?: number | null;
  latest_checkpoint_feedback?: string | null;
  supported_output_languages: string[];
  updated_at: string;
}

export interface LearnCheckpointRequest {
  concept_key: string;
  prompt: string;
  response_text: string;
  confidence?: number;
}

export interface LearnCheckpointResult {
  session_id: string;
  concept_key: string;
  score_percent: number;
  feedback: string;
  created_at: string;
}

export interface LearnMessage {
  id: number;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  tier?: string | null;
  msg_metadata?: LearnMessageMetadata | null;
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

export async function sendLearnMessage(
  sessionId: string,
  content: string,
  language?: string,
  mode?: TutorMode,
  sourceLocked?: boolean,
  useUploadedSources?: boolean,
  uploadMode?: NotebookUploadMode
) {
  const response = await apiClient.post<LearnMessage>(`/api/learn/sessions/${sessionId}/messages`, {
    content,
    language,
    mode,
    source_locked: sourceLocked,
    use_uploaded_sources: Boolean(useUploadedSources),
    upload_mode: uploadMode,
  });
  return response.data;
}

export async function uploadLearnNotebookSource(
  sessionId: string,
  file: File,
  uploadMode: NotebookUploadMode = 'quick',
  language?: string
) {
  const formData = new FormData();
  formData.append('index_mode', uploadMode);
  if (language) {
    formData.append('language', language);
  }
  formData.append('file', file);

  const response = await apiClient.post<LearnNotebookUploadResult>(
    `/api/learn/sessions/${sessionId}/notebook/sources`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 180000,
    }
  );

  return response.data;
}

export async function listLearnNotebookSources(sessionId: string) {
  const response = await apiClient.get<LearnNotebookSourceListResponse>(`/api/learn/sessions/${sessionId}/notebook/sources`);
  return response.data.sources ?? [];
}

export async function deleteLearnNotebookSource(sessionId: string, sourceId: string) {
  await apiClient.delete(`/api/learn/sessions/${sessionId}/notebook/sources/${sourceId}`);
}

export async function getLessonMissionContext(lessonId: number) {
  const response = await apiClient.get<LessonMissionContext>(`/api/learn/lessons/${lessonId}/context`);
  return response.data;
}

export async function setLearnSessionMode(sessionId: string, mode: TutorMode) {
  const response = await apiClient.post<LearnSessionModeState>(`/api/learn/sessions/${sessionId}/mode`, {
    mode,
  });
  return response.data;
}

export async function getLearnSessionMode(sessionId: string) {
  const response = await apiClient.get<LearnSessionModeState>(`/api/learn/sessions/${sessionId}/mode`);
  return response.data;
}

export async function setLearnSessionSourceLock(sessionId: string, enabled: boolean) {
  const response = await apiClient.post<LearnSessionSourceLockState>(`/api/learn/sessions/${sessionId}/source-lock`, {
    enabled,
  });
  return response.data;
}

export async function getLearnSessionSourceLock(sessionId: string) {
  const response = await apiClient.get<LearnSessionSourceLockState>(`/api/learn/sessions/${sessionId}/source-lock`);
  return response.data;
}

export async function submitLearnCheckpoint(sessionId: string, payload: LearnCheckpointRequest) {
  const response = await apiClient.post<LearnCheckpointResult>(`/api/learn/sessions/${sessionId}/checkpoint`, payload);
  return response.data;
}

export async function generateLearnChapterBrief(sessionId: string, payload?: GenerateChapterBriefRequest) {
  const response = await apiClient.post<LearnChapterBrief>(`/api/learn/sessions/${sessionId}/chapter-brief`, payload ?? {});
  return response.data;
}

export async function convertLearnSessionToNotes(sessionId: string, payload?: ConvertSessionToNotesRequest) {
  const response = await apiClient.post<LearnSessionNotes>(`/api/learn/sessions/${sessionId}/notes`, payload ?? {});
  return response.data;
}

export async function generateLearnRevisionSheet(sessionId: string, payload?: GenerateRevisionSheetRequest) {
  const response = await apiClient.post<LearnRevisionSheet>(`/api/learn/sessions/${sessionId}/revision-sheet`, payload ?? {});
  return response.data;
}

export async function getLearnSessionSummary(sessionId: string) {
  const response = await apiClient.get<LearnSessionSummary>(`/api/learn/sessions/${sessionId}/summary`);
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
