import apiClient from './api';

export interface SupportTicketItem {
  id: number;
  ticket_number: string;
  subject: string;
  description: string;
  category: string;
  subcategory?: string | null;
  priority: string;
  status: string;
  assigned_to?: number | null;
  resolution_summary?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  closed_at?: string | null;
}

export interface SupportTicketResponse {
  id: number;
  responder_type: string;
  responder_id?: number | null;
  responder_name?: string | null;
  message: string;
  is_internal: boolean;
  attachments?: string[] | null;
  is_automated: boolean;
  created_at?: string | null;
}

export interface SupportTicketDetail extends SupportTicketItem {
  resolution_type?: string | null;
  responses: SupportTicketResponse[];
}

export async function listSupportTickets(status?: string, limit = 20) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (status) {
    params.set('status', status);
  }
  const response = await apiClient.get<{ tickets: SupportTicketItem[] }>(`/api/support/tickets?${params.toString()}`);
  return response.data.tickets ?? [];
}

export async function createSupportTicket(payload: {
  subject: string;
  description: string;
  category?: string;
  subcategory?: string;
  priority?: string;
  attachments?: string[];
}) {
  const response = await apiClient.post<{ ticket: SupportTicketItem }>('/api/support/tickets', payload);
  return response.data.ticket;
}

export async function getSupportTicket(ticketId: number) {
  const response = await apiClient.get<{ ticket: SupportTicketDetail }>(`/api/support/tickets/${ticketId}`);
  return response.data.ticket;
}

export async function replySupportTicket(ticketId: number, message: string, attachments?: string[]) {
  await apiClient.post(`/api/support/tickets/${ticketId}/reply`, { message, attachments });
}

export async function reportContent(payload: {
  content_type: string;
  content_id: string;
  reason: string;
  description?: string;
  content_preview?: string;
}) {
  try {
    const response = await apiClient.post('/api/support/reports', payload);
    return response.data;
  } catch (error) {
    const status = (error as { response?: { status?: number } })?.response?.status;
    if (status && status !== 404) {
      throw error;
    }
    const fallback = await apiClient.post('/api/reports', payload);
    return fallback.data;
  }
}
