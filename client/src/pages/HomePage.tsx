import { useNavigate } from 'react-router-dom';
import {
  Card,
  CardBody,
  Button,
  Progress,
  Chip,
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
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import apiClient, { getApiErrorMessage } from '../lib/api';
import { getDailyProgress, type DailyProgressDay } from '../lib/progressService';
import { useProfileStore } from '../store/profileStore';
import { useGamificationStore } from '../store/gamificationStore';
import { useToast } from '../hooks/useToast';

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.07 } } };
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } };
const HEATMAP_GRID_COLUMNS = 7;
type HeatmapView = 'week' | 'month' | 'year';
type SubjectTone = 'blue' | 'green' | 'purple';
type NextBestAction = {
  key: string;
  title: string;
  description: string;
  cta_label: string;
  cta_route: string;
  accent?: string;
  action_kind?: string;
  priority?: number;
  metric_label?: string | null;
  metric_value?: string | null;
};

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
      background: 'color-mix(in srgb, var(--bg-5) 68%, var(--bg-2) 32%)',
      border: '1px solid var(--border-strong)',
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

function heatmapCellVisual(
  cell: { inRange: boolean; isFuture: boolean; intensity: number },
  isSelected: boolean
): React.CSSProperties {
  const outOfRange = !cell.inRange;
  const futureInRange = cell.inRange && cell.isFuture;

  const base = intensityStyles(outOfRange ? 0 : cell.intensity);
  const surfaceOverride = outOfRange
    ? {
      background: 'color-mix(in srgb, var(--bg-4) 86%, var(--bg-2) 14%)',
      border: '1px solid var(--border-default)',
    }
    : futureInRange
      ? {
        background: 'color-mix(in srgb, var(--bg-4) 82%, var(--bg-1) 18%)',
        border: '1px solid var(--border-strong)',
      }
      : {};

  return {
    ...base,
    ...surfaceOverride,
    color: outOfRange ? 'var(--text-muted)' : futureInRange ? 'var(--text-secondary)' : 'var(--text-primary)',
    opacity: outOfRange ? 0.72 : 1,
    outline: isSelected ? '2px solid var(--accent)' : 'none',
    cursor: cell.inRange ? 'pointer' : 'default',
  };
}

const subjectCards = [
  {
    key: 'physics',
    label: 'Physics',
    description: 'Mechanics, Thermodynamics, Optics, Modern Physics',
    icon: <Atom className="w-6 h-6" />,
    tone: 'blue' as SubjectTone,
  },
  {
    key: 'chemistry',
    label: 'Chemistry',
    description: 'Organic, Inorganic, Physical Chemistry',
    icon: <FlaskConical className="w-6 h-6" />,
    tone: 'green' as SubjectTone,
  },
  {
    key: 'biology',
    label: 'Biology',
    description: 'Botany, Zoology, Genetics, Ecology',
    icon: <Dna className="w-6 h-6" />,
    tone: 'purple' as SubjectTone,
  },
];

function subjectLearnButtonStyle(tone: SubjectTone): React.CSSProperties {
  return {
    background: `linear-gradient(135deg, var(--${tone}) 0%, color-mix(in srgb, var(--${tone}) 72%, var(--accent) 28%) 100%)`,
    borderColor: `color-mix(in srgb, var(--${tone}) 70%, white 30%)`,
    color: '#ffffff',
  };
}

function subjectQuizButtonStyle(tone: SubjectTone): React.CSSProperties {
  return {
    background: `color-mix(in srgb, var(--${tone}-soft) 42%, var(--bg-2) 58%)`,
    borderColor: `color-mix(in srgb, var(--${tone}) 34%, var(--border-default) 66%)`,
    color: `var(--${tone})`,
  };
}

function nextActionAccentColor(accent?: string) {
  if (accent === 'purple') return 'var(--purple)';
  if (accent === 'amber') return 'var(--amber)';
  if (accent === 'green') return 'var(--green)';
  if (accent === 'blue') return 'var(--blue)';
  return 'var(--accent)';
}

function nextActionIcon(action: NextBestAction) {
  const color = nextActionAccentColor(action.accent);
  if (action.action_kind === 'planning') {
    return <Target className="w-4 h-4" style={{ color }} />;
  }
  if (action.action_kind === 'revision') {
    return <BrainCircuit className="w-4 h-4" style={{ color }} />;
  }
  return <BookOpen className="w-4 h-4" style={{ color }} />;
}

export function HomePage() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const addToastRef = useRef(addToast);
  const heatmapCellRefs = useRef<Record<string, HTMLButtonElement | null>>({});
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
  const [nextActions, setNextActions] = useState<NextBestAction[]>([]);
  const [isNextActionsLoading, setIsNextActionsLoading] = useState(true);
  const [nextActionsError, setNextActionsError] = useState<string | null>(null);
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

  useEffect(() => {
    let active = true;

    async function loadNextActions() {
      setIsNextActionsLoading(true);
      setNextActionsError(null);
      try {
        const response = await apiClient.get('/api/dashboard/next-actions');
        const data = response.data;
        if (!active || !data?.success) return;

        const actions = Array.isArray(data.actions) ? data.actions : [];
        setNextActions(actions.slice(0, 3));
      } catch (error) {
        if (!active) return;
        setNextActionsError(getApiErrorMessage(error, 'Unable to personalize next actions right now.'));
        setNextActions([]);
      } finally {
        if (active) {
          setIsNextActionsLoading(false);
        }
      }
    }

    void loadNextActions();
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
  const fallbackNextActions = useMemo<NextBestAction[]>(() => [
    {
      key: 'continue_learning',
      title: 'Continue Learning',
      description: 'Resume your latest chapter with one click.',
      cta_label: 'Resume Chapter',
      cta_route: '/books',
      accent: 'accent',
      action_kind: 'learning',
    },
    {
      key: 'smart_revision',
      title: 'Smart Revision',
      description: 'Take a short weak-area quiz to improve consistency.',
      cta_label: 'Revise 15 Minutes',
      cta_route: '/study-plan',
      accent: 'purple',
      action_kind: 'revision',
    },
    {
      key: 'plan_ahead',
      title: 'Plan Ahead',
      description: 'Set your next study block and keep your streak safe.',
      cta_label: 'Open Study Plan',
      cta_route: '/study-plan',
      accent: 'amber',
      action_kind: 'planning',
    },
  ], []);
  const renderedNextActions = nextActions.length ? nextActions : fallbackNextActions;
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
      const padding = heatmapView === 'year' ? 31 : 21;
      const lookbackDays = Math.max(30, Math.min(365, diffDays + padding));

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
        const sortedKeys = Object.keys(progressMap).sort();
        const newestIso = sortedKeys.length > 0 ? sortedKeys[sortedKeys.length - 1] : null;
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

  const heatmapCellByIso = useMemo(() => {
    const map: Record<string, (typeof heatmapCells)[number]> = {};
    for (const cell of heatmapCells) {
      map[cell.iso] = cell;
    }
    return map;
  }, [heatmapCells]);

  function handleHeatmapCellKeyDown(iso: string, event: KeyboardEvent<HTMLButtonElement>) {
    const key = event.key;
    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(key)) {
      return;
    }

    event.preventDefault();

    const currentIndex = heatmapCells.findIndex((cell) => cell.iso === iso);
    if (currentIndex < 0) return;

    const step =
      key === 'ArrowLeft'
        ? -1
        : key === 'ArrowRight'
          ? 1
          : key === 'ArrowUp'
            ? -HEATMAP_GRID_COLUMNS
            : HEATMAP_GRID_COLUMNS;

    let nextIndex = currentIndex + step;
    while (nextIndex >= 0 && nextIndex < heatmapCells.length) {
      const candidate = heatmapCells[nextIndex];
      if (candidate.inRange && !candidate.isFuture) {
        setSelectedHeatmapDay(candidate.iso);
        requestAnimationFrame(() => {
          heatmapCellRefs.current[candidate.iso]?.focus();
        });
        return;
      }
      nextIndex += step;
    }
  }

  const levelProgress = useMemo(() => {
    const levelSpan = 500;
    const progressed = Math.max(0, levelSpan - xpForNextLevel);
    return Math.min(100, Math.round((progressed / levelSpan) * 100));
  }, [xpForNextLevel]);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  const dailyCompletionPercent = Math.max(0, Math.min(100, Math.round(dailyPercent)));
  const todayIsoNow = toIsoDate(new Date());

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="home-dashboard mx-auto w-full max-w-7xl space-y-3 md:space-y-4">
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

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 items-start">
        <motion.div variants={item} className="xl:col-span-8 space-y-3">
          <Card
            className="glass overflow-hidden relative"
            style={{
              background: 'linear-gradient(135deg, var(--bg-3) 0%, var(--accent-glow) 100%)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--r-lg)',
            }}
          >
            <div className="absolute top-[-10%] right-[-4%] w-64 h-64 rounded-full blur-[70px] pointer-events-none" style={{ background: 'var(--accent-glow)' }} />
            <CardBody className="relative z-10" style={{ padding: '24px 26px' }}>
              <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5" style={{ color: 'var(--accent)' }} />
                    <h1 className="text-2xl font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>
                      {greeting}, {profile?.name?.split(' ')[0] || 'Student'}
                    </h1>
                  </div>
                  <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                    {currentStreak > 0
                      ? `You are on a ${currentStreak}-day streak. Keep your momentum alive today.`
                      : 'Start a focused session now and begin your streak.'}
                  </p>
                </div>

                <div className="flex items-center gap-2 flex-wrap lg:justify-end min-w-64 w-full sm:w-auto">
                  <Chip
                    size="md"
                    variant="flat"
                    startContent={<Zap className="w-3 h-3" />}
                    style={{ background: 'var(--amber-soft)', color: 'var(--amber)', border: '1px solid var(--amber-border)', borderRadius: 'var(--r-pill)' }}
                  >
                    Level {currentLevel} • {totalXP} XP
                  </Chip>
                  {currentStreak > 0 && (
                    <Chip
                      size="md"
                      variant="flat"
                      startContent={<Flame className="w-3 h-3" />}
                      style={{ background: 'var(--red-soft)', color: 'var(--red)', border: '1px solid var(--red-border)', borderRadius: 'var(--r-pill)' }}
                    >
                      {currentStreak}d streak
                    </Chip>
                  )}
                </div>
              </div>
            </CardBody>
          </Card>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
            <Card
              className="glass ui-card-hover"
              style={{
                borderRadius: 'var(--r-md)',
                border: '1px solid var(--border-subtle)',
                boxShadow: '0 10px 24px rgba(0,0,0,0.04)',
              }}
            >
              <CardBody className="p-2.5 md:p-3">
                <p className="text-[10px] uppercase tracking-wide font-medium" style={{ color: 'var(--text-muted)' }}>XP Today</p>
                <div className="mt-1 flex items-end justify-between gap-1.5">
                  <p className="text-xl font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--green)' }}>+{todayProgress.xpEarned}</p>
                  <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                    {Math.min(100, Math.round((todayProgress.xpEarned / Math.max(40, dailyTarget * 20)) * 100))}%
                  </span>
                </div>
                <div className="mt-1.5 h-1 rounded-full" style={{ background: 'var(--bg-4)' }}>
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.min(100, Math.round((todayProgress.xpEarned / Math.max(40, dailyTarget * 20)) * 100))}%`,
                      background: 'linear-gradient(90deg, var(--green) 0%, color-mix(in srgb, var(--green) 62%, white 38%) 100%)',
                    }}
                  />
                </div>
              </CardBody>
            </Card>

            <Card
              className="glass ui-card-hover"
              style={{
                borderRadius: 'var(--r-md)',
                border: '1px solid var(--border-subtle)',
                boxShadow: '0 10px 24px rgba(0,0,0,0.04)',
              }}
            >
              <CardBody className="p-2.5 md:p-3">
                <p className="text-[10px] uppercase tracking-wide font-medium" style={{ color: 'var(--text-muted)' }}>Active Days</p>
                <p className="text-xl font-semibold mt-1" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>{periodMetrics.activeDays}</p>
                <div className="mt-1.5 flex items-center gap-1">
                  {Array.from({ length: 7 }).map((_, idx) => {
                    const filled = idx < Math.min(7, periodMetrics.activeDays);
                    return (
                      <span
                        key={`active-day-dot-${idx}`}
                        className="inline-block h-1.5 w-1.5 rounded-full"
                        style={{
                          background: filled ? 'var(--accent)' : 'var(--bg-4)',
                          boxShadow: filled ? '0 0 0 1px color-mix(in srgb, var(--accent) 28%, transparent)' : 'none',
                        }}
                      />
                    );
                  })}
                </div>
              </CardBody>
            </Card>

            <Card
              className="glass ui-card-hover"
              style={{
                borderRadius: 'var(--r-md)',
                border: '1px solid var(--border-subtle)',
                boxShadow: '0 10px 24px rgba(0,0,0,0.04)',
              }}
            >
              <CardBody className="p-2.5 md:p-3">
                <p className="text-[10px] uppercase tracking-wide font-medium" style={{ color: 'var(--text-muted)' }}>Avg Focus</p>
                <div className="mt-1 flex items-end justify-between gap-1.5">
                  <p className="text-xl font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--amber)' }}>{periodMetrics.avgFocus}%</p>
                  <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>focus</span>
                </div>
                <div className="mt-1.5 flex items-center gap-0.5">
                  {Array.from({ length: 10 }).map((_, idx) => {
                    const threshold = (idx + 1) * 10;
                    const filled = periodMetrics.avgFocus >= threshold;
                    return (
                      <span
                        key={`focus-meter-${idx}`}
                        className="inline-block h-1 flex-1 rounded-sm"
                        style={{
                          background: filled ? 'var(--amber)' : 'var(--bg-4)',
                          opacity: filled ? 1 : 0.85,
                        }}
                      />
                    );
                  })}
                </div>
              </CardBody>
            </Card>

            <Card
              className="glass ui-card-hover"
              style={{
                borderRadius: 'var(--r-md)',
                border: '1px solid var(--border-subtle)',
                boxShadow: '0 10px 24px rgba(0,0,0,0.04)',
              }}
            >
              <CardBody className="p-2.5 md:p-3">
                <p className="text-[10px] uppercase tracking-wide font-medium" style={{ color: 'var(--text-muted)' }}>Badges</p>
                <p className="text-xl font-semibold mt-1" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>{badgesCount}</p>
                <div className="mt-1.5 flex items-center gap-1">
                  {Array.from({ length: 4 }).map((_, idx) => {
                    const earned = idx < Math.min(4, badgesCount);
                    return (
                      <span
                        key={`badge-preview-${idx}`}
                        className="inline-flex items-center justify-center h-4 w-4 rounded-full"
                        style={{
                          background: earned ? 'var(--amber-soft)' : 'var(--bg-4)',
                          color: earned ? 'var(--amber)' : 'var(--text-faint)',
                          border: `1px solid ${earned ? 'var(--amber-border)' : 'var(--border-subtle)'}`,
                        }}
                      >
                        <Trophy className="w-2.5 h-2.5" />
                      </span>
                    );
                  })}
                </div>
              </CardBody>
            </Card>
          </div>
        </motion.div>

        <motion.div variants={item} className="xl:col-span-4">
          <Card className="glass" style={{ borderRadius: 'var(--r-lg)' }}>
            <CardBody className="p-3 md:p-3.5 flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>Daily Target</p>
                <Chip size="sm" variant="flat" color="secondary" style={{ borderRadius: 'var(--r-pill)' }}>
                  {dailyTarget}h goal
                </Chip>
              </div>

              <div className="grid grid-cols-[64px_1fr] gap-3 items-center">
                <div
                  className="relative h-16 w-16 rounded-full"
                  style={{
                    background: `conic-gradient(var(--green) ${dailyCompletionPercent}%, var(--bg-4) ${dailyCompletionPercent}% 100%)`,
                  }}
                >
                  <div
                    className="absolute rounded-full flex items-center justify-center"
                    style={{ background: 'var(--bg-1)', inset: 5 }}
                  >
                    <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-heading)' }}>
                      {dailyCompletionPercent}%
                    </span>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <div>
                    <p className="text-xl font-semibold leading-none" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>
                      {studyHoursToday.toFixed(1)}h
                    </p>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Studied today</p>
                    <p className="text-xs" style={{ color: 'var(--text-faint)' }}>{Math.max(0, dailyTarget - studyHoursToday).toFixed(1)}h remaining</p>
                  </div>

                  <div className="space-y-1">
                    <div className="h-1.5 rounded-full" style={{ background: 'var(--bg-4)' }}>
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${dailyCompletionPercent}%`,
                          background: 'linear-gradient(90deg, var(--green) 0%, color-mix(in srgb, var(--green) 70%, white 30%) 100%)',
                        }}
                      />
                    </div>
                    <div className="flex justify-between text-[10px]" style={{ color: 'var(--text-faint)' }}>
                      <span>0h</span>
                      <span>{(dailyTarget / 2).toFixed(dailyTarget % 2 === 0 ? 0 : 1)}h</span>
                      <span>{dailyTarget}h</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-1.5">
                <div className="ui-soft-panel p-2 space-y-1">
                  <div className="flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5" style={{ color: 'var(--accent)' }} />
                    <p className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>Lessons</p>
                  </div>
                  <p className="text-sm font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>{todayProgress.lessonsCompleted}</p>
                </div>

                <div className="ui-soft-panel p-2 space-y-1">
                  <div className="flex items-center gap-1.5">
                    <BrainCircuit className="w-3.5 h-3.5" style={{ color: 'var(--purple)' }} />
                    <p className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>Quizzes</p>
                  </div>
                  <p className="text-sm font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>{todayProgress.quizzesTaken}</p>
                </div>
              </div>
            </CardBody>
          </Card>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 items-start">
        <motion.div variants={item} className="xl:col-span-8 space-y-4">
          <Card className="glass h-full" style={{ borderRadius: 'var(--r-lg)' }}>
            <CardBody className="p-4 md:p-5">
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
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {subjectCards.map((s) => (
                  <motion.div key={s.key} variants={item} className="h-full">
                    <Card
                      className="h-full w-full min-h-52 ui-card-hover"
                      style={{
                        border: '1px solid var(--border-default)',
                        background: `linear-gradient(180deg, color-mix(in srgb, var(--bg-2) 93%, var(--${s.tone}-soft) 7%) 0%, var(--bg-2) 100%)`,
                      }}
                    >
                      <CardBody className="p-4 h-full flex flex-col">
                        <span
                          className="h-1.5 w-12 rounded-full mb-2"
                          style={{ background: `var(--${s.tone})`, opacity: 0.55 }}
                          aria-hidden="true"
                        />
                        <div className={`ui-icon-badge ${s.key === 'physics' ? 'ui-icon-badge-blue' : s.key === 'chemistry' ? 'ui-icon-badge-green' : 'ui-icon-badge-purple'} mb-2.5`}>
                          {s.icon}
                        </div>
                        <h3 className="text-lg font-semibold mb-1" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>{s.label}</h3>
                        <p className="text-xs mb-3 line-clamp-2 min-h-10" style={{ color: 'var(--text-muted)', lineHeight: 1.5 }}>{s.description}</p>
                        <div className="grid grid-cols-2 gap-2 mt-auto w-full">
                          <Button
                            size="sm"
                            className="w-full font-medium ui-action-subject"
                            variant="solid"
                            startContent={<BookOpen className="w-3 h-3" />}
                            style={subjectLearnButtonStyle(s.tone)}
                            onPress={() => navigate(`/subject/${s.key}`)}
                          >
                            Learn
                          </Button>
                          <Button
                            size="sm"
                            className="w-full font-medium ui-action-subject-secondary"
                            variant="bordered"
                            startContent={<BrainCircuit className="w-3 h-3" />}
                            style={subjectQuizButtonStyle(s.tone)}
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
            </CardBody>
          </Card>

          <Card className="glass" style={{ borderRadius: 'var(--r-md)' }}>
            <CardBody className="p-4 space-y-3">
              <h2 className="ui-section-title">Quick References</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {[
                  { label: 'NCERT Books', icon: <BookOpen className="w-4 h-4" />, path: '/books' },
                  { label: 'Resources', icon: <Target className="w-4 h-4" />, path: '/resources' },
                  { label: 'Study Plan', icon: <Clock className="w-4 h-4" />, path: '/study-plan' },
                  { label: 'Achievements', icon: <Trophy className="w-4 h-4" />, path: '/achievements' },
                ].map((a) => (
                  <Button
                    key={`quick-ref-${a.path}`}
                    variant="bordered"
                    className="justify-center md:justify-start ui-action-secondary"
                    onPress={() => navigate(a.path)}
                    startContent={a.icon}
                  >
                    {a.label}
                  </Button>
                ))}
              </div>
            </CardBody>
          </Card>
        </motion.div>

        <motion.div variants={item} className="xl:col-span-4 space-y-4">
          <Card className="glass" style={{ borderRadius: 'var(--r-md)' }}>
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
                aria-label="Level progress"
                classNames={{ track: 'bg-bg-5', indicator: 'bg-linear-to-r from-[var(--accent)] to-[#A89CF8]' }}
              />
              <div className="flex justify-between text-xs mt-1.5" style={{ color: 'var(--text-faint)' }}>
                <span>{badgesCount} badges earned</span>
                <span>{totalXP} total XP</span>
              </div>
            </CardBody>
          </Card>

          <div className="space-y-2">
            <div className="flex justify-center xl:justify-start">
              <div className="ui-soft-panel home-calendar-panel p-2.5 md:p-3 space-y-2.5 w-full">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-1">
                    {(['week', 'month', 'year'] as HeatmapView[]).map((view) => (
                      <Button
                        key={view}
                        size="sm"
                        variant={heatmapView === view ? 'flat' : 'light'}
                        color={heatmapView === view ? 'secondary' : 'default'}
                        className="capitalize min-w-14"
                        onPress={() => {
                          setHeatmapView(view);
                          setHeatmapCursor((prev) => alignToPeriod(prev, view));
                        }}
                      >
                        {view}
                      </Button>
                    ))}
                  </div>

                  <div className="flex items-center gap-1">
                    <Button
                      isIconOnly
                      size="sm"
                      variant="light"
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
                      variant="light"
                      isDisabled={isCurrentPeriodView}
                      onPress={() => setHeatmapCursor((prev) => shiftPeriod(prev, heatmapView, 1))}
                      aria-label="Next period"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
                    Day {selectedHeatmapCell?.date.getDate() ?? '-'}
                  </p>
                  <p className="text-[11px]" style={{ color: 'var(--text-faint)' }}>
                    {periodMetrics.activeDays} active
                  </p>
                </div>

                <div className="grid grid-cols-7 gap-1">
                  {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((label, idx) => (
                    <p
                      key={`hm-weekday-right-${label}-${idx}`}
                      className="text-[10px] text-center font-medium"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      {label}
                    </p>
                  ))}
                </div>

                {heatmapView === 'year' ? (
                  <div className="max-h-56 overflow-y-auto pr-1 space-y-2">
                    {Array.from({ length: 12 }).map((_, monthIndex) => {
                      const monthDate = new Date(alignedHeatmapCursor.getFullYear(), monthIndex, 1);
                      const monthLabel = monthDate.toLocaleString(undefined, { month: 'short' });
                      const monthStart = new Date(alignedHeatmapCursor.getFullYear(), monthIndex, 1);
                      const monthEnd = monthEndOf(monthStart);
                      const blockStart = weekStartOf(monthStart);
                      const blockEnd = weekEndOf(monthEnd);
                      const monthStartIso = toIsoDate(monthStart);
                      const monthEndIso = toIsoDate(monthEnd);

                      const monthCells: Array<(typeof heatmapCells)[number]> = [];
                      for (let d = new Date(blockStart); d <= blockEnd; d.setDate(d.getDate() + 1)) {
                        const cellDate = new Date(d);
                        const iso = toIsoDate(cellDate);
                        const existing = heatmapCellByIso[iso];
                        if (existing) {
                          monthCells.push(existing);
                        } else {
                          monthCells.push({
                            iso,
                            date: cellDate,
                            inRange: iso >= monthStartIso && iso <= monthEndIso,
                            isFuture: iso > todayIsoNow,
                            minutes: 0,
                            lessons: 0,
                            quizzes: 0,
                            xp: 0,
                            score: 0,
                            intensity: 0,
                            focusPercent: 0,
                          });
                        }
                      }

                      return (
                        <div key={`year-month-right-${monthIndex}`} className="space-y-1">
                          <p className="text-[10px] font-medium uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>
                            {monthLabel}
                          </p>
                          <div className="grid grid-cols-7 gap-1">
                            {monthCells.map((cell) => {
                              const isSelected = selectedHeatmapDay === cell.iso;
                              return (
                                <button
                                  key={`year-cell-right-${cell.iso}`}
                                  type="button"
                                  onClick={() => cell.inRange && setSelectedHeatmapDay(cell.iso)}
                                  onKeyDown={(event) => handleHeatmapCellKeyDown(cell.iso, event)}
                                  ref={(node) => {
                                    heatmapCellRefs.current[cell.iso] = node;
                                  }}
                                  className="font-medium transition-all h-5 w-5 text-[10px] rounded-md"
                                  style={heatmapCellVisual({
                                    inRange: cell.inRange,
                                    isFuture: cell.isFuture,
                                    intensity: cell.intensity,
                                  }, isSelected)}
                                  disabled={!cell.inRange}
                                  aria-label={`Heatmap ${cell.date.toLocaleDateString()}`}
                                  title={`${cell.date.toLocaleDateString()} • ${cell.minutes}m • ${cell.lessons} lessons • ${cell.quizzes} quizzes • Focus ${cell.focusPercent}% • +${cell.xp} XP`}
                                >
                                  {cell.date.getDate()}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="grid grid-cols-7 gap-1">
                    {heatmapCells.map((cell) => {
                      const isSelected = selectedHeatmapDay === cell.iso;
                      return (
                        <button
                          key={`cell-right-${cell.iso}`}
                          type="button"
                          onClick={() => cell.inRange && setSelectedHeatmapDay(cell.iso)}
                          onKeyDown={(event) => handleHeatmapCellKeyDown(cell.iso, event)}
                          ref={(node) => {
                            heatmapCellRefs.current[cell.iso] = node;
                          }}
                          className="font-medium transition-all h-7 w-7 md:h-8 md:w-8 text-[11px] rounded-lg"
                          style={heatmapCellVisual({
                            inRange: cell.inRange,
                            isFuture: cell.isFuture,
                            intensity: cell.intensity,
                          }, isSelected)}
                          disabled={!cell.inRange}
                          aria-label={`Heatmap ${cell.date.toLocaleDateString()}`}
                          title={`${cell.date.toLocaleDateString()} • ${cell.minutes}m • ${cell.lessons} lessons • ${cell.quizzes} quizzes • Focus ${cell.focusPercent}% • +${cell.xp} XP`}
                        >
                          {cell.date.getDate()}
                        </button>
                      );
                    })}
                  </div>
                )}

                <div className="flex items-center justify-center gap-1.5" aria-hidden="true">
                  {[0, 1, 2, 3, 4].map((level) => (
                    <span key={`legend-right-${level}`} className="inline-block h-1.5 w-5 rounded-sm" style={intensityStyles(level)} />
                  ))}
                </div>
              </div>
            </div>

            {heatmapError ? (
              <p className="text-xs text-center" style={{ color: 'var(--red)' }}>{heatmapError}</p>
            ) : null}
            {isHeatmapLoading ? (
              <p className="text-xs text-center" style={{ color: 'var(--text-muted)' }}>Loading {heatmapView} activity...</p>
            ) : null}
          </div>
        </motion.div>
      </div>

      <motion.div variants={item}>
        <Card className="glass" style={{ borderRadius: 'var(--r-lg)' }}>
          <CardBody className="p-4 md:p-5 space-y-3.5">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <h2 className="ui-section-title">Next Best Actions</h2>
              <Chip size="sm" variant="flat" style={{ borderRadius: 'var(--r-pill)', background: 'var(--accent-soft)', border: '1px solid var(--accent-border)', color: 'var(--accent)' }}>
                Personalized for today
              </Chip>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {renderedNextActions.map((action, idx) => (
                <Card key={action.key || `${action.title}-${idx}`} className="ui-soft-panel ui-card-hover" style={{ borderRadius: 'var(--r-md)' }}>
                  <CardBody className="p-3.5 space-y-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {nextActionIcon(action)}
                        <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{action.title}</p>
                      </div>
                      {action.metric_label && action.metric_value ? (
                        <span
                          className="text-[10px] px-2 py-0.5 rounded-full"
                          style={{ color: 'var(--text-faint)', background: 'var(--bg-3)', border: '1px solid var(--border-subtle)' }}
                        >
                          {action.metric_label}: {action.metric_value}
                        </span>
                      ) : null}
                    </div>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{action.description}</p>
                    <Button
                      size="sm"
                      variant={idx === 0 ? 'solid' : 'bordered'}
                      className={`${idx === 0 ? 'ui-action-primary' : 'ui-action-secondary'} w-full justify-center`}
                      onPress={() => navigate(action.cta_route || '/learn-sessions')}
                      endContent={<ArrowRight className="w-3.5 h-3.5" />}
                    >
                      {action.cta_label || 'Open'}
                    </Button>
                  </CardBody>
                </Card>
              ))}
            </div>

            {isNextActionsLoading ? (
              <p className="text-xs text-center" style={{ color: 'var(--text-muted)' }}>Personalizing actions...</p>
            ) : null}
            {nextActionsError ? (
              <p className="text-xs text-center" style={{ color: 'var(--text-faint)' }}>{nextActionsError}</p>
            ) : null}
          </CardBody>
        </Card>
      </motion.div>

    </motion.div>
  );
}
