import { useNavigate } from 'react-router-dom';
import {
  Card,
  CardBody,
  Button,
  Progress,
  Chip,
  CircularProgress,
} from '@heroui/react';
import { motion } from 'framer-motion';
import {
  Atom,
  FlaskConical,
  Dna,
  Sparkles,
  Flame,
  Zap,
  Target,
  BookOpen,
  BrainCircuit,
  Trophy,
  ArrowRight,
  Clock,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import apiClient, { getApiErrorMessage } from '../lib/api';
import { useProfileStore } from '../store/profileStore';
import { useGamificationStore } from '../store/gamificationStore';
import { useToast } from '../hooks/useToast';

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.07 } } };
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };

const subjectCards = [
  {
    key: 'physics',
    label: 'Physics',
    description: 'Mechanics, Thermodynamics, Optics, Modern Physics',
    icon: <Atom className="w-6 h-6" />,
    color: 'primary' as const,
    tone: 'blue' as const,
  },
  {
    key: 'chemistry',
    label: 'Chemistry',
    description: 'Organic, Inorganic, Physical Chemistry',
    icon: <FlaskConical className="w-6 h-6" />,
    color: 'success' as const,
    tone: 'green' as const,
  },
  {
    key: 'biology',
    label: 'Biology',
    description: 'Botany, Zoology, Genetics, Ecology',
    icon: <Dna className="w-6 h-6" />,
    color: 'secondary' as const,
    tone: 'purple' as const,
  },
];

export function DashboardPage() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const addToastRef = useRef(addToast);
  const profile = useProfileStore((s) => s.profile);
  const fallbackTotalXP = useGamificationStore((s) => s.totalXP);
  const fallbackCurrentLevel = useGamificationStore((s) => s.currentLevel);
  const fallbackXpForNextLevel = useGamificationStore((s) => s.xpForNextLevel);
  const fallbackCurrentStreak = useGamificationStore((s) => s.currentStreak);
  const fallbackTodayProgress = useGamificationStore((s) => s.todayProgress);
  const fallbackBadgesCount = useGamificationStore((s) => s.badges.length);

  const [summary, setSummary] = useState<{
    totalXP: number;
    currentLevel: number;
    xpForNextLevel: number;
    currentStreak: number;
    todayProgress: {
      xpEarned: number;
      lessonsCompleted: number;
      quizzesTaken: number;
      studyMinutes: number;
    };
    badgesCount: number;
  } | null>(null);
  const [summaryRequestKey, setSummaryRequestKey] = useState(0);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [isSummaryLoading, setIsSummaryLoading] = useState(true);

  useEffect(() => {
    addToastRef.current = addToast;
  }, [addToast]);

  useEffect(() => {
    let active = true;

    async function loadSummary() {
      setIsSummaryLoading(true);
      setSummaryError(null);
      try {
        const response = await apiClient.get('/api/dashboard/summary');
        const data = response.data;
        if (!active || !data?.success) return;

        setSummary({
          totalXP: data.gamification?.total_xp ?? 0,
          currentLevel: data.gamification?.current_level ?? 1,
          xpForNextLevel: data.gamification?.xp_to_next_level ?? 500,
          currentStreak: data.gamification?.current_streak ?? 0,
          todayProgress: {
            xpEarned: data.today?.xp_earned ?? 0,
            lessonsCompleted: data.today?.lessons_completed ?? 0,
            quizzesTaken: data.today?.quizzes_taken ?? 0,
            studyMinutes: data.today?.study_minutes ?? 0,
          },
          badgesCount: data.badges_count ?? 0,
        });
        if (summaryRequestKey > 0) {
          addToastRef.current('Dashboard updated successfully.', 'success');
        }
      } catch (error) {
        if (active) {
          const message = `${getApiErrorMessage(error, 'Unable to load live dashboard data.')} Showing local values.`;
          setSummaryError(message);
          addToastRef.current(message, 'error');
        }
      } finally {
        if (active) {
          setIsSummaryLoading(false);
        }
      }
    }

    void loadSummary();
    return () => {
      active = false;
    };
  }, [summaryRequestKey]);

  const totalXP = summary?.totalXP ?? fallbackTotalXP;
  const currentLevel = summary?.currentLevel ?? fallbackCurrentLevel;
  const xpForNextLevel = summary?.xpForNextLevel ?? fallbackXpForNextLevel;
  const currentStreak = summary?.currentStreak ?? fallbackCurrentStreak;
  const todayProgress = summary?.todayProgress ?? fallbackTodayProgress;
  const badgesCount = summary?.badgesCount ?? fallbackBadgesCount;

  const dailyTarget = profile?.dailyStudyTarget || 4;
  const studyHoursToday = todayProgress.studyMinutes / 60;
  const dailyPercent = Math.min((studyHoursToday / dailyTarget) * 100, 100);
  const levelProgress = useMemo(() => {
    const levelSpan = 500;
    const progressed = Math.max(0, levelSpan - xpForNextLevel);
    return Math.min(100, Math.round((progressed / levelSpan) * 100));
  }, [xpForNextLevel]);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="max-w-5xl mx-auto space-y-5">
      {/* Welcome banner */}
      <motion.div variants={item}>
        <Card className="glass overflow-hidden relative" style={{ background: 'linear-gradient(135deg, var(--bg-3) 0%, var(--accent-glow) 100%)', border: '1px solid var(--border-default)', borderRadius: 'var(--r-lg)' }}>
          <div className="absolute top-0 right-0 w-60 h-60 rounded-full blur-[60px] pointer-events-none" style={{ background: 'var(--accent-glow)' }} />
          <CardBody className="relative z-10" style={{ padding: '22px 26px' }}>
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Sparkles className="w-5 h-5" style={{ color: 'var(--accent)' }} />
                  <h2 className="text-xl font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>
                    {greeting}, {profile?.name?.split(' ')[0] || 'Student'}!
                  </h2>
                </div>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                  {currentStreak > 0
                    ? `You're on a ${currentStreak}-day streak! Keep it up! 🔥`
                    : "Start studying today to begin your streak!"}
                </p>
              </div>
              <div className="flex gap-2">
                <Chip size="md" variant="flat" startContent={<Zap className="w-3 h-3" />} style={{ background: 'var(--amber-soft)', color: 'var(--amber)', border: '1px solid var(--amber-border)', borderRadius: 'var(--r-pill)' }}>
                  Level {currentLevel} • {totalXP} XP
                </Chip>
                {currentStreak > 0 && (
                  <Chip size="md" variant="flat" startContent={<Flame className="w-3 h-3" />} style={{ background: 'var(--red-soft)', color: 'var(--red)', border: '1px solid var(--red-border)', borderRadius: 'var(--r-pill)' }}>
                    {currentStreak}d streak
                  </Chip>
                )}
              </div>
            </div>
          </CardBody>
        </Card>
      </motion.div>

      {summaryError && (
        <motion.div variants={item}>
          <Card className="glass" style={{ borderRadius: 'var(--r-md)' }}>
            <CardBody className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3" style={{ padding: 14 }}>
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Live dashboard refresh failed. You are seeing local fallback values.</p>
              <Button
                size="sm"
                variant="flat"
                color="secondary"
                isLoading={isSummaryLoading}
                onPress={() => setSummaryRequestKey((value) => value + 1)}
              >
                Retry
              </Button>
            </CardBody>
          </Card>
        </motion.div>
      )}

      {/* Stats row */}
      <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="glass" style={{ borderRadius: 'var(--r-md)' }}>
          <CardBody className="text-center" style={{ padding: 16 }}>
            <CircularProgress
              value={dailyPercent}
              color="success"
              size="lg"
              showValueLabel
              aria-label="Daily goal progress"
              classNames={{ value: 'text-xs font-bold' }}
            />
            <p className="mt-1.5" style={{ fontSize: 11, color: 'var(--text-muted)' }}>Daily Goal</p>
          </CardBody>
        </Card>
        <Card className="glass" style={{ borderRadius: 'var(--r-md)' }}>
          <CardBody className="text-center" style={{ padding: 16 }}>
            <p className="text-3xl font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>{todayProgress.lessonsCompleted}</p>
            <p className="mt-1.5" style={{ fontSize: 11, color: 'var(--text-muted)' }}>Lessons Today</p>
          </CardBody>
        </Card>
        <Card className="glass" style={{ borderRadius: 'var(--r-md)' }}>
          <CardBody className="text-center" style={{ padding: 16 }}>
            <p className="text-3xl font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--amber)' }}>{todayProgress.quizzesTaken}</p>
            <p className="mt-1.5" style={{ fontSize: 11, color: 'var(--text-muted)' }}>Quizzes Today</p>
          </CardBody>
        </Card>
        <Card className="glass" style={{ borderRadius: 'var(--r-md)' }}>
          <CardBody className="text-center" style={{ padding: 16 }}>
            <p className="text-3xl font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--green)' }}>+{todayProgress.xpEarned}</p>
            <p className="mt-1.5" style={{ fontSize: 11, color: 'var(--text-muted)' }}>XP Today</p>
          </CardBody>
        </Card>
      </motion.div>

      {/* Level progress */}
      <motion.div variants={item}>
        <Card className="glass">
          <CardBody className="p-4">
            <div className="flex items-center justify-between mb-2" style={{ fontSize: 12 }}>
              <div className="flex items-center gap-2">
                <Trophy className="w-4 h-4" style={{ color: 'var(--amber)' }} />
                <span className="text-sm font-medium" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>Level {currentLevel}</span>
              </div>
              <span className="text-xs" style={{ color: 'var(--text-faint)' }}>{xpForNextLevel} XP to Level {currentLevel + 1}</span>
            </div>
            <Progress
              value={levelProgress}
              color="secondary"
              size="sm"
              classNames={{ track: 'bg-bg-5', indicator: 'bg-linear-to-r from-[var(--accent)] to-[#A89CF8]' }}
            />
            <div className="flex justify-between text-xs mt-1.5" style={{ color: 'var(--text-faint)' }}>
              <span>{badgesCount} badges earned</span>
              <span>{totalXP} total XP</span>
            </div>
          </CardBody>
        </Card>
      </motion.div>

      {/* Subjects */}
      <motion.div variants={item}>
        <div className="flex items-center justify-between mb-3">
          <h2 className="ui-section-title">Subjects</h2>
          <Button
            size="sm"
            variant="light"
            color="secondary"
            endContent={<ArrowRight className="w-3 h-3" />}
            onPress={() => navigate('/books')}
          >
            NCERT Books
          </Button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {subjectCards.map((s) => (
            <motion.div key={s.key} variants={item} className="h-full">
              <Card
                className="glass h-full w-full min-h-[220px] transition-all duration-300 hover:scale-[1.015] hover:-translate-y-0.5"
                style={{
                  border: `1px solid var(--${s.tone}-border)`,
                  background: `linear-gradient(135deg, var(--bg-2) 0%, var(--${s.tone}-soft) 100%)`,
                }}
              >
                <CardBody className="p-5 h-full flex flex-col">
                  <div className={`ui-icon-badge ${s.key === 'physics' ? 'ui-icon-badge-blue' : s.key === 'chemistry' ? 'ui-icon-badge-green' : 'ui-icon-badge-purple'} mb-3`}>
                    {s.icon}
                  </div>
                  <h3 className="text-lg font-semibold mb-1.5" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>{s.label}</h3>
                  <p className="text-xs mb-4 line-clamp-2 min-h-[42px]" style={{ color: 'var(--text-muted)', lineHeight: 1.5 }}>{s.description}</p>
                  <div className="grid grid-cols-2 gap-2 mt-auto w-full">
                    <Button
                      size="sm"
                      className="w-full font-medium"
                      color={s.color}
                      variant="flat"
                      startContent={<BookOpen className="w-3 h-3" />}
                      onPress={() => navigate(`/subject/${s.key}`)}
                    >
                      Learn
                    </Button>
                    <Button
                      size="sm"
                      className="w-full border-border-default text-text-secondary hover:border-border-strong font-medium"
                      variant="bordered"
                      startContent={<BrainCircuit className="w-3 h-3" />}
                      onPress={() => navigate(`/subject/${s.key}/quiz`)}
                    >
                      Quiz
                    </Button>
                  </div>
                </CardBody>
              </Card>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Quick actions */}
      <motion.div variants={item}>
        <h2 className="ui-section-title mb-3">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'NCERT Books', icon: <BookOpen className="w-5 h-5" />, path: '/books', tone: 'green' },
            { label: 'Resources', icon: <Target className="w-5 h-5" />, path: '/resources', tone: 'blue' },
            { label: 'Study Plan', icon: <Clock className="w-5 h-5" />, path: '/study-plan', tone: 'amber' },
            { label: 'Achievements', icon: <Trophy className="w-5 h-5" />, path: '/achievements', tone: 'purple' },
          ].map((a) => (
            <Card
              key={a.path}
              isPressable
              onPress={() => navigate(a.path)}
              className="glass h-full transition-all duration-200 hover:scale-[1.015] hover:-translate-y-0.5"
              style={{ cursor: 'pointer' }}
            >
              <CardBody className="p-4 h-full min-h-[92px] flex flex-col items-center justify-center text-center">
                <div className={`ui-icon-badge mx-auto mb-2 ${a.tone === 'green' ? 'ui-icon-badge-green' : a.tone === 'blue' ? 'ui-icon-badge-blue' : a.tone === 'amber' ? 'ui-icon-badge-amber' : 'ui-icon-badge-purple'}`}>
                  {a.icon}
                </div>
                <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>{a.label}</p>
              </CardBody>
            </Card>
          ))}
        </div>
      </motion.div>
    </motion.div>
  );
}
