// Trainer API Service
// Handles quiz generation and answer evaluation

import apiClient, { API_ENDPOINTS, getApiErrorMessage } from './api';

export type QuizDifficulty = 'easy' | 'medium' | 'hard';

export interface QuizQuestion {
  id: number;
  question: string;
  options: string[];
  correct_answer: string;
  explanation?: string;
  difficulty: QuizDifficulty;
  topic: string;
}

export interface QuizData {
  quiz_id: string;
  subject: string;
  difficulty: QuizDifficulty;
  questions: QuizQuestion[];
  total_questions: number;
  time_limit: number;
}

export interface GenerateQuizRequest {
  subject: string;
  difficulty?: QuizDifficulty;
  question_count?: number;
  topics?: string[];
}

export interface GenerateQuizResponse {
  success: boolean;
  quiz: QuizData;
  metadata?: {
    generation_time_ms: number;
  };
  error?: string;
}

export interface SubmitAnswerRequest {
  quiz_id: string;
  question_id: number;
  user_answer: string;
  options?: string[];
  correct_answer: string;
  question_text?: string;
}

export interface SubmitAnswerResponse {
  success: boolean;
  correct: boolean;
  explanation: string;
  correct_answer?: string;
  error?: string;
}

interface SubmitAnswerBackendResponse {
  success: boolean;
  evaluation?: {
    correct?: boolean;
    explanation?: string;
    correct_answer?: string;
  };
}

// Generate quiz for a subject
export const generateQuiz = async (
  subject: string,
  difficulty: QuizDifficulty = 'medium',
  questionCount: number = 5,
  topics?: string[]
): Promise<GenerateQuizResponse> => {
  try {
    const requestData: GenerateQuizRequest = {
      subject,
      difficulty,
      question_count: questionCount,
      topics,
    };

    const response = await apiClient.post<GenerateQuizResponse>(
      API_ENDPOINTS.generateQuiz,
      requestData
    );

    return response.data;
  } catch (error: unknown) {
    console.error('Failed to generate quiz:', error);
    return {
      success: false,
      quiz: {
        quiz_id: '',
        subject: '',
        difficulty: 'medium',
        questions: [],
        total_questions: 0,
        time_limit: 0,
      },
      error: getApiErrorMessage(error, 'Quiz generation failed'),
    };
  }
};

// Submit answer for evaluation
export const submitAnswer = async (
  quizId: string,
  questionId: number,
  userAnswer: string,
  correctAnswer: string,
  questionText?: string,
  options?: string[]
): Promise<SubmitAnswerResponse> => {
  try {
    const requestData: SubmitAnswerRequest = {
      quiz_id: quizId,
      question_id: questionId,
      user_answer: userAnswer,
      options,
      correct_answer: correctAnswer,
      question_text: questionText,
    };

    const response = await apiClient.post<SubmitAnswerBackendResponse>(
      API_ENDPOINTS.submitAnswer,
      requestData
    );

    // Backend returns { success, evaluation: { correct, correct_answer, explanation } }
    const rd = response.data;
    const evaluation = rd.evaluation || {};
    return {
      success: rd.success,
      correct: evaluation.correct ?? false,
      explanation: evaluation.explanation || '',
      correct_answer: evaluation.correct_answer || '',
    };
  } catch (error: unknown) {
    console.error('Failed to submit answer:', error);
    return {
      success: false,
      correct: false,
      explanation: 'Failed to evaluate answer. Please try again.',
      error: getApiErrorMessage(error, 'Answer submission failed'),
    };
  }
};

// Trainer Service Object
export const trainerService = {
  generateQuiz,
  submitAnswer,
};
