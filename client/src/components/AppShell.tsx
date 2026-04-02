import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  Navbar,
  NavbarBrand,
  NavbarContent,
  NavbarItem,
  Button,
  Tooltip,
  Avatar,
  Badge,
  Chip,
} from '@heroui/react';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  BookOpen,
  Library,
  Trophy,
  CalendarDays,
  Globe,
  User,
  Bell,
  LifeBuoy,
  History,
  Sparkles,
  Flame,
  Zap,
  LogOut,
} from 'lucide-react';
import { useProfileStore } from '../store/profileStore';
import { useGamificationStore } from '../store/gamificationStore';
import { ThemeToggle } from './ThemeToggle';
import { SyncStatusPill } from './SyncStatusPill';

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

const baseNavItems: NavItem[] = [
  { path: '/home', label: 'Home', icon: <LayoutDashboard className="w-5 h-5" /> },
  { path: '/books', label: 'NCERT Books', icon: <BookOpen className="w-5 h-5" /> },
  { path: '/achievements', label: 'Achievements', icon: <Trophy className="w-5 h-5" /> },
  { path: '/study-plan', label: 'Study Plan', icon: <CalendarDays className="w-5 h-5" /> },
  { path: '/learn-sessions', label: 'Learn Sessions', icon: <History className="w-5 h-5" /> },
  { path: '/resources', label: 'Resources', icon: <Globe className="w-5 h-5" /> },
  { path: '/library', label: 'Library', icon: <Library className="w-5 h-5" /> },
  { path: '/notifications', label: 'Notifications', icon: <Bell className="w-5 h-5" /> },
  { path: '/support', label: 'Support', icon: <LifeBuoy className="w-5 h-5" /> },
  { path: '/profile', label: 'Profile', icon: <User className="w-5 h-5" /> },
];

export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const isHomeRoute = location.pathname === '/home' || location.pathname.startsWith('/home/');
  const profile = useProfileStore((s) => s.profile);
  const setAuthenticated = useProfileStore((s) => s.setAuthenticated);
  const { currentLevel, totalXP, currentStreak } = useGamificationStore();
  const navItems = baseNavItems;
  const roleLabel = 'Student';

  const handleLogout = () => {
    localStorage.removeItem('APXMIND_token');
    setAuthenticated(false);
    navigate('/login', { replace: true });
  };

  const initials = profile?.name
    ?.split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) || 'AN';

  return (
    <div className="flex h-dvh bg-bg-0 relative overflow-hidden">
      <div className="fixed top-3 right-3 md:top-4 md:right-4 z-40 flex items-center gap-2">
        <SyncStatusPill />
        <ThemeToggle />
      </div>

      {/* Ambient background orbs */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-secondary/10 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-primary/10 blur-[120px] rounded-full pointer-events-none" />
      {/* Sidebar */}
      <aside
        className="hidden md:flex flex-col border-r z-20"
        style={{
          width: 'var(--sidebar-w)',
          background: 'var(--bg-1)',
          borderRight: '1px solid var(--border-subtle)',
        }}
      >
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-5 py-5 border-b" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div
            className="flex items-center justify-center"
            style={{ width: 28, height: 28, background: 'var(--accent)', borderRadius: 'var(--r-sm)' }}
          >
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <span
            style={{
              fontFamily: 'var(--font-heading)',
              fontSize: 16,
              fontWeight: 600,
              color: 'var(--text-primary)',
            }}
          >
            APXMIND
          </span>
        </div>

        {/* XP / Level / Streak summary */}
        <div className="px-4 py-3.5 border-b space-y-2.5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="flex items-center gap-2.5">
            <Badge content={currentLevel} color="secondary" size="sm" placement="bottom-right">
              <Avatar
                name={initials}
                size="sm"
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: '50%',
                  background: 'var(--accent-soft)',
                  border: '1.5px solid var(--accent-border)',
                  color: 'var(--accent)',
                  fontSize: 12,
                  fontWeight: 600,
                }}
              />
            </Badge>
            <div className="flex-1 min-w-0">
              <p className="truncate" style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{profile?.name || 'Student'}</p>
              <p style={{ fontSize: 10, color: 'var(--text-faint)' }}>Level {currentLevel}</p>
              <Chip
                size="sm"
                variant="flat"
                color="default"
                style={{
                  marginTop: 4,
                  borderRadius: 'var(--r-pill)',
                  fontSize: 10,
                  height: 18,
                }}
              >
                {roleLabel}
              </Chip>
            </div>
          </div>
          <div className="flex gap-2">
            <Chip
              size="sm"
              variant="flat"
              startContent={<Zap className="w-3 h-3" />}
              style={{
                background: 'var(--amber-soft)',
                color: 'var(--amber)',
                border: '1px solid var(--amber-border)',
                borderRadius: 'var(--r-pill)',
                padding: '2px 9px',
                fontSize: 10,
                fontWeight: 500,
              }}
            >
              {totalXP} XP
            </Chip>
            {currentStreak > 0 && (
              <Chip
                size="sm"
                variant="flat"
                startContent={<Flame className="w-3 h-3" />}
                style={{
                  background: 'var(--red-soft)',
                  color: 'var(--red)',
                  border: '1px solid var(--red-border)',
                  borderRadius: 'var(--r-pill)',
                  padding: '2px 9px',
                  fontSize: 10,
                  fontWeight: 500,
                }}
              >
                {currentStreak}d
              </Chip>
            )}
          </div>
        </div>

        {/* Nav links */}
        <nav className="flex-1 py-3 px-2 overflow-y-auto space-y-0.5">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path || location.pathname.startsWith(item.path + '/');
            return (
              <NavLink key={item.path} to={item.path}>
                <div
                  className={`relative flex items-center gap-3 rounded-xl ${isActive
                    ? 'font-semibold'
                    : ''
                    }`}
                  style={
                    isActive
                      ? {
                        color: 'var(--text-primary)',
                        background: 'var(--accent-glow)',
                        borderLeft: '3px solid var(--accent)',
                        padding: '8px 16px',
                        fontSize: 13,
                        transition: 'all 0.1s',
                      }
                      : {
                        color: 'var(--text-muted)',
                        borderLeft: '3px solid transparent',
                        padding: '8px 16px',
                        fontSize: 13,
                        transition: 'all 0.1s',
                      }
                  }
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.color = 'var(--text-primary)';
                      e.currentTarget.style.background =
                        document.documentElement.classList.contains('light') ? 'rgba(0, 0, 0, 0.03)' : 'rgba(255, 255, 255, 0.03)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.color = 'var(--text-muted)';
                      e.currentTarget.style.background = 'transparent';
                    }
                  }}
                >
                  {isActive && (
                    <motion.div layoutId="sidebar-active" className="hidden" transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }} />
                  )}
                  {item.icon}
                  {item.label}
                </div>
              </NavLink>
            );
          })}
        </nav>

        {/* Bottom actions */}
        <div className="p-3 border-t" style={{ borderTop: '1px solid var(--border-subtle)' }}>
          <Button
            variant="light"
            className="w-full justify-start"
            startContent={<LogOut className="w-4 h-4" />}
            onPress={handleLogout}
            style={{ color: 'var(--text-muted)' }}
          >
            Logout
          </Button>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0 z-10">
        {/* Top navbar (mobile + secondary info) */}
        <Navbar
          maxWidth="full"
          className="md:hidden border-b"
          style={{
            background: 'var(--bg-1)',
            borderBottom: '1px solid var(--border-subtle)',
            padding: '10px 28px',
          }}
          height="3.5rem"
        >
          <NavbarBrand className="md:hidden">
            <Sparkles className="w-5 h-5 text-emerald-400 mr-1" />
            <span className="font-bold text-sm bg-linear-to-r from-emerald-400 to-purple-400 bg-clip-text text-transparent">
              APXMIND
            </span>
          </NavbarBrand>

          <NavbarContent className="md:hidden gap-1 overflow-x-auto" justify="center">
            {navItems.map((item) => {
              const isActive = location.pathname.startsWith(item.path);
              return (
                <NavbarItem key={item.path}>
                  <Tooltip content={item.label}>
                    <NavLink to={item.path}>
                      <Button
                        isIconOnly
                        aria-label={item.label}
                        variant={isActive ? 'flat' : 'light'}
                        color={isActive ? 'secondary' : 'default'}
                        size="sm"
                      >
                        {item.icon}
                      </Button>
                    </NavLink>
                  </Tooltip>
                </NavbarItem>
              );
            })}
          </NavbarContent>

          <NavbarContent justify="end" className="gap-2">
            <NavbarItem className="md:hidden">
              <Chip
                size="sm"
                variant="flat"
                color="default"
                style={{
                  borderRadius: 'var(--r-pill)',
                  fontSize: 10,
                  height: 20,
                }}
              >
                {roleLabel}
              </Chip>
            </NavbarItem>
            <NavbarItem>
              <Tooltip content="Logout">
                <Button isIconOnly aria-label="Logout" variant="light" size="sm" onPress={handleLogout}>
                  <LogOut className="w-4 h-4" />
                </Button>
              </Tooltip>
            </NavbarItem>
            <NavbarItem>
              <Tooltip content={`Role: ${roleLabel}`}>
                <NavLink to="/profile">
                  <Avatar
                    name={initials}
                    size="sm"
                    className="cursor-pointer"
                    style={{
                      width: 30,
                      height: 30,
                      borderRadius: '50%',
                      background: 'var(--accent-soft)',
                      border: '1.5px solid var(--accent-border)',
                      color: 'var(--accent)',
                      fontSize: 12,
                      fontWeight: 600,
                    }}
                  />
                </NavLink>
              </Tooltip>
            </NavbarItem>
          </NavbarContent>
        </Navbar>

        {/* Page content */}
        <main
          className={`flex-1 overflow-y-auto bg-transparent z-10 relative ${isHomeRoute ? 'px-4 md:px-6 pt-4 md:pt-5 pb-2 md:pb-3' : 'p-4 md:p-6'
            }`}
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
