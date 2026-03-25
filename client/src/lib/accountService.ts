import apiClient from './api';

export interface NotificationItem {
  id: string;
  title: string;
  body: string;
  category: string;
  priority?: string;
  is_read: boolean;
  created_at?: string | null;
}

export interface NotificationSettings {
  all_notifications_enabled: boolean;
  push_enabled: boolean;
  email_enabled: boolean;
  sms_enabled: boolean;
  quiet_hours_enabled?: boolean;
}

export interface SubscriptionPlan {
  id: string;
  code: string;
  display_name: string;
  description?: string | null;
  price_inr: number;
  original_price_inr?: number | null;
  billing_period: string;
  duration_days: number;
  is_featured?: boolean;
  badge_text?: string | null;
}

export interface UserSubscription {
  id: string;
  plan_id: string;
  status: string;
  started_at?: string | null;
  expires_at?: string | null;
  auto_renew: boolean;
  payment_method?: string | null;
}

export interface UserSessionInfo {
  id: string;
  device_id?: string | null;
  ip_address?: string | null;
  location?: string | null;
  is_revoked: boolean;
  last_activity?: string | null;
  created_at?: string | null;
}

export interface LoginHistoryItem {
  id: number;
  success: boolean;
  ip_address?: string | null;
  browser?: string | null;
  os?: string | null;
  is_suspicious?: boolean;
  created_at?: string | null;
}

export interface SecurityEventItem {
  id: number;
  event_type: string;
  severity: string;
  description: string;
  ip_address?: string | null;
  created_at?: string | null;
}

export async function getNotifications() {
  const [listRes, unreadRes, prefRes] = await Promise.all([
    apiClient.get('/api/notifications?limit=50'),
    apiClient.get('/api/notifications/unread-count'),
    apiClient.get('/api/notifications/preferences'),
  ]);

  return {
    notifications: (listRes.data?.notifications ?? []) as NotificationItem[],
    unreadCount: (unreadRes.data?.unread_count ?? 0) as number,
    settings: (prefRes.data?.settings ?? {
      all_notifications_enabled: true,
      push_enabled: true,
      email_enabled: true,
      sms_enabled: false,
    }) as NotificationSettings,
  };
}

export async function updateNotificationSettings(settings: Partial<NotificationSettings>) {
  await apiClient.put('/api/notifications/preferences', settings);
}

export async function markNotificationRead(notificationId: string, read: boolean) {
  await apiClient.patch(`/api/notifications/${notificationId}/read`, { read });
}

export async function markAllNotificationsRead() {
  await apiClient.post('/api/notifications/read-all');
}

export async function deleteNotification(notificationId: string) {
  await apiClient.delete(`/api/notifications/${notificationId}`);
}

export async function getSubscriptionOverview() {
  const [plansRes, currentRes, paymentsRes, invoicesRes, walletRes] = await Promise.all([
    apiClient.get('/api/payments/plans'),
    apiClient.get('/api/payments/subscriptions/current'),
    apiClient.get('/api/payments/payments?limit=10'),
    apiClient.get('/api/payments/invoices?limit=10'),
    apiClient.get('/api/payments/wallet'),
  ]);

  return {
    plans: (plansRes.data?.plans ?? []) as SubscriptionPlan[],
    currentSubscription: (currentRes.data?.subscription ?? null) as UserSubscription | null,
    payments: (paymentsRes.data?.payments ?? []) as Array<{ id: string; final_amount: number; status: string; created_at?: string | null }>,
    invoices: (invoicesRes.data?.invoices ?? []) as Array<{ id: string; invoice_number: string; total_amount: number; status: string; invoice_date?: string | null }>,
    wallet: (walletRes.data?.wallet ?? { balance: 0, lifetime_earned: 0, lifetime_spent: 0 }) as {
      balance: number;
      lifetime_earned: number;
      lifetime_spent: number;
    },
  };
}

export async function purchasePlan(planId: string, promoCode?: string) {
  const checkout = await apiClient.post('/api/payments/checkout', {
    plan_id: planId,
    payment_method: 'manual',
    promo_code: promoCode?.trim() || undefined,
  });

  const paymentId = checkout.data?.checkout?.payment_id as string;
  await apiClient.post('/api/payments/verify', {
    payment_id: paymentId,
    gateway_payment_id: `manual_${Date.now()}`,
    status_value: 'completed',
  });
}

export async function cancelSubscription(subscriptionId: string) {
  await apiClient.post(
    `/api/payments/subscriptions/${subscriptionId}/cancel`,
    'Cancelled from profile settings',
    {
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );
}

export async function getSecurityOverview() {
  const [historyResult, eventsResult] = await Promise.allSettled([
    apiClient.get('/api/security/login-history?limit=20'),
    apiClient.get('/api/security/events?limit=20'),
  ]);

  const historyRes = historyResult.status === 'fulfilled' ? historyResult.value : null;
  const eventsRes = eventsResult.status === 'fulfilled' ? eventsResult.value : null;

  return {
    sessions: [] as UserSessionInfo[],
    loginHistory: (historyRes?.data?.history ?? []) as LoginHistoryItem[],
    events: (eventsRes?.data?.events ?? []) as SecurityEventItem[],
  };
}

export async function revokeSession(sessionId: string) {
  await apiClient.post(`/api/security/sessions/${sessionId}/revoke`);
}

export async function revokeOtherSessions() {
  await apiClient.post('/api/security/sessions/revoke-others', null);
}

export async function requestPasswordReset(email: string) {
  const response = await apiClient.post('/api/security/password-reset/request', { email });
  return response.data as { success: boolean; message: string; reset_token?: string; expires_in_minutes?: number };
}

export async function confirmPasswordReset(token: string, newPassword: string) {
  await apiClient.post('/api/security/password-reset/confirm', { token, new_password: newPassword });
}