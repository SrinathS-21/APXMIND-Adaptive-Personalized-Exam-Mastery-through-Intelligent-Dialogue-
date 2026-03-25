// Subject API Service
// Handles all subject and lesson related API calls

import apiClient, { API_ENDPOINTS } from './api';

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

// Get all subjects
export const getAllSubjects = async (): Promise<ApiResponse<Subject[]>> => {
  try {
    const response = await apiClient.get<ApiResponse<Subject[]>>(API_ENDPOINTS.subjects);
    return response.data;
  } catch (error: any) {
    console.error('Failed to fetch subjects:', error);
    return {
      success: false,
      error: error.response?.data?.error || 'Failed to fetch subjects',
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
  } catch (error: any) {
    console.error(`Failed to fetch lessons for ${subject}:`, error);
    return {
      success: false,
      error: error.response?.data?.error || `Failed to fetch lessons for ${subject}`,
    };
  }
};

// Subject Service Object
export const subjectService = {
  getAllSubjects,
  getSubjectLessons,
};
