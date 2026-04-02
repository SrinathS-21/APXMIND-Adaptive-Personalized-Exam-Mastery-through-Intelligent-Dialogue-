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
