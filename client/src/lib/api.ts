// APXMIND API Client Configuration
// In production: same origin (FastAPI serves the SPA)
// In dev: Vite proxy forwards /api/* → http://localhost:8000
import axios from 'axios';

// Create axios instance with default config — no baseURL needed (relative URLs)
const apiClient = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds (LLM calls can be slow)
});

// Request interceptor - attach auth token + log in dev
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('APXMIND_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    if (import.meta.env.DEV) {
      console.log('🚀 API Request:', config.method?.toUpperCase(), config.url);
    }
    return config;
  },
  (error) => {
    console.error('❌ Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor - handle errors globally
apiClient.interceptors.response.use(
  (response) => {
    if (import.meta.env.DEV) {
      console.log('✅ API Response:', response.status, response.config.url);
    }
    return response;
  },
  (error) => {
    console.error('❌ API Error:', error.response?.status, error.message);

    // Handle specific error cases
    if (error.response) {
      const { status, data } = error.response;

      switch (status) {
        case 401:
          // Token expired or invalid — clear stored data
          localStorage.removeItem('APXMIND_token');
          localStorage.removeItem('APXMIND_user');
          break;
        case 400:
          console.error('Bad Request:', data.error || 'Invalid request');
          break;
        case 404:
          console.error('Not Found:', data.error || 'Resource not found');
          break;
        case 500:
          console.error('Server Error:', data.error || 'Internal server error');
          break;
        default:
          console.error('Error:', data.error || 'An error occurred');
      }
    } else if (error.request) {
      console.error('No response from server. Check if APXMIND API is running.');
    }

    return Promise.reject(error);
  }
);

export default apiClient;

export const getApiErrorMessage = (error: unknown, fallback = 'Something went wrong. Please try again.') => {
  if (axios.isAxiosError(error)) {
    const responseData = error.response?.data as
      | { detail?: string; error?: string; message?: string }
      | undefined;

    const message =
      responseData?.detail ||
      responseData?.error ||
      responseData?.message;

    if (typeof message === 'string' && message.trim()) {
      return message;
    }

    if (error.code === 'ECONNABORTED') {
      return 'Request timed out. Please try again.';
    }

    if (!error.response) {
      return 'Unable to reach server. Check your internet connection.';
    }

    switch (error.response.status) {
      case 400:
        return 'Invalid request. Please check your input and try again.';
      case 401:
        return 'Session expired. Please sign in again.';
      case 403:
        return 'You do not have permission for this action.';
      case 404:
        return 'Requested resource was not found.';
      case 409:
        return 'Conflict detected. Please refresh and try again.';
      case 422:
        return 'Some input values are invalid.';
      case 429:
        return 'Too many requests. Please wait and retry.';
      case 500:
      case 502:
      case 503:
      case 504:
        return 'Server is temporarily unavailable. Please try again shortly.';
      default:
        return fallback;
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return fallback;
};

// API Health Check
export const checkApiHealth = async (): Promise<boolean> => {
  try {
    const response = await apiClient.get('/health');
    return response.data.status === 'healthy';
  } catch (error) {
    console.error('API Health Check Failed:', error);
    return false;
  }
};

// API Endpoints
export const API_ENDPOINTS = {
  health: '/health',
  subjects: '/api/subjects',
  subjectLessons: (subject: string) => `/api/subjects/${subject}/lessons`,
  query: '/api/query',
  bookTutor: '/api/books/tutor',
  generateQuiz: '/api/trainer/generate-quiz',
  submitAnswer: '/api/trainer/submit-answer',
  // Auth
  register: '/api/auth/register',
  login: '/api/auth/login',
  me: '/api/auth/me',
  updateProfile: '/api/auth/profile',
  users: '/api/auth/users',
} as const;
