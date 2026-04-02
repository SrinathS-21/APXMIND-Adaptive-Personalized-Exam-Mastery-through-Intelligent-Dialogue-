import apiClient from './api';
import { enqueueSyncOperation } from './syncService';

export type StudySubject = 'physics' | 'chemistry' | 'biology';

export interface DailyProgressDay {
    date: string;
    study_minutes: number;
    lessons_completed: number;
    quizzes_taken: number;
    xp_earned: number;
    subjects_studied: string[];
}

interface DailyProgressListResponse {
    success: boolean;
    days: DailyProgressDay[];
}

interface RecordStudyMinutesResponse {
    success: boolean;
    message?: string;
    minutes_recorded?: number;
    xp_awarded?: number;
}

export async function getDailyProgress(days = 7) {
    const response = await apiClient.get<DailyProgressListResponse>(`/api/progress/daily?days=${days}`);
    return response.data.days ?? [];
}

export async function recordStudyMinutes(subject: StudySubject, minutes: number, date?: string) {
    const payload: { subject: StudySubject; minutes: number; date?: string } = {
        subject,
        minutes,
    };
    if (date) {
        payload.date = date;
    }

    const response = await apiClient.post<RecordStudyMinutesResponse>('/api/progress/study-minutes', payload);
    void enqueueSyncOperation({
        operationType: 'event',
        entityType: 'study_minutes',
        entityId: date ?? new Date().toISOString().slice(0, 10),
        payload: {
            subject,
            minutes,
            date,
            xp_awarded: response.data?.xp_awarded,
        },
    });
    return response.data;
}
