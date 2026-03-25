import {
  Card,
  CardBody,
  CardHeader,
  Progress,
  Divider,
} from '@heroui/react';
import { motion } from 'framer-motion';
import { CalendarDays, Target, CheckCircle2, Clock, Flame } from 'lucide-react';
import { useGamificationStore } from '../store/gamificationStore';
import { useProfileStore } from '../store/profileStore';

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 15 }, show: { opacity: 1, y: 0 } };

const daysOfWeek = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export function StudyPlanPage() {
  const profile = useProfileStore((s) => s.profile);
  const { currentStreak, dailyHistory, todayProgress } = useGamificationStore();

  const dailyTarget = profile?.dailyStudyTarget || 4;
  const studyHoursToday = todayProgress.studyMinutes / 60;
  const dailyPercent = Math.min((studyHoursToday / dailyTarget) * 100, 100);

  // Build weekly heatmap data
  const today = new Date();
  const weekData = Array.from({ length: 7 }, (_, i) => {
    const date = new Date(today);
    date.setDate(date.getDate() - (6 - i));
    const dateStr = date.toISOString().split('T')[0];
    const historyEntry = dailyHistory.find((d) => d.date === dateStr);
    const isTodayDate = dateStr === today.toISOString().split('T')[0];
    const progress = isTodayDate ? todayProgress : historyEntry;
    return {
      day: daysOfWeek[date.getDay() === 0 ? 6 : date.getDay() - 1],
      date: dateStr,
      minutes: progress?.studyMinutes || 0,
      xp: progress?.xpEarned || 0,
      lessons: progress?.lessonsCompleted || 0,
      quizzes: progress?.quizzesTaken || 0,
      isToday: isTodayDate,
    };
  });

  const neetExamDate = profile?.targetYear
    ? new Date(`${profile.targetYear}-05-05`) // Approximate NEET date
    : null;
  const daysUntilNEET = neetExamDate
    ? Math.max(0, Math.floor((neetExamDate.getTime() - Date.now()) / 86400000))
    : null;

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="max-w-4xl mx-auto space-y-5">
      <motion.div variants={item}>
        <h1 className="flex items-center gap-2" style={{ fontFamily: 'var(--font-heading)', fontSize: 20, fontWeight: 600, color: 'var(--text-primary)' }}>
          <CalendarDays className="w-6 h-6 text-primary" />
          Study Plan
        </h1>
      </motion.div>

      {/* Countdown card */}
      {daysUntilNEET !== null && (
        <motion.div variants={item}>
          <Card className="glass" style={{ background: 'var(--bg-3)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--r-lg)' }}>
            <CardBody className="text-center" style={{ padding: '28px 20px' }}>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Days Until NEET {profile?.targetYear}</p>
              <p style={{ fontFamily: 'var(--font-heading)', fontSize: 56, fontWeight: 600, color: 'var(--accent)', lineHeight: 1 }}>{daysUntilNEET}</p>
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Stay focused, stay consistent!</p>
            </CardBody>
          </Card>
        </motion.div>
      )}

      {/* Today's progress */}
      <motion.div variants={item}>
        <Card className="glass">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Target className="w-4 h-4 text-success" />
              <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>Today's Progress</h2>
            </div>
          </CardHeader>
          <CardBody className="gap-3">
            <div className="flex items-center justify-between">
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Study Time</span>
              <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{Math.round(studyHoursToday * 10) / 10}h / {dailyTarget}h</span>
            </div>
            <Progress value={dailyPercent} color="success" size="md" classNames={{ track: 'bg-bg-5', indicator: 'bg-linear-to-r from-[#22C55E] to-[var(--green)]' }} />
            <div className="grid grid-cols-3 gap-3 mt-2">
              <div className="text-center">
                <p className="text-lg font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>{todayProgress.lessonsCompleted}</p>
                <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>Lessons</p>
              </div>
              <div className="text-center">
                <p className="text-lg font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--text-primary)' }}>{todayProgress.quizzesTaken}</p>
                <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>Quizzes</p>
              </div>
              <div className="text-center">
                <p className="text-lg font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--amber)' }}>+{todayProgress.xpEarned}</p>
                <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>XP</p>
              </div>
            </div>
          </CardBody>
        </Card>
      </motion.div>

      {/* Weekly heatmap */}
      <motion.div variants={item}>
        <Card className="glass">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Flame className="w-4 h-4 text-danger" />
              <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>This Week ({currentStreak} day streak)</h2>
            </div>
          </CardHeader>
          <CardBody>
            <div className="grid grid-cols-7 gap-2">
              {weekData.map((d) => {
                const intensity =
                  d.minutes === 0 ? 0 : d.minutes < 30 ? 1 : d.minutes < 60 ? 2 : d.minutes < 120 ? 3 : 4;
                return (
                  <div key={d.date} className="text-center">
                    <p
                      className="mb-1"
                      style={{
                        fontSize: 10,
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        color: d.isToday ? 'var(--accent)' : 'var(--text-faint)',
                        fontWeight: d.isToday ? 600 : 400,
                      }}
                    >
                      {d.day}
                    </p>
                    <div
                      className="w-full aspect-square flex items-center justify-center"
                      style={{
                        background:
                          d.isToday
                            ? 'var(--accent-glow)'
                            : intensity === 0
                            ? 'var(--bg-3)'
                            : intensity <= 2
                            ? 'var(--green-soft)'
                            : 'rgba(74, 222, 128, 0.24)',
                        border: d.isToday
                          ? '1px solid var(--accent)'
                          : intensity > 0
                          ? '1px solid var(--green-border)'
                          : '1px solid var(--border-subtle)',
                        borderRadius: 'var(--r-md)',
                        padding: '10px 8px',
                      }}
                    >
                      {d.minutes > 0 && (
                        <CheckCircle2 className="w-4 h-4 text-success" />
                      )}
                    </div>
                    <p className="mt-1" style={{ fontSize: 10, color: 'var(--text-faint)' }}>
                      {d.minutes > 0 ? `${d.minutes}m` : '—'}
                    </p>
                  </div>
                );
              })}
            </div>
          </CardBody>
        </Card>
      </motion.div>

      {/* Suggested daily routine */}
      <motion.div variants={item}>
        <Card className="glass">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-400" />
              <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>Suggested Daily Routine</h2>
            </div>
          </CardHeader>
          <CardBody>
            <div className="space-y-2">
              {[
                { time: '6:00 – 8:00 AM', activity: 'Physics — Theory + NCERT reading', subject: 'physics' },
                { time: '8:30 – 10:30 AM', activity: 'Chemistry — NCERT + practice MCQs', subject: 'chemistry' },
                { time: '11:00 – 1:00 PM', activity: 'Biology — NCERT + diagrams', subject: 'biology' },
                { time: '2:00 – 3:00 PM', activity: 'Revision — weak topics', subject: 'all' },
                { time: '3:30 – 5:00 PM', activity: 'Practice quizzes on APXMIND', subject: 'all' },
                { time: '5:30 – 7:00 PM', activity: 'PYQ solving + analysis', subject: 'all' },
                { time: '8:00 – 9:00 PM', activity: 'Quick revision before sleep', subject: 'all' },
              ].map((slot, i) => (
                <div key={i} className="flex items-start gap-4" style={{ padding: '12px 0', borderBottom: i === 6 ? 'none' : '1px solid var(--border-subtle)' }}>
                  <span className="w-32 shrink-0" style={{ minWidth: 100, fontSize: 11, color: 'var(--text-faint)' }}>{slot.time}</span>
                  <Divider orientation="vertical" className="h-4" />
                  <span className="flex-1" style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{slot.activity}</span>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      </motion.div>
    </motion.div>
  );
}
