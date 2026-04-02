import { useNavigate } from 'react-router-dom';
import {
  Card,
  CardBody,
  Button,
  Progress,
  Chip,
  CircularProgress,
  Tooltip,
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
  ChevronLeft,
  ChevronRight,
  CalendarRange,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import apiClient, { getApiErrorMessage } from '../lib/api';
import { getDailyProgress, type DailyProgressDay } from '../lib/progressService';
import { useProfileStore } from '../store/profileStore';
import { useGamificationStore } from '../store/gamificationStore';
import { useToast } from '../hooks/useToast';

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.07 } } };
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };
const HEATMAP_WEEKDAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
type HeatmapView = 'week' | 'month' | 'year';

function toIsoDate(date: Date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function monthStartOf(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function monthEndOf(date: Date) {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}

function weekStartOf(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() - date.getDay());
}

function weekEndOf(date: Date) {
  const start = weekStartOf(date);
  return new Date(start.getFullYear(), start.getMonth(), start.getDate() + 6);
}

function yearStartOf(date: Date) {
  return new Date(date.getFullYear(), 0, 1);
}

function yearEndOf(date: Date) {
  return new Date(date.getFullYear(), 11, 31);
}

function alignToPeriod(date: Date, view: HeatmapView) {
  if (view === 'week') return weekStartOf(date);
  if (view === 'year') return yearStartOf(date);
  return monthStartOf(date);
}

function shiftPeriod(date: Date, view: HeatmapView, delta: number) {
  if (view === 'week') {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate() + delta * 7);
  }
  if (view === 'year') {
    return new Date(date.getFullYear() + delta, 0, 1);
  }
  return new Date(date.getFullYear(), date.getMonth() + delta, 1);
}

function periodBounds(date: Date, view: HeatmapView) {
  const start = alignToPeriod(date, view);
  if (view === 'week') {
    return { start, end: weekEndOf(start) };
  }
  if (view === 'year') {
    return { start, end: yearEndOf(start) };
  }
  return { start, end: monthEndOf(start) };
}

function intensityLevel(score: number) {
  if (score <= 0) return 0;
  if (score < 0.25) return 1;
  if (score < 0.5) return 2;
  if (score < 0.75) return 3;
  return 4;
}

function intensityStyles(level: number): React.CSSProperties {
  if (level === 0) {
    return {
      background: 'var(--bg-4)',
      border: '1px solid var(--border-subtle)',
    };
  }
  if (level === 1) {
    return {
      background: 'color-mix(in srgb, var(--accent) 22%, var(--bg-2) 78%)',
      border: '1px solid color-mix(in srgb, var(--accent) 28%, var(--border-subtle) 72%)',
    };
  }
  if (level === 2) {
    return {
      background: 'color-mix(in srgb, var(--accent) 45%, var(--bg-2) 55%)',
      border: '1px solid color-mix(in srgb, var(--accent) 52%, var(--border-subtle) 48%)',
    };
  }
  if (level === 3) {
    return {
      background: 'color-mix(in srgb, var(--accent) 70%, var(--bg-1) 30%)',
      border: '1px solid color-mix(in srgb, var(--accent) 72%, white 28%)',
      boxShadow: '0 0 0 1px color-mix(in srgb, var(--accent) 34%, transparent) inset',
    };
  }
  return {
    background: 'var(--accent)',
    border: '1px solid color-mix(in srgb, var(--accent) 74%, white 26%)',
    boxShadow: '0 0 10px color-mix(in srgb, var(--accent) 55%, transparent)',
  };
}

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
  const [heatmapView, setHeatmapView] = useState<HeatmapView>('month');
  const [heatmapCursor, setHeatmapCursor] = useState(() => monthStartOf(new Date()));
  const [periodProgress, setPeriodProgress] = useState<Record<string, DailyProgressDay>>({});
  const [isHeatmapLoading, setIsHeatmapLoading] = useState(false);
  const [heatmapError, setHeatmapError] = useState<string | null>(null);
  const [selectedHeatmapDay, setSelectedHeatmapDay] = useState<string | null>(null);

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
          addToastRef.current('Home updated successfully.', 'success');
        }
      } catch (error) {
        if (active) {
          const message = `${getApiErrorMessage(error, 'Unable to load live home data.')} Showing local values.`;
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
  const today = useMemo(() => new Date(), []);
  const alignedHeatmapCursor = useMemo(() => alignToPeriod(heatmapCursor, heatmapView), [heatmapCursor, heatmapView]);
  const currentPeriodCursor = useMemo(() => alignToPeriod(today, heatmapView), [today, heatmapView]);
  const isCurrentPeriodView = toIsoDate(alignedHeatmapCursor) === toIsoDate(currentPeriodCursor);

  useEffect(() => {
    let active = true;

    async function loadHeatmap() {
      const { start: periodStart, end: periodEnd } = periodBounds(alignedHeatmapCursor, heatmapView);
      const todayDate = new Date();
      const diffMs = Math.max(0, todayDate.getTime() - periodStart.getTime());
      const diffDays = Math.ceil(diffMs / 86400000);
      const padding = heatmapView === 'year' ? 380 : 70;
      const lookbackDays = Math.max(padding, Math.min(1200, diffDays + padding));

      setIsHeatmapLoading(true);
      setHeatmapError(null);

      try {
        const days = await getDailyProgress(lookbackDays);
        if (!active) return;

        const startIso = toIsoDate(periodStart);
        const endIso = toIsoDate(periodEnd);
        const progressMap: Record<string, DailyProgressDay> = {};
        for (const day of days) {
          if (day.date >= startIso && day.date <= endIso) {
            progressMap[day.date] = day;
          }
        }
        setPeriodProgress(progressMap);

        const todayIso = toIsoDate(todayDate);
        const newestIso = Object.keys(progressMap).sort().at(-1) ?? null;
        setSelectedHeatmapDay((prev) => {
          if (prev && progressMap[prev]) return prev;
          if (progressMap[todayIso]) return todayIso;
          return newestIso ?? startIso;
        });
      } catch (error) {
        if (!active) return;
        const message = getApiErrorMessage(error, 'Unable to load period activity heatmap.');
        setHeatmapError(message);
      } finally {
        if (active) {
          setIsHeatmapLoading(false);
        }
      }
    }

    void loadHeatmap();
    return () => {
      active = false;
    };
  }, [alignedHeatmapCursor, heatmapView]);

  const heatmapPeriodLabel = useMemo(() => {
    if (heatmapView === 'week') {
      const end = weekEndOf(alignedHeatmapCursor);
      const startLabel = alignedHeatmapCursor.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      const endLabel = end.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
      return `${startLabel} - ${endLabel}`;
    }
    if (heatmapView === 'year') {
      return String(alignedHeatmapCursor.getFullYear());
    }
    return alignedHeatmapCursor.toLocaleString(undefined, { month: 'long', year: 'numeric' });
  }, [alignedHeatmapCursor, heatmapView]);

  const heatmapFocusLabel = heatmapView === 'week' ? 'Week Focus' : heatmapView === 'year' ? 'Year Focus' : 'Month Focus';

  const heatmapCells = useMemo(() => {
    const { start, end } = periodBounds(alignedHeatmapCursor, heatmapView);
    const gridStart = weekStartOf(start);
    const gridEnd = weekEndOf(end);

    const targetMinutes = Math.max(60, dailyTarget * 60);
    const cells: Array<{
      iso: string;
      date: Date;
      inRange: boolean;
      isFuture: boolean;
      minutes: number;
      lessons: number;
      quizzes: number;
      xp: number;
      score: number;
      intensity: number;
      focusPercent: number;
    }> = [];

    const todayIso = toIsoDate(new Date());
    const startIso = toIsoDate(start);
    const endIso = toIsoDate(end);

    for (let d = new Date(gridStart); d <= gridEnd; d.setDate(d.getDate() + 1)) {
      const cellDate = new Date(d);
      const iso = toIsoDate(cellDate);
      const day = periodProgress[iso];
      const minutes = day?.study_minutes ?? 0;
      const lessons = day?.lessons_completed ?? 0;
      const quizzes = day?.quizzes_taken ?? 0;
      const xp = day?.xp_earned ?? 0;

      const minPart = Math.min(1, minutes / targetMinutes);
      const lessonPart = Math.min(1, lessons / 2);
      const quizPart = Math.min(1, quizzes / 2);
      const xpPart = Math.min(1, xp / 80);
      const score = Number((0.5 * minPart + 0.25 * lessonPart + 0.15 * quizPart + 0.1 * xpPart).toFixed(3));
      const focusPercent =
        minutes === 0 && lessons === 0 && quizzes === 0
          ? 0
          : Math.round(Math.min(100, minPart * 70 + lessonPart * 20 + quizPart * 10));

      cells.push({
        iso,
        date: cellDate,
        inRange: iso >= startIso && iso <= endIso,
        isFuture: iso > todayIso,
        minutes,
        lessons,
        quizzes,
        xp,
        score,
        intensity: intensityLevel(score),
        focusPercent,
      });
    }

    return cells;
  }, [alignedHeatmapCursor, heatmapView, periodProgress, dailyTarget]);

  const periodMetrics = useMemo(() => {
    const inRangeCells = heatmapCells.filter((cell) => cell.inRange);
    const activeCells = inRangeCells.filter((cell) => cell.score > 0);
    const totalMinutes = activeCells.reduce((sum, cell) => sum + cell.minutes, 0);
    const avgFocus = activeCells.length
      ? Math.round(activeCells.reduce((sum, cell) => sum + cell.focusPercent, 0) / activeCells.length)
      : 0;
    const consistency = inRangeCells.length
      ? Math.round((activeCells.length / inRangeCells.length) * 100)
      : 0;
    const peakDay = activeCells.reduce<typeof activeCells[number] | null>(
      (best, cell) => (best && best.score >= cell.score ? best : cell),
      null
    );

    return {
      activeDays: activeCells.length,
      consistency,
      avgFocus,
      totalMinutes,
      peakDay,
    };
  }, [heatmapCells]);

  const selectedHeatmapCell = useMemo(
    () => heatmapCells.find((cell) => cell.iso === selectedHeatmapDay) ?? null,
    [heatmapCells, selectedHeatmapDay]
  );

  const levelProgress = useMemo(() => {
    const levelSpan = 500;
    const progressed = Math.max(0, levelSpan - xpForNextLevel);
    return Math.min(100, Math.round((progressed / levelSpan) * 100));
  }, [xpForNextLevel]);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="max-w-5xl mx-auto space-y-5 md:pt-4 lg:pt-6">
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
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Live home refresh failed. You are seeing local fallback values.</p>
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

      {/* Learning heatmap */}
      <motion.div variants={item}>
        <Card className="glass">
          <CardBody className="p-4 md:p-5 space-y-4">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <CalendarRange className="w-4 h-4" style={{ color: 'var(--accent)' }} />
                  <h2 className="ui-section-title">Learning Heatmap</h2>
                </div>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  Brighter days mean deeper learning activity and stronger focus.
                </p>
              </div>

              <div className="flex items-center gap-2 flex-wrap justify-end">
                <div className="flex items-center gap-1.5">
                  {(['week', 'month', 'year'] as HeatmapView[]).map((view) => (
                    <Button
                      key={view}
                      size="sm"
                      variant={heatmapView === view ? 'flat' : 'bordered'}
                      color={heatmapView === view ? 'secondary' : 'default'}
                      className="capitalize"
                      onPress={() => {
                        setHeatmapView(view);
                        setHeatmapCursor((prev) => alignToPeriod(prev, view));
                      }}
                    >
                      {view}
                    </Button>
                  ))}
                </div>
                <Button
                  isIconOnly
                  size="sm"
                  variant="flat"
                  onPress={() => setHeatmapCursor((prev) => shiftPeriod(prev, heatmapView, -1))}
                  aria-label="Previous period"
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <Chip size="sm" variant="flat" color="secondary" style={{ borderRadius: 'var(--r-pill)' }}>
                  {heatmapPeriodLabel}
                </Chip>
                <Button
                  isIconOnly
                  size="sm"
                  variant="flat"
                  isDisabled={isCurrentPeriodView}
                  onPress={() => setHeatmapCursor((prev) => shiftPeriod(prev, heatmapView, 1))}
                  aria-label="Next period"
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-[1.8fr_1fr] gap-4">
              <div className="space-y-2">
                <div className="grid grid-cols-7 gap-1.5">
                  {HEATMAP_WEEKDAY_LABELS.map((label) => (
                    <p
                      key={label}
                      className="text-[10px] text-center uppercase tracking-wide"
                      style={{ color: 'var(--text-faint)' }}
                    >
                      {label}
                    </p>
                  ))}
                </div>

                <div className={`grid grid-cols-7 gap-1.5 ${heatmapView === 'year' ? 'max-h-105 overflow-y-auto pr-1' : ''}`}>
                  {heatmapCells.map((cell) => {
                    const isSelected = selectedHeatmapDay === cell.iso;
                    const muted = !cell.inRange || cell.isFuture;
                    const tooltip = (
                      <div className="text-[11px] leading-tight">
                        <p className="font-semibold">{cell.date.toLocaleDateString()}</p>
                        <p>{cell.minutes} min study</p>
                        <p>{cell.lessons} lessons • {cell.quizzes} quizzes</p>
                        <p>Focus {cell.focusPercent}% • +{cell.xp} XP</p>
                      </div>
                    );
                    return (
                      <Tooltip key={cell.iso} content={tooltip} delay={0} closeDelay={0}>
                        <button
                          type="button"
                          onClick={() => cell.inRange && setSelectedHeatmapDay(cell.iso)}
                          className={`rounded-md text-[11px] font-medium transition-all ${heatmapView === 'year' ? 'h-6' : 'h-8'}`}
                          style={{
                            ...intensityStyles(muted ? 0 : cell.intensity),
                            color: muted ? 'var(--text-faint)' : 'var(--text-primary)',
                            opacity: muted ? 0.55 : 1,
                            outline: isSelected ? '2px solid var(--accent)' : 'none',
                            cursor: cell.inRange ? 'pointer' : 'default',
                          }}
                          disabled={!cell.inRange}
                        >
                          {cell.date.getDate()}
                        </button>
                      </Tooltip>
                    );
                  })}
                </div>

                {heatmapError ? (
                  <p className="text-xs" style={{ color: 'var(--red)' }}>{heatmapError}</p>
                ) : null}
                {isHeatmapLoading ? (
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Loading {heatmapView} activity…</p>
                ) : null}

                <div className="flex items-center gap-2 text-[10px]" style={{ color: 'var(--text-faint)' }}>
                  <span>Low</span>
                  {[0, 1, 2, 3, 4].map((level) => (
                    <span key={level} className="inline-block h-2.5 w-5 rounded-sm" style={intensityStyles(level)} />
                  ))}
                  <span>Peak</span>
                </div>
              </div>

              <div className="space-y-2.5">
                <div className="ui-soft-panel p-3 space-y-2">
                  <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>{heatmapFocusLabel}</p>
                  <p className="text-2xl font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>
                    {periodMetrics.avgFocus}%
                  </p>
                  <Progress
                    value={periodMetrics.avgFocus}
                    color="secondary"
                    size="sm"
                    classNames={{ track: 'bg-bg-5', indicator: 'bg-linear-to-r from-[var(--accent)] to-[#A89CF8]' }}
                  />
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    Estimated focus from study depth and completed learning actions.
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="ui-soft-panel p-2.5">
                    <p className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>Consistency</p>
                    <p className="text-lg font-semibold" style={{ fontFamily: 'var(--font-heading)' }}>{periodMetrics.consistency}%</p>
                    <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>{periodMetrics.activeDays} active days</p>
                  </div>
                  <div className="ui-soft-panel p-2.5">
                    <p className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>Study Time</p>
                    <p className="text-lg font-semibold" style={{ fontFamily: 'var(--font-heading)' }}>{Math.round(periodMetrics.totalMinutes / 60)}h</p>
                    <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>{periodMetrics.totalMinutes} minutes</p>
                  </div>
                </div>

                <div className="ui-soft-panel p-3 space-y-1.5">
                  <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>Selected Day</p>
                  <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                    {selectedHeatmapCell ? selectedHeatmapCell.date.toLocaleDateString() : 'No day selected'}
                  </p>
                  {selectedHeatmapCell ? (
                    <>
                      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        {selectedHeatmapCell.minutes} min • {selectedHeatmapCell.lessons} lessons • {selectedHeatmapCell.quizzes} quizzes
                      </p>
                      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        Focus {selectedHeatmapCell.focusPercent}% • +{selectedHeatmapCell.xp} XP
                      </p>
                      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        Intensity {Math.round(selectedHeatmapCell.score * 100)}%
                      </p>
                    </>
                  ) : (
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Activity details will appear here.</p>
                  )}
                </div>

                {periodMetrics.peakDay ? (
                  <p className="text-[11px]" style={{ color: 'var(--text-faint)' }}>
                    Top day: {periodMetrics.peakDay.date.toLocaleDateString()} with focus {periodMetrics.peakDay.focusPercent}%
                  </p>
                ) : null}
              </div>
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
                className="glass h-full w-full min-h-55 transition-all duration-300 hover:scale-[1.015] hover:-translate-y-0.5"
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
                  <p className="text-xs mb-4 line-clamp-2 min-h-10.5" style={{ color: 'var(--text-muted)', lineHeight: 1.5 }}>{s.description}</p>
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
              <CardBody className="p-4 h-full min-h-23 flex flex-col items-center justify-center text-center">
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
