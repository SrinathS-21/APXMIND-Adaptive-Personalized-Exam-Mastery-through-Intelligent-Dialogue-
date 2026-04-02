// Subject API Service
// Handles all subject and lesson related API calls

import apiClient, { API_ENDPOINTS, getApiErrorMessage } from './api';
import { enqueueSyncOperation } from './syncService';

export interface Subject {
  id: number;
  name: string;
  display_name: string;
  description: string;
  icon: string;
  color: string;
  total_lessons: number;
}

export interface Lesson {
  id: number;
  subject_id: number;
  subject_name?: string;
  title: string;
  description?: string;
  order: number;
  difficulty: 'easy' | 'medium' | 'hard';
  estimated_time: number;
  topics: string[];
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface CompleteLessonResponse {
  success: boolean;
  lesson_id?: number;
  xp_awarded?: number;
  message?: string;
}

// Get all subjects
export const getAllSubjects = async (): Promise<ApiResponse<Subject[]>> => {
  try {
    const response = await apiClient.get<ApiResponse<Subject[]>>(API_ENDPOINTS.subjects);
    return response.data;
  } catch (error: unknown) {
    console.error('Failed to fetch subjects:', error);
    return {
      success: false,
      error: getApiErrorMessage(error, 'Failed to fetch subjects'),
    };
  }
};

// Get lessons for a specific subject
export const getSubjectLessons = async (subject: string): Promise<ApiResponse<Lesson[]>> => {
  try {
    const response = await apiClient.get<{ success: boolean; lessons: Lesson[] }>(
      API_ENDPOINTS.subjectLessons(subject)
    );
    return {
      success: response.data.success,
      data: response.data.lessons,
    };
  } catch (error: unknown) {
    console.error(`Failed to fetch lessons for ${subject}:`, error);
    return {
      success: false,
      error: getApiErrorMessage(error, `Failed to fetch lessons for ${subject}`),
    };
  }
};

// Mark lesson completed for the current user
export const completeLesson = async (
  subject: string,
  lessonId: number
): Promise<ApiResponse<CompleteLessonResponse>> => {
  try {
    const response = await apiClient.post<CompleteLessonResponse>(
      `/api/subjects/${subject}/lessons/${lessonId}/complete`
    );
    void enqueueSyncOperation({
      operationType: 'event',
      entityType: 'lesson_completion',
      entityId: `${subject}:${lessonId}`,
      payload: {
        subject,
        lesson_id: lessonId,
        xp_awarded: response.data.xp_awarded,
      },
    });
    return {
      success: Boolean(response.data.success),
      data: response.data,
      message: response.data.message,
    };
  } catch (error: unknown) {
    console.error(`Failed to complete lesson ${lessonId} for ${subject}:`, error);
    return {
      success: false,
      error: getApiErrorMessage(error, 'Failed to complete lesson'),
    };
  }
};

// Subject Service Object
export const subjectService = {
  getAllSubjects,
  getSubjectLessons,
  completeLesson,
};
