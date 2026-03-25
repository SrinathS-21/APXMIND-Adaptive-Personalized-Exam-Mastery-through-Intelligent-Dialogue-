import { useEffect, useRef, useState } from 'react';
import {
  Card,
  CardBody,
  CardHeader,
  Button,
  Checkbox,
  Chip,
  Divider,
  Spinner,
} from '@heroui/react';
import { Bell, CheckCheck, Trash2 } from 'lucide-react';
import {
  deleteNotification,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type NotificationItem,
  type NotificationSettings,
  updateNotificationSettings,
} from '../lib/accountService';
import { getApiErrorMessage } from '../lib/api';

export function NotificationsPage() {
  const loadedOnceRef = useRef(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [settings, setSettings] = useState<NotificationSettings>({
    all_notifications_enabled: true,
    push_enabled: true,
    email_enabled: true,
    sms_enabled: false,
  });

  async function loadData() {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getNotifications();
      setNotifications(data.notifications);
      setUnreadCount(data.unreadCount);
      setSettings(data.settings);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Failed to load notifications.'));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (loadedOnceRef.current) return;
    loadedOnceRef.current = true;
    void loadData();
  }, []);

  async function handleSaveSettings() {
    setIsSaving(true);
    setError(null);
    try {
      await updateNotificationSettings(settings);
      await loadData();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Unable to save notification settings.'));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleMarkRead(id: string, read: boolean) {
    try {
      await markNotificationRead(id, read);
      await loadData();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Unable to update notification state.'));
    }
  }

  async function handleMarkAllRead() {
    try {
      await markAllNotificationsRead();
      await loadData();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Unable to mark all notifications as read.'));
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteNotification(id);
      await loadData();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Unable to delete notification.'));
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <h1 className="flex items-center gap-2" style={{ fontFamily: 'var(--font-heading)', fontSize: 20, fontWeight: 600, color: 'var(--text-primary)' }}>
        <Bell className="w-6 h-6 text-secondary" />
        Notifications
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="glass lg:col-span-1">
          <CardHeader>
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>Preferences</h2>
          </CardHeader>
          <CardBody className="gap-3">
            <Checkbox isSelected={settings.all_notifications_enabled} onValueChange={(v) => setSettings((s) => ({ ...s, all_notifications_enabled: v }))}>
              Enable all notifications
            </Checkbox>
            <Checkbox isSelected={settings.push_enabled} onValueChange={(v) => setSettings((s) => ({ ...s, push_enabled: v }))}>
              Push notifications
            </Checkbox>
            <Checkbox isSelected={settings.email_enabled} onValueChange={(v) => setSettings((s) => ({ ...s, email_enabled: v }))}>
              Email notifications
            </Checkbox>
            <Checkbox isSelected={settings.sms_enabled} onValueChange={(v) => setSettings((s) => ({ ...s, sms_enabled: v }))}>
              SMS notifications
            </Checkbox>
            <Button color="secondary" onPress={handleSaveSettings} isLoading={isSaving}>
              Save Preferences
            </Button>
          </CardBody>
        </Card>

        <Card className="glass lg:col-span-2">
          <CardHeader className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>Inbox</h2>
              <Chip size="sm" variant="flat" color={unreadCount > 0 ? 'danger' : 'default'}>
                {unreadCount} unread
              </Chip>
            </div>
            <Button size="sm" variant="flat" color="secondary" startContent={<CheckCheck className="w-4 h-4" />} onPress={handleMarkAllRead}>
              Mark all as read
            </Button>
          </CardHeader>
          <CardBody>
            {isLoading ? (
              <div className="py-8 flex justify-center"><Spinner label="Loading notifications" /></div>
            ) : notifications.length === 0 ? (
              <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No notifications yet.</p>
            ) : (
              <div className="space-y-3">
                {notifications.map((item) => (
                  <div key={item.id} className="rounded-lg p-3" style={{ border: '1px solid var(--border-subtle)', background: item.is_read ? 'var(--bg-2)' : 'var(--accent-glow)' }}>
                    <div className="flex justify-between items-start gap-3">
                      <div className="min-w-0">
                        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{item.title}</p>
                        <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{item.body}</p>
                        <div className="flex items-center gap-2 mt-2">
                          <Chip size="sm" variant="flat">{item.category}</Chip>
                          {item.priority ? <Chip size="sm" variant="flat" color="warning">{item.priority}</Chip> : null}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="flat"
                          color={item.is_read ? 'default' : 'success'}
                          onPress={() => void handleMarkRead(item.id, !item.is_read)}
                        >
                          {item.is_read ? 'Mark unread' : 'Mark read'}
                        </Button>
                        <Button isIconOnly aria-label="Delete notification" size="sm" variant="light" color="danger" onPress={() => void handleDelete(item.id)}>
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                    <Divider className="my-2" />
                    <p style={{ fontSize: 11, color: 'var(--text-faint)' }}>{item.created_at ? new Date(item.created_at).toLocaleString() : 'Unknown time'}</p>
                  </div>
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      {error ? <p style={{ fontSize: 12, color: 'var(--red)' }}>{error}</p> : null}
    </div>
  );
}
