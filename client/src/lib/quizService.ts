import apiClient from './api';
import { enqueueSyncOperation } from './syncService';

export type QuizDifficulty = 'easy' | 'medium' | 'hard' | 'mixed';

export interface QuizMeta {
    id: string;
    subject: string;
    topic?: string | null;
    difficulty: string;
    question_count: number;
    time_limit_sec?: number | null;
    status: string;
    started_at: string;
    completed_at?: string | null;
}

export interface QuizQuestion {
    id: number;
    question_no: number;
    question_text: string;
    options: string[];
    topic?: string | null;
    difficulty?: string | null;
}

export interface StartQuizResponse {
    quiz: QuizMeta;
    questions: QuizQuestion[];
}

interface QuizListResponse {
    success: boolean;
    quizzes: QuizMeta[];
    total: number;
}

export interface QuizListParams {
    subject?: 'physics' | 'chemistry' | 'biology';
    status?: 'active' | 'completed' | 'abandoned';
    difficulty?: QuizDifficulty;
    limit?: number;
    offset?: number;
}

export interface SubmitQuizAnswerResponse {
    result: {
        is_correct: boolean;
        correct_answer: string;
        explanation?: string | null;
        score_awarded: number;
    };
}

export interface QuizSummary {
    id: number;
    quiz_id: string;
    subject: string;
    difficulty: string;
    correct_answers: number;
    total_questions: number;
    score_percent: number;
    xp_awarded: number;
    time_taken_sec?: number | null;
    created_at: string;
}

export interface QuizResultQuestion {
    question_no: number;
    question_text: string;
    options: string[];
    correct_answer: string;
    user_answer?: string | null;
    is_correct?: boolean | null;
    explanation?: string | null;
}

export interface QuizResultsPayload {
    success: boolean;
    quiz: QuizMeta;
    questions: QuizResultQuestion[];
    summary?: QuizSummary | null;
}

export async function startQuiz(
    subject: 'physics' | 'chemistry' | 'biology',
    difficulty: QuizDifficulty,
    questionCount: number,
    topic?: string
) {
    const response = await apiClient.post<StartQuizResponse>('/api/quiz', {
        subject,
        difficulty,
        question_count: questionCount,
        topic,
    });
    return response.data;
}

export async function submitQuizAnswer(
    quizId: string,
    questionId: number,
    userAnswer: string,
    confidenceLevel?: number
) {
    const response = await apiClient.post<SubmitQuizAnswerResponse>(`/api/quiz/${quizId}/answers`, {
        question_id: questionId,
        user_answer: userAnswer,
        confidence_level: confidenceLevel,
    });
    return response.data;
}

export async function updateQuizAnswer(
    quizId: string,
    questionId: number,
    userAnswer: string,
    confidenceLevel?: number
) {
    const response = await apiClient.put<SubmitQuizAnswerResponse>(`/api/quiz/${quizId}/answers/${questionId}`, {
        user_answer: userAnswer,
        confidence_level: confidenceLevel,
    });
    return response.data;
}

export async function finishQuiz(quizId: string) {
    const response = await apiClient.post<{ summary: QuizSummary }>(`/api/quiz/${quizId}/finish`);
    void enqueueSyncOperation({
        operationType: 'event',
        entityType: 'quiz_completion',
        entityId: quizId,
        payload: {
            score_percent: response.data?.summary?.score_percent,
            correct_answers: response.data?.summary?.correct_answers,
            total_questions: response.data?.summary?.total_questions,
            xp_awarded: response.data?.summary?.xp_awarded,
        },
    });
    return response.data;
}

export async function abandonQuiz(quizId: string) {
    const response = await apiClient.patch<{ success: boolean; quiz_id: string; status: string }>(`/api/quiz/${quizId}/abandon`);
    return response.data;
}

export async function listQuizHistoryPaged(params?: QuizListParams) {
    const query = new URLSearchParams();
    if (params?.subject) {
        query.set('subject', params.subject);
    }
    if (params?.status) {
        query.set('status', params.status);
    }
    if (params?.difficulty) {
        query.set('difficulty', params.difficulty);
    }
    query.set('limit', String(params?.limit ?? 10));
    query.set('offset', String(params?.offset ?? 0));

    const response = await apiClient.get<QuizListResponse>(`/api/quiz?${query.toString()}`);
    return {
        quizzes: response.data.quizzes ?? [],
        total: response.data.total ?? 0,
    };
}

export async function listQuizHistory(params?: QuizListParams) {
    const response = await listQuizHistoryPaged(params);
    return response.quizzes;
}

export async function getQuiz(quizId: string) {
    const response = await apiClient.get<QuizMeta>(`/api/quiz/${quizId}`);
    return response.data;
}

export async function getQuizResults(quizId: string) {
    const response = await apiClient.get<QuizResultsPayload>(`/api/quiz/${quizId}/results`);
    return response.data;
}

export async function getQuizQuestions(quizId: string) {
    const response = await apiClient.get<QuizQuestion[]>(`/api/quiz/${quizId}/questions`);
    return response.data;
}

export async function deleteQuiz(quizId: string) {
    await apiClient.delete(`/api/quiz/${quizId}`);
}
