import { useEffect, useRef, useState } from 'react';
import {
  Card,
  CardBody,
  CardHeader,
  Button,
  Input,
  Chip,
  Spinner,
} from '@heroui/react';
import { Shield, KeyRound, Laptop, AlertTriangle } from 'lucide-react';
import {
  confirmPasswordReset,
  getSecurityOverview,
  requestPasswordReset,
  revokeOtherSessions,
  revokeSession,
  type LoginHistoryItem,
  type SecurityEventItem,
  type UserSessionInfo,
} from '../lib/accountService';
import { getApiErrorMessage } from '../lib/api';
import { useProfileStore } from '../store/profileStore';

export function SecurityPage() {
  const loadedOnceRef = useRef(false);
  const profile = useProfileStore((s) => s.profile);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessions, setSessions] = useState<UserSessionInfo[]>([]);
  const [history, setHistory] = useState<LoginHistoryItem[]>([]);
  const [events, setEvents] = useState<SecurityEventItem[]>([]);

  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [generatedToken, setGeneratedToken] = useState<string | null>(null);
  const [tokenExpiry, setTokenExpiry] = useState<number | null>(null);

  async function loadData() {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getSecurityOverview();
      setSessions(data.sessions);
      setHistory(data.loginHistory);
      setEvents(data.events);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Failed to load security data.'));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (loadedOnceRef.current) return;
    loadedOnceRef.current = true;
    void loadData();
  }, []);

  async function handleRequestReset() {
    if (!profile?.email) {
      setError('Email is required in profile to request password reset.');
      return;
    }
    try {
      const response = await requestPasswordReset(profile.email);
      setGeneratedToken(response.reset_token ?? null);
      setTokenExpiry(response.expires_in_minutes ?? null);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Unable to request password reset token.'));
    }
  }

  async function handleConfirmReset() {
    if (!resetToken.trim() || !newPassword.trim()) {
      setError('Reset token and new password are required.');
      return;
    }
    try {
      await confirmPasswordReset(resetToken.trim(), newPassword);
      setResetToken('');
      setNewPassword('');
      setGeneratedToken(null);
      setTokenExpiry(null);
      await loadData();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Unable to reset password.'));
    }
  }

  async function handleRevokeSession(sessionId: string) {
    try {
      await revokeSession(sessionId);
      await loadData();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Unable to revoke session.'));
    }
  }

  async function handleRevokeOthers() {
    try {
      await revokeOtherSessions();
      await loadData();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Unable to revoke other sessions.'));
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <h1 className="flex items-center gap-2" style={{ fontFamily: 'var(--font-heading)', fontSize: 20, fontWeight: 600, color: 'var(--text-primary)' }}>
        <Shield className="w-6 h-6 text-secondary" />
        Security Center
      </h1>

      <Card className="glass">
        <CardHeader className="pb-2">
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>Password Reset</h2>
        </CardHeader>
        <CardBody className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Button color="secondary" startContent={<KeyRound className="w-4 h-4" />} onPress={() => void handleRequestReset()}>
              Generate Reset Token
            </Button>
            {generatedToken ? <Chip variant="flat" color="warning">Token: {generatedToken}</Chip> : null}
            {tokenExpiry ? <Chip variant="flat">Expires in {tokenExpiry} min</Chip> : null}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Input
              label="Reset Token"
              value={resetToken}
              onValueChange={setResetToken}
              aria-label="Reset token"
              variant="bordered"
            />
            <Input
              label="New Password"
              type="password"
              value={newPassword}
              onValueChange={setNewPassword}
              aria-label="New password"
              variant="bordered"
            />
          </div>
          <Button color="secondary" onPress={() => void handleConfirmReset()}>Confirm Password Reset</Button>
        </CardBody>
      </Card>

      <Card className="glass">
        <CardHeader className="flex justify-between items-center">
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>Active Sessions</h2>
          <Button size="sm" variant="flat" color="danger" onPress={() => void handleRevokeOthers()}>Revoke Other Sessions</Button>
        </CardHeader>
        <CardBody>
          {isLoading ? (
            <div className="py-8 flex justify-center"><Spinner label="Loading sessions" /></div>
          ) : sessions.length === 0 ? (
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>No sessions found.</p>
          ) : (
            <div className="space-y-2">
              {sessions.map((session) => (
                <div key={session.id} className="rounded-lg p-3 flex items-center justify-between gap-3" style={{ border: '1px solid var(--border-subtle)' }}>
                  <div className="min-w-0">
                    <p className="flex items-center gap-2" style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                      <Laptop className="w-4 h-4" />
                      {session.device_id || 'Unknown device'}
                    </p>
                    <p style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                      {session.ip_address || 'No IP'} • Last active {session.last_activity ? new Date(session.last_activity).toLocaleString() : 'unknown'}
                    </p>
                  </div>
                  <Button size="sm" variant="flat" color="danger" isDisabled={session.is_revoked} onPress={() => void handleRevokeSession(session.id)}>
                    {session.is_revoked ? 'Revoked' : 'Revoke'}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="glass">
          <CardHeader><h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>Login History</h2></CardHeader>
          <CardBody className="space-y-2">
            {history.length === 0 ? (
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>No login records.</p>
            ) : history.map((entry) => (
              <div key={entry.id} className="flex justify-between gap-2" style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                <span>{entry.success ? 'Success' : 'Failed'}</span>
                <span>{entry.ip_address || 'No IP'}</span>
                <span>{entry.created_at ? new Date(entry.created_at).toLocaleDateString() : '-'}</span>
              </div>
            ))}
          </CardBody>
        </Card>

        <Card className="glass">
          <CardHeader><h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>Security Events</h2></CardHeader>
          <CardBody className="space-y-2">
            {events.length === 0 ? (
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>No security events.</p>
            ) : events.map((event) => (
              <div key={event.id} className="flex justify-between gap-2" style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                <span className="inline-flex items-center gap-1">
                  {event.severity === 'critical' ? <AlertTriangle className="w-3 h-3 text-danger" /> : null}
                  {event.event_type}
                </span>
                <span>{event.severity}</span>
                <span>{event.created_at ? new Date(event.created_at).toLocaleDateString() : '-'}</span>
              </div>
            ))}
          </CardBody>
        </Card>
      </div>

      {error ? <p style={{ fontSize: 12, color: 'var(--red)' }}>{error}</p> : null}
    </div>
  );
}
