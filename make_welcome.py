file_path = 'client/src/pages/WelcomeScreen.tsx'
content = '''import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Input, Spinner } from '@heroui/react';
import { Sparkles, User, Lock, Plus } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useProfileStore } from '../store/profileStore';
import apiClient from '../lib/api';

interface LocalUser {
  id: int;
  name: string;
}

export function WelcomeScreen() {
  const navigate = useNavigate();
  const [users, setUsers] = useState<LocalUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState<LocalUser | null>(null);
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loggingIn, setLoggingIn] = useState(false);
  const setProfile = useProfileStore((s) => s.setProfile);

  useEffect(() => {
    async function fetchUsers() {
      try {
        const res = await apiClient.get('/api/auth/users');
        if (res.data && res.data.users) {
          setUsers(res.data.users);
          // If no users, just redirect instantly to setup
          if (res.data.users.length === 0) {
            navigate('/setup');
          }
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
        setProfile(res.data.user); // updates zustand & isAuthenticated
        navigate('/dashboard');
      }
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Invalid password limit or authentication failed');
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

  return (
    <div className="min-h-dvh flex items-center justify-center bg-background p-4 relative overflow-hidden">
      {/* Background gradients for aesthetics */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-secondary/10 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-primary/10 blur-[120px] rounded-full pointer-events-none" />

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="text-center mb-8">
          <div className="mx-auto w-16 h-16 bg-bg-2 rounded-2xl flex items-center justify-center mb-6 edge-glow">
            <Sparkles className="w-8 h-8 text-secondary" />
          </div>
          <h1 className="text-3xl font-bold text-content1 mb-2">Welcome Back</h1>
          <p className="text-content2">Who is ready to learn today?</p>
        </div>

        <div className="bg-bg-2/80 backdrop-blur-xl border border-border-default rounded-3xl p-6 sm:p-8">
          {!selectedUser ? (
            <div className="space-y-4">
              <div className="grid gap-3">
                {users.map((user) => (
                  <button
                    key={user.id}
                    onClick={() => setSelectedUser(user)}
                    className="w-full flex items-center gap-4 p-4 rounded-xl border border-border-default bg-bg-1 hover:border-secondary/50 hover:bg-secondary/5 transition-all text-left group"
                  >
                    <div className="w-12 h-12 rounded-full bg-secondary/10 flex items-center justify-center text-secondary group-hover:scale-110 transition-transform">
                      <User className="w-6 h-6" />
                    </div>
                    <span className="text-lg font-medium text-content1">{user.name}</span>
                  </button>
                ))}
              </div>

              <div className="relative flex items-center py-4">
                <div className="flex-grow border-t border-border-default"></div>
                <span className="flex-shrink-0 mx-4 text-content3 text-sm">or</span>
                <div className="flex-grow border-t border-border-default"></div>
              </div>

              <Button
                className="w-full bg-bg-3 border border-border-default text-content1 hover:bg-bg-1"
                size="lg"
                startContent={<Plus className="w-5 h-5" />}
                onPress={() => navigate('/setup')}
              >
                Create New Profile
              </Button>
            </div>
          ) : (
            <AnimatePresence mode="popLayout">
              <motion.form
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                onSubmit={handleLogin}
                className="space-y-6"
              >
                <div className="flex items-center gap-4 mb-2">
                  <div className="w-12 h-12 rounded-full bg-secondary/20 flex items-center justify-center text-secondary">
                    <User className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-sm text-content2">Logging in as</p>
                    <p className="text-lg font-bold text-content1">{selectedUser.name}</p>
                  </div>
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
                />

                <div className="flex gap-3">
                  <Button
                    type="button"
                    variant="flat"
                    className="flex-1"
                    onPress={() => {
                      setSelectedUser(null);
                      setPassword('');
                      setError('');
                    }}
                  >
                    Back
                  </Button>
                  <Button
                    type="submit"
                    color="secondary"
                    className="flex-1 text-white shadow-glow"
                    isLoading={loggingIn}
                  >
                    Login
                  </Button>
                </div>
              </motion.form>
            </AnimatePresence>
          )}
        </div>
      </motion.div>
    </div>
  );
}
'''
with open(file_path, 'w') as f:
    f.write(content)

print("Created WelcomeScreen.tsx")
