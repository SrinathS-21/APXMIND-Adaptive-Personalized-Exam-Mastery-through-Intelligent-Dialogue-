import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  CardBody,
  CardHeader,
  Progress,
  Divider,
  Chip,
  Button,
  Spinner,
  Input,
} from '@heroui/react';
import { motion } from 'framer-motion';
import {
  CalendarDays,
  Target,
  CheckCircle2,
  Clock,
  Flame,
  AlertTriangle,
  RefreshCcw,
  Check,
  X,
  Sparkles,
  Activity,
  TrendingUp,
  Trash2,
} from 'lucide-react';
import { useGamificationStore } from '../store/gamificationStore';
import { useProfileStore } from '../store/profileStore';
import { getApiErrorMessage } from '../lib/api';
import {
  DailyPlannerSnapshot,
  ExamReadinessSnapshot,
  HabitSignal,
  PlannerTask,
  TopicRisk,
  TopicMastery,
  CalibrationSnapshot,
  WeeklySummary,
  getCalibration,
  getDailyPlanner,
  getHabitSignals,
  getMastery,
  getReadiness,
  getRiskTopics,
  runStrategistPlanner,
  getWeeklySummary,
  updatePlannerTask,
} from '../lib/plannerInsightsService';
import {
  RecommendationItem,
  deleteRecommendation,
  getRecommendations,
  updateRecommendationStatus,
} from '../lib/recommendationsService';
import {
  SpacedReviewItem,
  completeSpacedReview,
  getSpacedQueue,
} from '../lib/retrievalService';
import {
  MistakeCardItem,
  getMistakeCards,
  updateMistakeCardStatus,
} from '../lib/errorNotebookService';
import {
  DailyProgressDay,
  StudySubject,
  getDailyProgress,
  recordStudyMinutes,
} from '../lib/progressService';

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 15 }, show: { opacity: 1, y: 0 } };

const daysOfWeek = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export function StudyPlanPage() {
  const navigate = useNavigate();
  const profile = useProfileStore((s) => s.profile);
  const { currentStreak, dailyHistory, todayProgress } = useGamificationStore();
  const [planner, setPlanner] = useState<DailyPlannerSnapshot | null>(null);
  const [riskTopics, setRiskTopics] = useState<TopicRisk[]>([]);
  const [masteryRows, setMasteryRows] = useState<TopicMastery[]>([]);
  const [readinessLatest, setReadinessLatest] = useState<ExamReadinessSnapshot | null>(null);
  const [habitSignals, setHabitSignals] = useState<HabitSignal[]>([]);
  const [calibration, setCalibration] = useState<CalibrationSnapshot | null>(null);
  const [weeklySummary, setWeeklySummary] = useState<WeeklySummary | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [spacedQueue, setSpacedQueue] = useState<SpacedReviewItem[]>([]);
  const [mistakeCards, setMistakeCards] = useState<MistakeCardItem[]>([]);
  const [isLiveLoading, setIsLiveLoading] = useState(true);
  const [isGeneratingPlan, setIsGeneratingPlan] = useState(false);
  const [updatingTaskId, setUpdatingTaskId] = useState<string | null>(null);
  const [updatingRecommendationId, setUpdatingRecommendationId] = useState<number | null>(null);
  const [updatingReviewId, setUpdatingReviewId] = useState<string | null>(null);
  const [updatingCardId, setUpdatingCardId] = useState<string | null>(null);
  const [liveError, setLiveError] = useState<string | null>(null);
  const [dailyProgressRows, setDailyProgressRows] = useState<DailyProgressDay[]>([]);
  const [manualMinutes, setManualMinutes] = useState('30');
  const [manualSubject, setManualSubject] = useState<StudySubject>('biology');
  const [isRecordingMinutes, setIsRecordingMinutes] = useState(false);
  const [manualStudyMessage, setManualStudyMessage] = useState<string | null>(null);

  const dailyTarget = profile?.dailyStudyTarget || 4;
  const studyHoursToday = todayProgress.studyMinutes / 60;
  const dailyPercent = Math.min((studyHoursToday / dailyTarget) * 100, 100);

  async function loadLiveData() {
    setIsLiveLoading(true);
    setLiveError(null);
    try {
      const dueCutoff = new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString();
      const [
        plannerData,
        riskRows,
        masteryData,
        readinessData,
        habitData,
        calibrationData,
        weeklyData,
        recommendationRows,
        queueRows,
        cardRows,
        dailyRows,
      ] = await Promise.all([
        getDailyPlanner(),
        getRiskTopics(5),
        getMastery(),
        getReadiness(30),
        getHabitSignals(7),
        getCalibration(30),
        getWeeklySummary(7),
        getRecommendations({ status: 'active', limit: 6 }),
        getSpacedQueue(6, dueCutoff),
        getMistakeCards('active', 6),
        getDailyProgress(7),
      ]);
      setPlanner(plannerData);
      setRiskTopics(riskRows);
      setMasteryRows(masteryData);
      setReadinessLatest(readinessData.latest ?? null);
      setHabitSignals(habitData);
      setCalibration(calibrationData);
      setWeeklySummary(weeklyData);
      setRecommendations(recommendationRows);
      setSpacedQueue(queueRows);
      setMistakeCards(cardRows);
      setDailyProgressRows(dailyRows);
    } catch (error) {
      setLiveError(getApiErrorMessage(error, 'Unable to load live planning insights.'));
    } finally {
      setIsLiveLoading(false);
    }
  }

  useEffect(() => {
    void loadLiveData();
  }, []);

  async function handleGeneratePlan() {
    setIsGeneratingPlan(true);
    try {
      await runStrategistPlanner();
      await loadLiveData();
    } catch (error) {
      setLiveError(getApiErrorMessage(error, 'Unable to generate daily plan right now.'));
    } finally {
      setIsGeneratingPlan(false);
    }
  }

  async function handleTaskUpdate(taskId: string, status: 'completed' | 'skipped') {
    setUpdatingTaskId(taskId);
    try {
      await updatePlannerTask(taskId, status);
      await loadLiveData();
    } catch (error) {
      setLiveError(getApiErrorMessage(error, 'Unable to update task status.'));
    } finally {
      setUpdatingTaskId(null);
    }
  }

  function handleLaunchMiniSet(task: PlannerTask) {
    const params = new URLSearchParams({ taskId: task.id });
    if (task.topic) {
      params.set('topic', task.topic);
    }
    if (task.subject) {
      params.set('subject', task.subject);
    }
    navigate(`/mini-set?${params.toString()}`);
  }

  function handleLaunchStamina(task: PlannerTask) {
    const params = new URLSearchParams({ taskId: task.id });
    if (task.topic) {
      params.set('topic', task.topic);
    }
    if (task.subject) {
      params.set('subject', task.subject);
    }
    navigate(`/exam/stamina?${params.toString()}`);
  }

  async function handleRecommendationUpdate(
    recommendationId: number,
    status: 'accepted' | 'dismissed'
  ) {
    setUpdatingRecommendationId(recommendationId);
    try {
      await updateRecommendationStatus(recommendationId, status);
      setRecommendations((prev) => prev.filter((item) => item.id !== recommendationId));
    } catch (error) {
      setLiveError(getApiErrorMessage(error, 'Unable to update recommendation right now.'));
    } finally {
      setUpdatingRecommendationId(null);
    }
  }

  async function handleRecommendationDelete(recommendationId: number) {
    setUpdatingRecommendationId(recommendationId);
    try {
      await deleteRecommendation(recommendationId);
      setRecommendations((prev) => prev.filter((item) => item.id !== recommendationId));
    } catch (error) {
      setLiveError(getApiErrorMessage(error, 'Unable to delete recommendation right now.'));
    } finally {
      setUpdatingRecommendationId(null);
    }
  }

  async function handleCompleteReview(reviewId: string, result: 'correct' | 'partial' | 'incorrect') {
    setUpdatingReviewId(reviewId);
    try {
      await completeSpacedReview(reviewId, result, result === 'incorrect' ? 2 : 4);
      setSpacedQueue((prev) => prev.filter((item) => item.id !== reviewId));
    } catch (error) {
      setLiveError(getApiErrorMessage(error, 'Unable to update spaced review right now.'));
    } finally {
      setUpdatingReviewId(null);
    }
  }

  async function handleResolveMistakeCard(cardId: string) {
    setUpdatingCardId(cardId);
    try {
      await updateMistakeCardStatus(cardId, 'resolved');
      setMistakeCards((prev) => prev.filter((card) => card.id !== cardId));
    } catch (error) {
      setLiveError(getApiErrorMessage(error, 'Unable to update mistake card.'));
    } finally {
      setUpdatingCardId(null);
    }
  }

  async function handleRecordManualStudy() {
    const parsed = Number.parseInt(manualMinutes, 10);
    if (!Number.isFinite(parsed) || parsed < 1 || parsed > 720) {
      setLiveError('Study minutes must be between 1 and 720.');
      return;
    }

    setIsRecordingMinutes(true);
    setManualStudyMessage(null);
    setLiveError(null);
    try {
      const result = await recordStudyMinutes(manualSubject, parsed);
      if (result.message) {
        setManualStudyMessage(result.message);
      } else {
        const xpAwarded = result.xp_awarded ?? 0;
        setManualStudyMessage(`Recorded ${parsed} minutes in ${manualSubject}. +${xpAwarded} XP`);
      }
      await loadLiveData();
    } catch (error) {
      setLiveError(getApiErrorMessage(error, 'Unable to record manual study minutes.'));
    } finally {
      setIsRecordingMinutes(false);
    }
  }

  // Build weekly heatmap data
  const today = new Date();
  const progressByDate = new Map(dailyProgressRows.map((row) => [row.date, row]));
  const weekData = Array.from({ length: 7 }, (_, i) => {
    const date = new Date(today);
    date.setDate(date.getDate() - (6 - i));
    const dateStr = date.toISOString().split('T')[0];
    const historyEntry = dailyHistory.find((d) => d.date === dateStr);
    const isTodayDate = dateStr === today.toISOString().split('T')[0];
    const fallbackProgress = isTodayDate ? todayProgress : historyEntry;
    const backendProgress = progressByDate.get(dateStr);
    return {
      day: daysOfWeek[date.getDay() === 0 ? 6 : date.getDay() - 1],
      date: dateStr,
      minutes: backendProgress?.study_minutes ?? fallbackProgress?.studyMinutes ?? 0,
      xp: backendProgress?.xp_earned ?? fallbackProgress?.xpEarned ?? 0,
      lessons: backendProgress?.lessons_completed ?? fallbackProgress?.lessonsCompleted ?? 0,
      quizzes: backendProgress?.quizzes_taken ?? fallbackProgress?.quizzesTaken ?? 0,
      isToday: isTodayDate,
    };
  });

  const neetExamDate = profile?.targetYear
    ? new Date(`${profile.targetYear}-05-05`) // Approximate NEET date
    : null;
  const daysUntilNEET = neetExamDate
    ? Math.max(0, Math.floor((neetExamDate.getTime() - Date.now()) / 86400000))
    : null;

  const weakMastery = [...masteryRows]
    .sort((a, b) => a.mastery_score - b.mastery_score)
    .slice(0, 5);

  const habitDayCount = habitSignals.length;
  const avgFocusMinutes = habitDayCount
    ? habitSignals.reduce((sum, row) => sum + row.deep_focus_minutes, 0) / habitDayCount
    : 0;
  const avgSessions = habitDayCount
    ? habitSignals.reduce((sum, row) => sum + row.session_count, 0) / habitDayCount
    : 0;
  const avgInterruptions = habitDayCount
    ? habitSignals.reduce((sum, row) => sum + row.interruptions_count, 0) / habitDayCount
    : 0;

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="max-w-7xl mx-auto space-y-5">
      <motion.div variants={item}>
        <h1 className="flex items-center gap-2" style={{ fontFamily: 'var(--font-heading)', fontSize: 20, fontWeight: 600, color: 'var(--text-primary)' }}>
          <CalendarDays className="w-6 h-6 text-primary" />
          Study Plan
        </h1>
      </motion.div>

      {/* Main workspace: planner on left, week + routine stacked on right */}
      <motion.div variants={item} className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        <div className="xl:col-span-8 space-y-4">
          {daysUntilNEET !== null && (
            <Card className="glass" style={{ background: 'var(--bg-3)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--r-lg)' }}>
              <CardBody className="text-center" style={{ padding: '28px 20px' }}>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Days Until NEET {profile?.targetYear}</p>
                <p style={{ fontFamily: 'var(--font-heading)', fontSize: 56, fontWeight: 600, color: 'var(--accent)', lineHeight: 1 }}>{daysUntilNEET}</p>
                <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Stay focused, stay consistent!</p>
              </CardBody>
            </Card>
          )}

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

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card className="glass lg:col-span-2">
              <CardHeader className="pb-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-secondary" />
                  <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
                    Adaptive Daily Plan
                  </h2>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="flat"
                    color="secondary"
                    startContent={<RefreshCcw className="w-3 h-3" />}
                    onPress={() => void loadLiveData()}
                    isDisabled={isLiveLoading}
                  >
                    Refresh
                  </Button>
                  <Button
                    size="sm"
                    color="secondary"
                    onPress={() => void handleGeneratePlan()}
                    isLoading={isGeneratingPlan}
                  >
                    Generate Plan
                  </Button>
                </div>
              </CardHeader>
              <CardBody className="space-y-3">
                {isLiveLoading ? (
                  <div className="py-5 flex items-center justify-center">
                    <Spinner size="sm" color="secondary" label="Loading planner" />
                  </div>
                ) : (
                  <>
                    {planner ? (
                      <div className="flex flex-wrap gap-2">
                        <Chip size="sm" variant="flat">{planner.total} tasks</Chip>
                        <Chip size="sm" variant="flat">{planner.planned_minutes} min planned</Chip>
                        <Chip size="sm" variant="flat" color="success">{planner.completed_count} completed</Chip>
                        <Chip size="sm" variant="flat" color="warning">{planner.pending_count} pending</Chip>
                        <Chip size="sm" variant="flat" color="secondary">
                          {planner.day_adherence_percent.toFixed(0)}% adherence
                        </Chip>
                      </div>
                    ) : null}

                    {planner?.tasks?.length ? (
                      <div className="space-y-2">
                        {planner.tasks.map((task) => (
                          <div
                            key={task.id}
                            className="rounded-lg p-3"
                            style={{ border: '1px solid var(--border-subtle)', background: 'var(--bg-2)' }}
                          >
                            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                              <div>
                                <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                                  {task.task_type.replace('_', ' ')}: {task.topic || 'General revision'}
                                </p>
                                <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                                  {(task.subject || 'all subjects').toUpperCase()} • {task.recommended_minutes} minutes • priority {task.priority_score.toFixed(1)}
                                </p>
                              </div>
                              <div className="flex items-center gap-1.5">
                                <Chip
                                  size="sm"
                                  variant="flat"
                                  color={task.status === 'completed' ? 'success' : task.status === 'skipped' ? 'danger' : 'warning'}
                                >
                                  {task.status}
                                </Chip>
                                {task.status === 'pending' && (
                                  <>
                                    {task.task_type === 'mini_set' ? (
                                      <Button
                                        size="sm"
                                        variant="flat"
                                        color="secondary"
                                        startContent={<Sparkles className="w-3 h-3" />}
                                        onPress={() => handleLaunchMiniSet(task)}
                                      >
                                        Start Mini-Set
                                      </Button>
                                    ) : task.task_type === 'stamina' ? (
                                      <Button
                                        size="sm"
                                        variant="flat"
                                        color="secondary"
                                        startContent={<Clock className="w-3 h-3" />}
                                        onPress={() => handleLaunchStamina(task)}
                                      >
                                        Start Stamina
                                      </Button>
                                    ) : (
                                      <Button
                                        size="sm"
                                        variant="flat"
                                        color="success"
                                        isLoading={updatingTaskId === task.id}
                                        startContent={<Check className="w-3 h-3" />}
                                        onPress={() => void handleTaskUpdate(task.id, 'completed')}
                                      >
                                        Done
                                      </Button>
                                    )}
                                    <Button
                                      size="sm"
                                      variant="flat"
                                      color="danger"
                                      isLoading={updatingTaskId === task.id}
                                      startContent={<X className="w-3 h-3" />}
                                      onPress={() => void handleTaskUpdate(task.id, 'skipped')}
                                    >
                                      Skip
                                    </Button>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        No planner tasks available for today. Click Generate Plan to create one.
                      </p>
                    )}
                  </>
                )}

                {liveError ? (
                  <div className="rounded-lg p-3 flex items-start gap-2" style={{ background: 'var(--red-soft)', border: '1px solid var(--red-border)' }}>
                    <AlertTriangle className="w-4 h-4 mt-0.5" style={{ color: 'var(--red)' }} />
                    <p style={{ fontSize: 12, color: 'var(--red)' }}>{liveError}</p>
                  </div>
                ) : null}
              </CardBody>
            </Card>

            <div className="space-y-4">
              <Card className="glass">
                <CardHeader className="pb-2">
                  <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
                    Top Risk Topics
                  </h2>
                </CardHeader>
                <CardBody className="space-y-2">
                  {isLiveLoading ? (
                    <Spinner size="sm" color="warning" label="Loading risks" />
                  ) : riskTopics.length ? (
                    riskTopics.map((topic) => (
                      <div key={`${topic.subject}-${topic.topic}`} className="rounded-md p-2" style={{ border: '1px solid var(--border-subtle)' }}>
                        <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>
                          {topic.topic}
                        </p>
                        <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                          {topic.subject} • risk {topic.risk_score.toFixed(1)} • {topic.state_label}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>No risk topics identified yet.</p>
                  )}
                </CardBody>
              </Card>

              <Card className="glass">
                <CardHeader className="pb-2">
                  <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
                    Calibration & Weekly Summary
                  </h2>
                </CardHeader>
                <CardBody className="space-y-1.5">
                  <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    Confidence gap: <strong>{(calibration?.confidence_accuracy_gap ?? 0).toFixed(1)}%</strong>
                  </p>
                  <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    Confident-wrong: <strong>{(calibration?.confident_wrong_rate ?? 0).toFixed(1)}%</strong>
                  </p>
                  <Divider className="my-1" />
                  <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    Retention: <strong>{(weeklySummary?.retention_score ?? 0).toFixed(1)}%</strong>
                  </p>
                  <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    Accuracy: <strong>{(weeklySummary?.accuracy_percent ?? 0).toFixed(1)}%</strong>
                  </p>
                  <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    Speed: <strong>{(weeklySummary?.speed_qph ?? 0).toFixed(1)} q/h</strong>
                  </p>
                </CardBody>
              </Card>

              <Card className="glass">
                <CardHeader className="pb-2">
                  <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
                    Spaced Revision Queue
                  </h2>
                </CardHeader>
                <CardBody className="space-y-2">
                  {isLiveLoading ? (
                    <Spinner size="sm" color="secondary" label="Loading queue" />
                  ) : spacedQueue.length ? (
                    spacedQueue.map((item) => (
                      <div key={item.id} className="rounded-md p-2" style={{ border: '1px solid var(--border-subtle)' }}>
                        <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>{item.topic}</p>
                        <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                          {(item.subject || 'general').toUpperCase()} • due {new Date(item.due_at).toLocaleDateString()} • streak {item.streak}
                        </p>
                        <div className="flex items-center gap-1.5 mt-2">
                          <Button
                            size="sm"
                            variant="flat"
                            color="success"
                            isLoading={updatingReviewId === item.id}
                            onPress={() => void handleCompleteReview(item.id, 'correct')}
                          >
                            Correct
                          </Button>
                          <Button
                            size="sm"
                            variant="flat"
                            color="warning"
                            isLoading={updatingReviewId === item.id}
                            onPress={() => void handleCompleteReview(item.id, 'partial')}
                          >
                            Partial
                          </Button>
                          <Button
                            size="sm"
                            variant="flat"
                            color="danger"
                            isLoading={updatingReviewId === item.id}
                            onPress={() => void handleCompleteReview(item.id, 'incorrect')}
                          >
                            Incorrect
                          </Button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>No due revision items in the next 48 hours.</p>
                  )}
                </CardBody>
              </Card>

              <Card className="glass">
                <CardHeader className="pb-2">
                  <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
                    Error Notebook
                  </h2>
                </CardHeader>
                <CardBody className="space-y-2">
                  {isLiveLoading ? (
                    <Spinner size="sm" color="warning" label="Loading mistakes" />
                  ) : mistakeCards.length ? (
                    mistakeCards.map((card) => (
                      <div key={card.id} className="rounded-md p-2" style={{ border: '1px solid var(--border-subtle)' }}>
                        <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>
                          {card.topic || 'General concept'}
                        </p>
                        <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                          {card.error_reason_code} • repeated {card.times_repeated} times
                        </p>
                        <p style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>
                          {card.prompt_snapshot.slice(0, 120)}{card.prompt_snapshot.length > 120 ? '...' : ''}
                        </p>
                        <Button
                          size="sm"
                          variant="flat"
                          color="success"
                          className="mt-2"
                          isLoading={updatingCardId === card.id}
                          onPress={() => void handleResolveMistakeCard(card.id)}
                        >
                          Mark Resolved
                        </Button>
                      </div>
                    ))
                  ) : (
                    <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>No active mistake cards right now.</p>
                  )}
                </CardBody>
              </Card>
            </div>
          </div>
        </div>

        <div className="xl:col-span-4 space-y-4">
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
              <p className="mt-2" style={{ fontSize: 11, color: 'var(--text-faint)' }}>
                Heatmap uses live rows from /api/progress/daily with local fallback.
              </p>
            </CardBody>
          </Card>

          <Card className="glass">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-primary" />
                <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
                  Log Study Minutes
                </h2>
              </div>
            </CardHeader>
            <CardBody className="space-y-2">
              <Input
                type="number"
                min={1}
                max={720}
                value={manualMinutes}
                onValueChange={setManualMinutes}
                label="Minutes"
                size="sm"
                variant="bordered"
              />
              <div className="flex items-center gap-2 flex-wrap">
                {(['physics', 'chemistry', 'biology'] as StudySubject[]).map((subjectKey) => (
                  <Button
                    key={subjectKey}
                    size="sm"
                    variant={manualSubject === subjectKey ? 'solid' : 'flat'}
                    color={manualSubject === subjectKey ? 'secondary' : 'default'}
                    onPress={() => setManualSubject(subjectKey)}
                    className="capitalize"
                  >
                    {subjectKey}
                  </Button>
                ))}
              </div>
              <Button
                size="sm"
                color="secondary"
                onPress={() => void handleRecordManualStudy()}
                isLoading={isRecordingMinutes}
              >
                Record Minutes
              </Button>
              {manualStudyMessage ? (
                <Chip size="sm" color="success" variant="flat" className="w-full justify-center">
                  {manualStudyMessage}
                </Chip>
              ) : null}
            </CardBody>
          </Card>

          <Card className="glass">
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-blue-400" />
                <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
                  Readiness & Habits
                </h2>
              </div>
            </CardHeader>
            <CardBody className="space-y-2">
              {readinessLatest ? (
                <>
                  <div className="flex items-center gap-2 flex-wrap">
                    <Chip size="sm" variant="flat" color="secondary">
                      {readinessLatest.risk_band || 'Unknown risk'}
                    </Chip>
                    <Chip size="sm" variant="flat">
                      snapshot {new Date(readinessLatest.snapshot_date).toLocaleDateString()}
                    </Chip>
                  </div>
                  <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    Projected score: <strong>{Math.round(readinessLatest.projected_score ?? 0)}</strong>
                  </p>
                  <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    Coverage: <strong>{(readinessLatest.syllabus_coverage_percent ?? 0).toFixed(1)}%</strong>
                  </p>
                  <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    Consistency: <strong>{(readinessLatest.consistency_score ?? 0).toFixed(1)}%</strong>
                  </p>
                  <Divider className="my-1" />
                </>
              ) : (
                <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  No readiness snapshot yet. Continue quizzes and revision to generate one.
                </p>
              )}

              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-success" />
                <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  7d focus avg: <strong>{avgFocusMinutes.toFixed(0)}m/day</strong>
                </p>
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                Sessions/day: <strong>{avgSessions.toFixed(1)}</strong> • Interruptions/day: <strong>{avgInterruptions.toFixed(1)}</strong>
              </p>
            </CardBody>
          </Card>

          <Card className="glass">
            <CardHeader className="pb-2">
              <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
                Mastery Snapshot
              </h2>
            </CardHeader>
            <CardBody className="space-y-2">
              {isLiveLoading ? (
                <Spinner size="sm" color="secondary" label="Loading mastery" />
              ) : weakMastery.length ? (
                weakMastery.map((row) => (
                  <div key={`${row.subject}-${row.topic}`} className="rounded-md p-2" style={{ border: '1px solid var(--border-subtle)' }}>
                    <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>
                      {row.topic}
                    </p>
                    <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {row.subject} • mastery {row.mastery_score.toFixed(1)} • confidence {row.confidence.toFixed(1)} • {row.state_label}
                    </p>
                  </div>
                ))
              ) : (
                <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  No mastery rows yet. Complete recalls and quizzes to populate this.
                </p>
              )}
            </CardBody>
          </Card>

          <Card className="glass">
            <CardHeader className="pb-2">
              <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
                Active Recommendations
              </h2>
            </CardHeader>
            <CardBody className="space-y-2">
              {isLiveLoading ? (
                <Spinner size="sm" color="secondary" label="Loading recommendations" />
              ) : recommendations.length ? (
                recommendations.map((rec) => (
                  <div key={rec.id} className="rounded-md p-2" style={{ border: '1px solid var(--border-subtle)' }}>
                    <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>
                      {rec.title}
                    </p>
                    <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {rec.reason}
                    </p>
                    <div className="flex flex-wrap items-center gap-1.5 mt-2">
                      <Chip size="sm" variant="flat" color="secondary">
                        {rec.rec_type}
                      </Chip>
                      {rec.subject ? (
                        <Chip size="sm" variant="flat">
                          {rec.subject}
                        </Chip>
                      ) : null}
                      {rec.topic ? (
                        <Chip size="sm" variant="flat">
                          {rec.topic}
                        </Chip>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-1.5 mt-2">
                      <Button
                        size="sm"
                        variant="flat"
                        color="success"
                        startContent={<Check className="w-3 h-3" />}
                        isLoading={updatingRecommendationId === rec.id}
                        onPress={() => void handleRecommendationUpdate(rec.id, 'accepted')}
                      >
                        Accept
                      </Button>
                      <Button
                        size="sm"
                        variant="flat"
                        color="danger"
                        startContent={<X className="w-3 h-3" />}
                        isLoading={updatingRecommendationId === rec.id}
                        onPress={() => void handleRecommendationUpdate(rec.id, 'dismissed')}
                      >
                        Dismiss
                      </Button>
                      <Button
                        size="sm"
                        variant="flat"
                        color="default"
                        startContent={<Trash2 className="w-3 h-3" />}
                        isLoading={updatingRecommendationId === rec.id}
                        onPress={() => void handleRecommendationDelete(rec.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                ))
              ) : (
                <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  No active recommendations right now. Generate a plan to refresh suggestions.
                </p>
              )}
              <div className="rounded-md p-2 flex items-start gap-2" style={{ background: 'var(--accent-glow)', border: '1px solid var(--accent-border)' }}>
                <Sparkles className="w-4 h-4 mt-0.5" style={{ color: 'var(--accent)' }} />
                <p style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                  Recommendations are personalized from your planner, weak topics, and recent learning signals.
                </p>
              </div>
            </CardBody>
          </Card>

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
        </div>
      </motion.div>
    </motion.div>
  );
}
