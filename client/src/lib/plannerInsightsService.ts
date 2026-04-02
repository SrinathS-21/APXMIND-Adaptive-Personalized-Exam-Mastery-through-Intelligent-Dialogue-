import apiClient from './api';
import { enqueueSyncOperation } from './syncService';

export interface PlannerTask {
  id: string;
  task_date: string;
  task_type: string;
  subject?: string | null;
  topic?: string | null;
  recommended_minutes: number;
  priority_score: number;
  status: 'pending' | 'completed' | 'skipped';
  completed_at?: string | null;
}

export interface DailyPlannerSnapshot {
  date: string;
  total: number;
  planned_minutes: number;
  completed_count: number;
  skipped_count: number;
  pending_count: number;
  day_adherence_percent: number;
  weekly_adherence_percent: number;
  tasks: PlannerTask[];
}

export interface TopicRisk {
  subject: string;
  topic: string;
  mastery_score: number;
  confidence: number;
  state_label: string;
  repeated_mistakes: number;
  days_since_last_assessed: number;
  risk_score: number;
}

export interface TopicMastery {
  subject: string;
  topic: string;
  mastery_score: number;
  confidence: number;
  state_label: string;
  last_assessed_at?: string | null;
}

export interface CalibrationSnapshot {
  sample_count: number;
  mean_confidence: number;
  accuracy_percent: number;
  confidence_accuracy_gap: number;
  confident_wrong_rate: number;
}

export interface WeeklySummary {
  retention_score: number;
  accuracy_percent: number;
  speed_qph: number;
  consistency_score: number;
  active_days: number;
  period_days: number;
}

export interface ExamReadinessSnapshot {
  snapshot_date: string;
  projected_score?: number | null;
  syllabus_coverage_percent?: number | null;
  accuracy_percent?: number | null;
  speed_qph?: number | null;
  consistency_score?: number | null;
  risk_band?: string | null;
}

export interface HabitSignal {
  date: string;
  session_count: number;
  deep_focus_minutes: number;
  interruptions_count: number;
  first_activity_at?: string | null;
  last_activity_at?: string | null;
}

export async function getDailyPlanner(date?: string) {
  const query = date ? `?date=${encodeURIComponent(date)}` : '';
  const response = await apiClient.get<DailyPlannerSnapshot>(`/api/planner/daily${query}`);
  return response.data;
}

export async function generateDailyPlanner(availableMinutes: number, date?: string) {
  const response = await apiClient.post('/api/planner/generate', {
    available_minutes: availableMinutes,
    date,
  });
  void enqueueSyncOperation({
    operationType: 'event',
    entityType: 'planner_generation',
    entityId: response.data?.date ?? date ?? null,
    payload: {
      available_minutes: availableMinutes,
      generated_count: Array.isArray(response.data?.tasks) ? response.data.tasks.length : 0,
      date: response.data?.date ?? date,
    },
  });
  return response.data as { tasks: PlannerTask[]; date: string };
}

export async function runStrategistPlanner(date?: string) {
  const response = await apiClient.post('/api/planner/strategist', { date });
  void enqueueSyncOperation({
    operationType: 'event',
    entityType: 'planner_strategist',
    entityId: response.data?.date ?? date ?? null,
    payload: {
      generated_count: Array.isArray(response.data?.tasks) ? response.data.tasks.length : 0,
      date: response.data?.date ?? date,
    },
  });
  return response.data as { tasks: PlannerTask[]; date: string };
}

export async function updatePlannerTask(taskId: string, status: 'pending' | 'completed' | 'skipped') {
  const response = await apiClient.patch(`/api/planner/tasks/${taskId}`, { status });
  void enqueueSyncOperation({
    operationType: 'update',
    entityType: 'planner_task',
    entityId: taskId,
    payload: {
      status,
      completed_at: response.data?.task?.completed_at ?? null,
      rescheduled_task_id: response.data?.rescheduled_task?.id ?? null,
    },
  });
  return response.data as { task: PlannerTask };
}

export async function getRiskTopics(limit = 5, subject?: string) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (subject) {
    params.set('subject', subject);
  }
  const response = await apiClient.get<{ risk_topics: TopicRisk[] }>(`/api/insights/risk-topics?${params.toString()}`);
  return response.data.risk_topics ?? [];
}

export async function getMastery(subject?: string) {
  const params = new URLSearchParams();
  if (subject) {
    params.set('subject', subject);
  }
  const query = params.toString();
  const response = await apiClient.get<{ mastery: TopicMastery[] }>(
    `/api/insights/mastery${query ? `?${query}` : ''}`
  );
  return response.data.mastery ?? [];
}

export async function getCalibration(days = 30) {
  const response = await apiClient.get<CalibrationSnapshot>(`/api/insights/calibration?days=${days}`);
  return response.data;
}

export async function getWeeklySummary(days = 7) {
  const response = await apiClient.get<{ summary: WeeklySummary }>(
    `/api/insights/weekly-report?days=${days}&export_format=json`
  );
  return response.data.summary;
}

export async function getReadiness(days = 30) {
  const response = await apiClient.get<{ latest: ExamReadinessSnapshot | null; history: ExamReadinessSnapshot[] }>(
    `/api/insights/readiness?days=${days}`
  );
  return response.data;
}

export async function getHabitSignals(days = 7) {
  const response = await apiClient.get<{ signals: HabitSignal[] }>(`/api/insights/habits?days=${days}`);
  return response.data.signals ?? [];
}
