// Query API Service
// Handles intelligent query processing with LangGraph routing

import apiClient, { API_ENDPOINTS, getApiErrorMessage } from './api';

export interface QueryRequest {
  query: string;
  subject?: string;
  user_id?: number;
  context?: Record<string, unknown>;
}

export interface QueryResponse {
  success: boolean;
  answer: string;
  metadata?: {
    tier: 'tier-0' | 'tier-1' | 'tier-2' | 'langgraph';
    intent: string;
    subject: string;
    confidence: number;
    sources?: Array<{
      content: string;
      page?: number;
      title?: string;
    }>;
    tier0_latency_ms?: number;
    tier1_latency_ms?: number;
    tier2_latency_ms?: number;
    total_latency_ms: number;
  };
  error?: string;
}

// Process user query with intelligent routing
export const processQuery = async (
  query: string,
  subject?: string,
  userId?: number
): Promise<QueryResponse> => {
  try {
    const requestData: QueryRequest = {
      query,
      subject,
      user_id: userId,
      context: {},
    };

    const response = await apiClient.post<QueryResponse>(
      API_ENDPOINTS.query,
      requestData
    );

    return response.data;
  } catch (error: unknown) {
    console.error('Failed to process query:', error);
    return {
      success: false,
      answer: 'Failed to process your question. Please try again.',
      error: getApiErrorMessage(error, 'Query processing failed'),
    };
  }
};

// Query Service Object
export const queryService = {
  processQuery,
};
