import { useEffect, useMemo, useState } from 'react';
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
  ChevronDown,
  Globe,
  User,
  Bell,
  LifeBuoy,
  History,
  Sparkles,
  Flame,
  Zap,
  LogOut,
  NotebookPen,
} from 'lucide-react';
import { useProfileStore } from '../store/profileStore';
import { normalizeApiUserProfile } from '../store/profileStore';
import { useGamificationStore } from '../store/gamificationStore';
import apiClient from '../lib/api';
import {
  LANGUAGE_OPTIONS,
  normalizeLanguage,
  readLanguageFromPersistedProfile,
  writeLanguageToPersistedProfile,
} from '../lib/language';
import { tUi } from '../lib/uiI18n';
import { ThemeToggle } from './ThemeToggle';
import { SyncStatusPill } from './SyncStatusPill';

interface NavItem {
  path: string;
  labelKey: string;
  label: string;
  icon: React.ReactNode;
}

const baseNavItems: Omit<NavItem, 'label'>[] = [
  { path: '/home', labelKey: 'nav.home', icon: <LayoutDashboard className="w-5 h-5" /> },
  { path: '/books', labelKey: 'nav.ncertBooks', icon: <BookOpen className="w-5 h-5" /> },
  { path: '/achievements', labelKey: 'nav.achievements', icon: <Trophy className="w-5 h-5" /> },
  { path: '/study-plan', labelKey: 'nav.studyPlan', icon: <CalendarDays className="w-5 h-5" /> },
  { path: '/learn-sessions', labelKey: 'nav.learnSessions', icon: <History className="w-5 h-5" /> },
  { path: '/notebook-studio', labelKey: 'nav.notebookStudio', icon: <NotebookPen className="w-5 h-5" /> },
  { path: '/resources', labelKey: 'nav.resources', icon: <Globe className="w-5 h-5" /> },
  { path: '/library', labelKey: 'nav.library', icon: <Library className="w-5 h-5" /> },
  { path: '/notifications', labelKey: 'nav.notifications', icon: <Bell className="w-5 h-5" /> },
  { path: '/support', labelKey: 'nav.support', icon: <LifeBuoy className="w-5 h-5" /> },
  { path: '/profile', labelKey: 'nav.profile', icon: <User className="w-5 h-5" /> },
];

export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const isHomeRoute = location.pathname === '/home' || location.pathname.startsWith('/home/');
  const profile = useProfileStore((s) => s.profile);
  const setProfile = useProfileStore((s) => s.setProfile);
  const updateProfile = useProfileStore((s) => s.updateProfile);
  const setAuthenticated = useProfileStore((s) => s.setAuthenticated);
  const { currentLevel, totalXP, currentStreak } = useGamificationStore();
  const [selectedLanguage, setSelectedLanguage] = useState(() =>
    normalizeLanguage(profile?.preferredLanguage ?? readLanguageFromPersistedProfile())
  );
  const roleLabel = tUi(selectedLanguage, 'app.student');
  const navItems = useMemo<NavItem[]>(
    () => baseNavItems.map((item) => ({ ...item, label: tUi(selectedLanguage, item.labelKey) })),
    [selectedLanguage]
  );

  useEffect(() => {
    setSelectedLanguage(
      normalizeLanguage(profile?.preferredLanguage ?? readLanguageFromPersistedProfile())
    );
  }, [profile?.preferredLanguage]);

  const handleLanguageChange = async (value: string) => {
    const nextLanguage = normalizeLanguage(value);
    if (nextLanguage === selectedLanguage) {
      return;
    }

    setSelectedLanguage(nextLanguage);
    writeLanguageToPersistedProfile(nextLanguage);
    updateProfile({ preferredLanguage: nextLanguage });

    try {
      const response = await apiClient.put('/api/auth/profile', { preferred_language: nextLanguage });
      if (response?.data) {
        setProfile(normalizeApiUserProfile(response.data));
      }
    } catch (error) {
      if (import.meta.env.DEV) {
        console.warn('Failed to sync preferred language with backend profile:', error);
      }
    }
  };

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
        <div
          className="relative flex items-center rounded-full"
          style={{
            background: 'var(--bg-1)',
            border: '1px solid var(--border-subtle)',
            boxShadow: '0 6px 18px rgba(0, 0, 0, 0.12)',
          }}
        >
          <Globe
            className="w-3.5 h-3.5"
            style={{
              position: 'absolute',
              left: 10,
              color: 'var(--text-muted)',
              pointerEvents: 'none',
            }}
          />
          <select
            aria-label={tUi(selectedLanguage, 'app.selectLanguage')}
            value={selectedLanguage}
            onChange={(event) => {
              void handleLanguageChange(event.target.value);
            }}
            style={{
              background: 'transparent',
              color: 'var(--text-primary)',
              border: 'none',
              outline: 'none',
              fontSize: 12,
              fontWeight: 600,
              letterSpacing: '0.01em',
              lineHeight: 1,
              padding: '9px 30px 9px 30px',
              borderRadius: 999,
              cursor: 'pointer',
              appearance: 'none',
              WebkitAppearance: 'none',
              MozAppearance: 'none',
            }}
          >
            {LANGUAGE_OPTIONS.map((option) => (
              <option key={option.code} value={option.code}>
                {option.label}
              </option>
            ))}
          </select>
          <ChevronDown
            className="w-3.5 h-3.5"
            style={{
              position: 'absolute',
              right: 10,
              color: 'var(--text-faint)',
              pointerEvents: 'none',
            }}
          />
        </div>
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
              <p className="truncate" style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{profile?.name || roleLabel}</p>
              <p style={{ fontSize: 10, color: 'var(--text-faint)' }}>{tUi(selectedLanguage, 'app.level', { level: currentLevel })}</p>
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
            {tUi(selectedLanguage, 'app.logout')}
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
              <Tooltip content={tUi(selectedLanguage, 'app.logout')}>
                <Button isIconOnly aria-label={tUi(selectedLanguage, 'app.logout')} variant="light" size="sm" onPress={handleLogout}>
                  <LogOut className="w-4 h-4" />
                </Button>
              </Tooltip>
            </NavbarItem>
            <NavbarItem>
              <Tooltip content={tUi(selectedLanguage, 'app.roleTooltip', { role: roleLabel })}>
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
