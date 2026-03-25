import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Badge {
  id: string;
  name: string;
  description: string;
  icon: string;
  earnedAt?: string;
}

export interface DailyProgress {
  date: string;
  xpEarned: number;
  lessonsCompleted: number;
  quizzesTaken: number;
  studyMinutes: number;
}

interface GamificationState {
  // XP & Level
  totalXP: number;
  currentLevel: number;
  xpForNextLevel: number;

  // Streaks
  currentStreak: number;
  longestStreak: number;
  lastStudyDate: string | null;

  // Badges
  badges: Badge[];

  // Daily tracking
  dailyHistory: DailyProgress[];
  todayProgress: DailyProgress;

  // Badge helpers
  hadPerfectQuiz: boolean;
  subjectsStudiedToday: string[];

  // Hydration
  _hasHydrated: boolean;
  setHasHydrated: (v: boolean) => void;

  // Actions
  addXP: (amount: number) => void;
  recordStudySession: (minutes: number) => void;
  recordLessonComplete: () => void;
  recordQuizComplete: (score: number, total: number) => void;
  recordSubjectStudied: (subject: string) => void;
  checkAndAwardBadges: () => void;
  updateStreak: () => void;
}

const XP_PER_LEVEL = 500;
const STREAK_XP_BONUS = 50;

function getToday(): string {
  return new Date().toISOString().split('T')[0];
}

function getEmptyDay(date: string): DailyProgress {
  return { date, xpEarned: 0, lessonsCompleted: 0, quizzesTaken: 0, studyMinutes: 0 };
}

function calculateLevel(xp: number): { level: number; xpForNext: number } {
  const level = Math.floor(xp / XP_PER_LEVEL) + 1;
  const xpForNext = level * XP_PER_LEVEL - xp;
  return { level, xpForNext };
}

const ALL_BADGES: Badge[] = [
  { id: 'first_lesson', name: 'First Step', description: 'Complete your first lesson', icon: '🎯' },
  { id: 'streak_3', name: 'On Fire', description: '3-day study streak', icon: '🔥' },
  { id: 'streak_7', name: 'Week Warrior', description: '7-day study streak', icon: '⚡' },
  { id: 'streak_30', name: 'Monthly Master', description: '30-day study streak', icon: '🏆' },
  { id: 'quiz_5', name: 'Quiz Lover', description: 'Take 5 quizzes', icon: '📝' },
  { id: 'quiz_perfect', name: 'Perfect Score', description: 'Score 100% on a quiz', icon: '💯' },
  { id: 'xp_1000', name: 'Rising Star', description: 'Earn 1,000 XP', icon: '⭐' },
  { id: 'xp_5000', name: 'NEET Grinder', description: 'Earn 5,000 XP', icon: '💎' },
  { id: 'xp_10000', name: 'NEET Legend', description: 'Earn 10,000 XP', icon: '👑' },
  { id: 'study_60', name: 'Deep Focus', description: 'Study for 60 minutes in one day', icon: '🧠' },
  { id: 'all_subjects', name: 'Well Rounded', description: 'Study all 3 subjects in one day', icon: '🌟' },
  { id: 'level_5', name: 'Scholar', description: 'Reach Level 5', icon: '📚' },
  { id: 'level_10', name: 'Expert', description: 'Reach Level 10', icon: '🎓' },
];

export const useGamificationStore = create<GamificationState>()(
  persist(
    (set, get) => ({
      totalXP: 0,
      currentLevel: 1,
      xpForNextLevel: XP_PER_LEVEL,
      currentStreak: 0,
      longestStreak: 0,
      lastStudyDate: null,
      badges: [],
      dailyHistory: [],
      todayProgress: getEmptyDay(getToday()),
      hadPerfectQuiz: false,
      subjectsStudiedToday: [],
      _hasHydrated: false,
      setHasHydrated: (v) => set({ _hasHydrated: v }),

      addXP: (amount: number) => {
        set((state) => {
          const newXP = state.totalXP + amount;
          const { level, xpForNext } = calculateLevel(newXP);
          const today = getToday();
          const todayProgress =
            state.todayProgress.date === today
              ? { ...state.todayProgress, xpEarned: state.todayProgress.xpEarned + amount }
              : { ...getEmptyDay(today), xpEarned: amount };
          return { totalXP: newXP, currentLevel: level, xpForNextLevel: xpForNext, todayProgress };
        });
      },

      recordStudySession: (minutes: number) => {
        const { addXP, updateStreak, checkAndAwardBadges } = get();
        const xp = Math.round(minutes * 2); // 2 XP per minute
        addXP(xp);
        set((state) => {
          const today = getToday();
          const todayProgress =
            state.todayProgress.date === today
              ? { ...state.todayProgress, studyMinutes: state.todayProgress.studyMinutes + minutes }
              : { ...getEmptyDay(today), studyMinutes: minutes };
          return { todayProgress };
        });
        updateStreak();
        checkAndAwardBadges();
      },

      recordLessonComplete: () => {
        const { addXP, updateStreak, checkAndAwardBadges } = get();
        addXP(100);
        set((state) => {
          const today = getToday();
          const todayProgress =
            state.todayProgress.date === today
              ? { ...state.todayProgress, lessonsCompleted: state.todayProgress.lessonsCompleted + 1 }
              : { ...getEmptyDay(today), lessonsCompleted: 1 };
          return { todayProgress };
        });
        updateStreak();
        checkAndAwardBadges();
      },

      recordQuizComplete: (score: number, total: number) => {
        const { addXP, updateStreak, checkAndAwardBadges } = get();
        const baseXP = 50;
        const bonusXP = Math.round((score / total) * 100);
        addXP(baseXP + bonusXP);
        const isPerfect = score === total && total > 0;
        set((state) => {
          const today = getToday();
          const todayProgress =
            state.todayProgress.date === today
              ? { ...state.todayProgress, quizzesTaken: state.todayProgress.quizzesTaken + 1 }
              : { ...getEmptyDay(today), quizzesTaken: 1 };
          return { todayProgress, hadPerfectQuiz: state.hadPerfectQuiz || isPerfect };
        });
        updateStreak();
        checkAndAwardBadges();
      },

      recordSubjectStudied: (subject: string) => {
        set((state) => {
          const today = getToday();
          const isToday = state.todayProgress.date === today;
          const current = isToday ? state.subjectsStudiedToday : [];
          if (current.includes(subject)) return {};
          return { subjectsStudiedToday: [...current, subject] };
        });
        get().checkAndAwardBadges();
      },

      updateStreak: () => {
        set((state) => {
          const today = getToday();
          const yesterday = new Date();
          yesterday.setDate(yesterday.getDate() - 1);
          const yesterdayStr = yesterday.toISOString().split('T')[0];

          let newStreak = state.currentStreak;
          if (state.lastStudyDate === today) {
            return {}; // Already counted today
          } else if (state.lastStudyDate === yesterdayStr) {
            newStreak = state.currentStreak + 1;
          } else {
            newStreak = 1; // Streak broken, restart
          }

          // Archive yesterday if needed
          const dailyHistory = [...state.dailyHistory];
          if (state.todayProgress.date !== today && state.todayProgress.xpEarned > 0) {
            dailyHistory.push(state.todayProgress);
            if (dailyHistory.length > 90) dailyHistory.shift(); // Keep 90 days
          }

          // Streak bonus XP
          if (newStreak > 1) {
            const streakBonus = STREAK_XP_BONUS * Math.min(newStreak, 7);
            const totalXP = state.totalXP + streakBonus;
            const { level, xpForNext } = calculateLevel(totalXP);
            return {
              currentStreak: newStreak,
              longestStreak: Math.max(newStreak, state.longestStreak),
              lastStudyDate: today,
              dailyHistory,
              totalXP,
              currentLevel: level,
              xpForNextLevel: xpForNext,
            };
          }

          return {
            currentStreak: newStreak,
            longestStreak: Math.max(newStreak, state.longestStreak),
            lastStudyDate: today,
            dailyHistory,
          };
        });
      },

      checkAndAwardBadges: () => {
        set((state) => {
          const earned = new Set(state.badges.map((b) => b.id));
          const newBadges: Badge[] = [...state.badges];
          const now = new Date().toISOString();

          const totalQuizzes = state.dailyHistory.reduce((s, d) => s + d.quizzesTaken, 0) + state.todayProgress.quizzesTaken;
          const totalLessons = state.dailyHistory.reduce((s, d) => s + d.lessonsCompleted, 0) + state.todayProgress.lessonsCompleted;

          const checks: Array<[string, boolean]> = [
            ['first_lesson', totalLessons >= 1],
            ['streak_3', state.currentStreak >= 3],
            ['streak_7', state.currentStreak >= 7],
            ['streak_30', state.currentStreak >= 30],
            ['quiz_5', totalQuizzes >= 5],
            ['quiz_perfect', state.hadPerfectQuiz],
            ['xp_1000', state.totalXP >= 1000],
            ['xp_5000', state.totalXP >= 5000],
            ['xp_10000', state.totalXP >= 10000],
            ['study_60', state.todayProgress.studyMinutes >= 60],
            ['all_subjects', state.subjectsStudiedToday.length >= 3],
            ['level_5', state.currentLevel >= 5],
            ['level_10', state.currentLevel >= 10],
          ];

          for (const [id, condition] of checks) {
            if (condition && !earned.has(id)) {
              const template = ALL_BADGES.find((b) => b.id === id);
              if (template) {
                newBadges.push({ ...template, earnedAt: now });
              }
            }
          }

          return newBadges.length !== state.badges.length ? { badges: newBadges } : {};
        });
      },
    }),
    { name: 'APXMIND-gamification', onRehydrateStorage: () => (state) => { state?.setHasHydrated(true); } }
  )
);

export { ALL_BADGES };
