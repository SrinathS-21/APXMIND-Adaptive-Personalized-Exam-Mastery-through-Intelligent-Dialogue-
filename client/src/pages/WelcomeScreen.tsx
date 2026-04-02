import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Input, Select, SelectItem, Spinner } from '@heroui/react';
import { User, Lock, Plus } from 'lucide-react';
import { motion } from 'framer-motion';
import { useTheme } from '../hooks/useTheme';
import { ThemeToggle } from '../components/ThemeToggle';
import { normalizeApiUserProfile, useProfileStore } from '../store/profileStore';
import apiClient from '../lib/api';

interface LocalUser {
  id: number;
  name: string;
}

export function WelcomeScreen() {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const [users, setUsers] = useState<LocalUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loggingIn, setLoggingIn] = useState(false);
  const setProfile = useProfileStore((s) => s.setProfile);
  const selectedUser = users.find((user) => String(user.id) === selectedUserId) ?? null;

  useEffect(() => {
    async function fetchUsers() {
      try {
        const res = await apiClient.get('/api/auth/users');
        if (res.data && res.data.users) {
          setUsers(res.data.users);
        }
      } catch (err) {
        console.error('Failed to fetch local users', err);
      } finally {
        setLoading(false);
      }
    }
    fetchUsers();
  }, [navigate]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser || !password) return;

    setLoggingIn(true);
    setError('');

    try {
      const res = await apiClient.post('/api/auth/login', {
        name: selectedUser.name,
        password
      });

      if (res.data.success && res.data.token) {
        localStorage.setItem('APXMIND_token', res.data.token);
        setProfile(normalizeApiUserProfile(res.data.user));
        navigate('/home');
      }
    } catch (err: unknown) {
      console.error(err);
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Invalid password limit or authentication failed');
    } finally {
      setLoggingIn(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-background">
        <Spinner color="secondary" />
      </div>
    );
  }

  const logoFilter =
    theme === 'dark'
      ? 'brightness(0) invert(1)'
      : 'brightness(0) saturate(100%) invert(35%) sepia(88%) saturate(1510%) hue-rotate(236deg) brightness(95%) contrast(95%)';

  return (
    <div className="min-h-dvh flex items-center justify-center bg-background p-4 relative overflow-hidden">
      <div className="absolute top-4 right-4 z-20">
        <ThemeToggle />
      </div>

      {/* Background gradients for aesthetics */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-secondary/10 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-primary/10 blur-[120px] rounded-full pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="text-center mb-7">
          <div className="mx-auto w-72 h-24 flex items-center justify-center mb-4 overflow-visible">
            <img
              src="/asset/apxmind-logo.svg"
              alt="APXMIND logo"
              className="w-full h-full object-contain"
              style={{ filter: logoFilter, transform: 'scale(2.55)', transformOrigin: 'center center' }}
            />
          </div>
          <h1 className="ui-page-title justify-center" style={{ fontSize: 28 }}>Welcome Back</h1>
          <p className="ui-page-subtitle mt-1">Who is ready to learn today?</p>
        </div>

        <div className="bg-bg-2/85 backdrop-blur-xl border border-border-default rounded-2xl p-5 sm:p-6 shadow-[0_10px_30px_rgba(0,0,0,0.12)]">
          {users.length === 0 ? (
            <div className="space-y-3 text-center">
              <p className="text-sm text-text-muted">No account found on this device.</p>
              <Button
                className="w-full bg-accent text-white font-semibold hover:opacity-90"
                size="md"
                startContent={<Plus className="w-5 h-5" />}
                onPress={() => navigate('/register')}
              >
                Create New Profile
              </Button>
            </div>
          ) : (
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-1.5">
                <Select
                  label="Profile"
                  placeholder="Select profile"
                  selectedKeys={selectedUserId ? new Set([selectedUserId]) : new Set()}
                  onSelectionChange={(keys) => {
                    const next = String(Array.from(keys)[0] ?? '');
                    setSelectedUserId(next);
                    setError('');
                  }}
                  variant="bordered"
                  size="md"
                  startContent={<User className="w-4 h-4 text-text-muted" />}
                  classNames={{
                    trigger: 'bg-bg-3 border-border-default hover:border-accent rounded-[var(--r-md)] min-h-11 px-3',
                    label: 'text-[11px] text-text-muted mb-[5px]',
                    value: 'text-[13px] text-text-primary',
                    popoverContent: 'bg-bg-2 border border-border-default shadow-[0_10px_30px_rgba(92,60,35,0.14)]',
                    listbox: 'p-1',
                  }}
                >
                  {users.map((user) => (
                    <SelectItem key={String(user.id)} textValue={user.name} className="text-text-primary data-[hover=true]:bg-bg-3 data-[selected=true]:bg-accent-soft">
                      {user.name}
                    </SelectItem>
                  ))}
                </Select>
              </div>

              <Input
                type="password"
                label="Password / PIN"
                placeholder="Enter your local password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                startContent={<Lock className="w-4 h-4 text-content3" />}
                isInvalid={!!error}
                errorMessage={error}
                autoFocus
                classNames={{
                  inputWrapper: 'bg-bg-3 border-border-default rounded-(--r-md)',
                  label: 'text-[11px] text-text-muted',
                  input: 'text-[13px] text-text-primary placeholder:text-text-faint',
                }}
              />

              <Button
                type="submit"
                color="secondary"
                className="w-full shadow-glow"
                isLoading={loggingIn}
                isDisabled={!selectedUserId || !password}
              >
                Continue to Home
              </Button>

              <div className="relative flex items-center py-1">
                <div className="grow border-t border-border-default"></div>
                <span className="shrink-0 mx-4 text-content3 text-sm">or</span>
                <div className="grow border-t border-border-default"></div>
              </div>

              <Button
                className="w-full bg-accent text-white font-semibold hover:opacity-90"
                size="md"
                startContent={<Plus className="w-5 h-5" />}
                onPress={() => navigate('/register')}
              >
                Create New Profile
              </Button>
            </form>
          )}
        </div>
      </motion.div>
    </div>
  );
}
