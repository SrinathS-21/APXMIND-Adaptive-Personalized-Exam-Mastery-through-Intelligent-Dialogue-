import apiClient, { getApiErrorMessage } from './api';

export type TutorTaskMode =
  | 'summary'
  | 'detailed_explain'
  | 'examples'
  | 'key_points'
  | 'questions'
  | 'follow_up';

export interface TutorChatTurn {
  role: 'user' | 'assistant';
  content: string;
  task?: TutorTaskMode;
}

export interface BookTutorRequest {
  context: string;
  task: TutorTaskMode;
  page_number?: number;
  chat_history?: TutorChatTurn[];
  user_query?: string;
  source_type?: 'selected_text' | 'ocr' | 'manual' | 'prior_response';
}

export interface BookTutorResponse {
  success: boolean;
  mode: TutorTaskMode;
  response: string;
  topic: string;
  caution?: string | null;
  timestamp: string;
}

export async function askBookTutor(payload: BookTutorRequest): Promise<BookTutorResponse> {
  try {
    const response = await apiClient.post<BookTutorResponse>('/api/books/tutor', payload);
    return response.data;
  } catch (error: unknown) {
    throw new Error(getApiErrorMessage(error, 'Unable to get tutor response right now.'));
  }
}
