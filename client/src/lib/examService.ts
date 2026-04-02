import apiClient from './api';
import { enqueueSyncOperation } from './syncService';

export type StaminaMode = 'mixed' | 'subject';
export type StaminaErrorReason = 'formula_error' | 'concept_confusion' | 'misread' | 'time_pressure' | 'other';

export interface StaminaBlockPlan {
  block_no: number;
  planned_minutes: number;
  planned_questions: number;
}

export interface StartStaminaSessionResponse {
  session_id: string;
  mode: StaminaMode;
  subject?: string | null;
  topic?: string | null;
  duration_minutes: number;
  planned_questions: number;
  started_at: string;
  block_plan: StaminaBlockPlan[];
}

export interface FinishStaminaBlockResult {
  block_no: number;
  attempted_questions: number;
  correct_answers: number;
  elapsed_sec: number;
  dominant_error?: StaminaErrorReason;
}

export interface FinishStaminaSessionResponse {
  session_id: string;
  completed_at: string;
  total_questions: number;
  correct_answers: number;
  score_percent: number;
  pacing_qph: number;
  fatigue_accuracy_dip: number;
  fatigue_detected: boolean;
  error_clusters: Record<string, number>;
  xp_awarded: number;
}

export async function startStaminaSession(params: {
  mode: StaminaMode;
  subject?: 'physics' | 'chemistry' | 'biology';
  topic?: string;
  durationMinutes: number;
  plannedQuestions: number;
  blockCount: number;
}) {
  const response = await apiClient.post<StartStaminaSessionResponse>('/api/exam/stamina/sessions', {
    mode: params.mode,
    subject: params.subject,
    topic: params.topic,
    duration_minutes: params.durationMinutes,
    planned_questions: params.plannedQuestions,
    block_count: params.blockCount,
  });
  return response.data;
}

export async function finishStaminaSession(
  sessionId: string,
  params: {
    blockResults: FinishStaminaBlockResult[];
    notes?: string;
  }
) {
  const response = await apiClient.post<FinishStaminaSessionResponse>(`/api/exam/stamina/sessions/${sessionId}/finish`, {
    block_results: params.blockResults,
    notes: params.notes,
  });
  void enqueueSyncOperation({
    operationType: 'event',
    entityType: 'stamina_completion',
    entityId: sessionId,
    payload: {
      total_questions: response.data?.total_questions,
      correct_answers: response.data?.correct_answers,
      score_percent: response.data?.score_percent,
      pacing_qph: response.data?.pacing_qph,
      fatigue_accuracy_dip: response.data?.fatigue_accuracy_dip,
      fatigue_detected: response.data?.fatigue_detected,
      xp_awarded: response.data?.xp_awarded,
    },
  });
  return response.data;
}
