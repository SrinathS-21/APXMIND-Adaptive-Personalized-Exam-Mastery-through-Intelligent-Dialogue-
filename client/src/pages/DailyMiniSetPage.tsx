import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Button,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  Chip,
  Divider,
  Progress,
  Radio,
  RadioGroup,
  Spinner,
} from '@heroui/react';
import { motion } from 'framer-motion';
import { ArrowLeft, ArrowRight, BrainCircuit, CheckCircle2, Sparkles, Trophy, XCircle } from 'lucide-react';

import { getApiErrorMessage } from '../lib/api';
import { updatePlannerTask } from '../lib/plannerInsightsService';
import {
  finishQuiz,
  startQuiz,
  submitQuizAnswer,
  updateQuizAnswer,
  type QuizQuestion,
  type QuizSummary,
} from '../lib/quizService';
import { useGamificationStore } from '../store/gamificationStore';

type Phase = 'setup' | 'playing' | 'review' | 'segmentComplete' | 'results';
type QuizSubject = 'physics' | 'chemistry' | 'biology';

interface AnswerSnapshot {
  question: QuizQuestion;
  userAnswer: string;
  correctAnswer: string;
  correct: boolean;
  explanation: string;
}

interface SubjectSession {
  subject: QuizSubject;
  quizId: string;
  questions: QuizQuestion[];
  answers: AnswerSnapshot[];
  summary?: QuizSummary;
}

const SUBJECT_ORDER: QuizSubject[] = ['physics', 'chemistry', 'biology'];
const SUBJECT_LABELS: Record<QuizSubject, string> = {
  physics: 'Physics',
  chemistry: 'Chemistry',
  biology: 'Biology',
};
const QUESTIONS_PER_SUBJECT = 2;

function buildExplanation(params: {
  isCorrect: boolean;
  userAnswer: string;
  correctAnswer: string;
  backendExplanation?: string;
}) {
  const fromBackend = params.backendExplanation?.trim();
  if (fromBackend && fromBackend.toLowerCase() !== 'explanation not available.') {
    return fromBackend;
  }

  if (params.isCorrect) {
    return params.correctAnswer
      ? `Correct. ${params.correctAnswer} is the right option.`
      : 'Correct. Your answer matches the expected option.';
  }

  return params.correctAnswer
    ? `Incorrect. You selected ${params.userAnswer}, but the correct answer is ${params.correctAnswer}.`
    : 'Incorrect. Review the options and retry this concept.';
}

function aggregateScore(sessions: Partial<Record<QuizSubject, SubjectSession>>) {
  let correct = 0;
  let total = 0;

  SUBJECT_ORDER.forEach((subject) => {
    const session = sessions[subject];
    if (!session) {
      return;
    }

    if (session.summary) {
      correct += session.summary.correct_answers;
      total += session.summary.total_questions;
      return;
    }

    correct += session.answers.filter((entry) => entry.correct).length;
    total += session.answers.length;
  });

  return { correct, total };
}

export function DailyMiniSetPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { recordQuizComplete } = useGamificationStore();

  const taskId = searchParams.get('taskId')?.trim() || '';
  const plannerTopicRaw = searchParams.get('topic')?.trim() || '';
  const plannerSubjectRaw = searchParams.get('subject')?.trim() || '';

  const plannerTopic = useMemo(() => {
    if (!plannerTopicRaw) {
      return undefined;
    }
    if (/daily mixed mini-set/i.test(plannerTopicRaw)) {
      return undefined;
    }
    return plannerTopicRaw;
  }, [plannerTopicRaw]);

  const plannerSubject = useMemo(() => {
    const value = plannerSubjectRaw.toLowerCase();
    if (value === 'physics' || value === 'chemistry' || value === 'biology') {
      return value as QuizSubject;
    }
    return undefined;
  }, [plannerSubjectRaw]);

  const [phase, setPhase] = useState<Phase>('setup');
  const [subjectIndex, setSubjectIndex] = useState(0);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState('');
  const [sessions, setSessions] = useState<Partial<Record<QuizSubject, SubjectSession>>>({});
  const [lastReview, setLastReview] = useState<{ correct: boolean; explanation: string } | null>(null);

  const [isLoadingSegment, setIsLoadingSegment] = useState(false);
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);
  const [isFinishingSegment, setIsFinishingSegment] = useState(false);
  const [isUpdatingTask, setIsUpdatingTask] = useState(false);
  const [taskUpdateMessage, setTaskUpdateMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const activeSubject = SUBJECT_ORDER[subjectIndex];
  const activeSession = sessions[activeSubject];
  const activeQuestion = activeSession?.questions[currentQuestionIndex] ?? null;

  useEffect(() => {
    if (phase !== 'playing' || !activeQuestion || !activeSession) {
      setSelectedAnswer('');
      return;
    }
    const existing = activeSession.answers.find((entry) => entry.question.id === activeQuestion.id);
    setSelectedAnswer(existing?.userAnswer ?? '');
  }, [activeQuestion, activeSession, phase]);

  async function startSubjectSegment(subject: QuizSubject) {
    setIsLoadingSegment(true);
    setError(null);
    setLastReview(null);
    setTaskUpdateMessage(null);

    try {
      const response = await startQuiz(subject, 'mixed', QUESTIONS_PER_SUBJECT, plannerTopic);
      const session: SubjectSession = {
        subject,
        quizId: response.quiz.id,
        questions: response.questions || [],
        answers: [],
      };
      setSessions((prev) => ({ ...prev, [subject]: session }));
      setCurrentQuestionIndex(0);
      setSelectedAnswer('');
      setPhase('playing');
    } catch (err) {
      setError(getApiErrorMessage(err, `Unable to start ${SUBJECT_LABELS[subject]} segment.`));
    } finally {
      setIsLoadingSegment(false);
    }
  }

  async function handleStartMiniSet() {
    const firstSubject = plannerSubject ?? SUBJECT_ORDER[0];
    const firstSubjectIndex = SUBJECT_ORDER.indexOf(firstSubject);

    setSessions({});
    setSubjectIndex(firstSubjectIndex >= 0 ? firstSubjectIndex : 0);
    setCurrentQuestionIndex(0);
    setSelectedAnswer('');
    setLastReview(null);
    setError(null);
    setTaskUpdateMessage(null);

    await startSubjectSegment(firstSubject);
  }

  function updateSessionAnswer(subject: QuizSubject, answerSnapshot: AnswerSnapshot) {
    setSessions((prev) => {
      const session = prev[subject];
      if (!session) {
        return prev;
      }

      const existingIndex = session.answers.findIndex((entry) => entry.question.id === answerSnapshot.question.id);
      const answers = [...session.answers];
      if (existingIndex === -1) {
        answers.push(answerSnapshot);
      } else {
        answers[existingIndex] = answerSnapshot;
      }

      return {
        ...prev,
        [subject]: {
          ...session,
          answers,
        },
      };
    });
  }

  async function handleSubmitAnswer() {
    if (!activeSession || !activeQuestion || !selectedAnswer) {
      return;
    }

    setIsSubmittingAnswer(true);
    setError(null);

    try {
      const hasExisting = activeSession.answers.some((entry) => entry.question.id === activeQuestion.id);
      const response = hasExisting
        ? await updateQuizAnswer(activeSession.quizId, activeQuestion.id, selectedAnswer, 3)
        : await submitQuizAnswer(activeSession.quizId, activeQuestion.id, selectedAnswer, 3);

      const answerSnapshot: AnswerSnapshot = {
        question: activeQuestion,
        userAnswer: selectedAnswer,
        correctAnswer: response.result.correct_answer,
        correct: response.result.is_correct,
        explanation: buildExplanation({
          isCorrect: response.result.is_correct,
          userAnswer: selectedAnswer,
          correctAnswer: response.result.correct_answer,
          backendExplanation: response.result.explanation || undefined,
        }),
      };

      updateSessionAnswer(activeSubject, answerSnapshot);
      setLastReview({ correct: answerSnapshot.correct, explanation: answerSnapshot.explanation });
      setPhase('review');
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to submit answer right now.'));
    } finally {
      setIsSubmittingAnswer(false);
    }
  }

  async function finalizeCurrentSegment() {
    if (!activeSession) {
      return;
    }

    setIsFinishingSegment(true);
    setError(null);

    try {
      const response = await finishQuiz(activeSession.quizId);
      const updatedSession: SubjectSession = {
        ...activeSession,
        summary: response.summary,
      };
      const nextSessions: Partial<Record<QuizSubject, SubjectSession>> = {
        ...sessions,
        [activeSubject]: updatedSession,
      };
      setSessions(nextSessions);

      const hasNextSubject = subjectIndex + 1 < SUBJECT_ORDER.length;
      if (hasNextSubject) {
        setPhase('segmentComplete');
        return;
      }

      const totals = aggregateScore(nextSessions);
      recordQuizComplete(totals.correct, totals.total);

      if (taskId) {
        setIsUpdatingTask(true);
        try {
          await updatePlannerTask(taskId, 'completed');
          setTaskUpdateMessage('Daily mini-set complete and planner task marked done.');
        } catch (err) {
          setTaskUpdateMessage(getApiErrorMessage(err, 'Mini-set completed, but planner task update failed.'));
        } finally {
          setIsUpdatingTask(false);
        }
      }

      setPhase('results');
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to finalize this subject segment.'));
    } finally {
      setIsFinishingSegment(false);
    }
  }

  async function handleContinueFlow() {
    if (phase === 'review') {
      const totalQuestions = activeSession?.questions.length ?? 0;
      const hasMoreQuestions = currentQuestionIndex + 1 < totalQuestions;

      if (hasMoreQuestions) {
        setCurrentQuestionIndex((prev) => prev + 1);
        setLastReview(null);
        setPhase('playing');
        return;
      }

      await finalizeCurrentSegment();
      return;
    }

    if (phase === 'segmentComplete') {
      const nextIndex = subjectIndex + 1;
      const nextSubject = SUBJECT_ORDER[nextIndex];
      setSubjectIndex(nextIndex);
      setCurrentQuestionIndex(0);
      setSelectedAnswer('');
      setLastReview(null);
      await startSubjectSegment(nextSubject);
    }
  }

  const totals = aggregateScore(sessions);
  const percent = totals.total ? Math.round((totals.correct / totals.total) * 100) : 0;

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-3xl mx-auto space-y-4">
      <div className="flex items-center justify-between gap-3">
        <Button
          variant="flat"
          size="sm"
          startContent={<ArrowLeft className="w-4 h-4" />}
          onPress={() => navigate('/study-plan')}
        >
          Back to Study Plan
        </Button>
        <Chip variant="flat" color="secondary">
          Daily Mixed Mini-Set
        </Chip>
      </div>

      <Card className="glass">
        <CardHeader className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BrainCircuit className="w-5 h-5 text-secondary" />
            <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>
              Mixed Mini-Set
            </h1>
          </div>
          <Chip size="sm" variant="flat">
            {totals.correct}/{totals.total} correct
          </Chip>
        </CardHeader>
        <CardBody className="space-y-3">
          <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            Three quick segments across Physics, Chemistry, and Biology. Finish all segments to complete your daily mixed mini-set.
          </p>
          {plannerTopic ? (
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Focus topic: {plannerTopic}
            </p>
          ) : null}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            {SUBJECT_ORDER.map((subject) => {
              const session = sessions[subject];
              const isActive = subject === activeSubject && (phase === 'playing' || phase === 'review' || phase === 'segmentComplete');
              const subjectCorrect = session?.summary?.correct_answers ?? session?.answers.filter((entry) => entry.correct).length ?? 0;
              const subjectTotal = session?.summary?.total_questions ?? session?.answers.length ?? 0;
              const isDone = Boolean(session?.summary);

              return (
                <div
                  key={subject}
                  className="rounded-lg p-3"
                  style={{
                    border: isActive ? '1px solid var(--accent)' : '1px solid var(--border-subtle)',
                    background: isDone ? 'var(--green-soft)' : 'var(--bg-2)',
                  }}
                >
                  <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>{SUBJECT_LABELS[subject]}</p>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {isDone ? 'Completed' : isActive ? 'In progress' : 'Pending'}
                  </p>
                  <p style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                    {subjectCorrect}/{subjectTotal} correct
                  </p>
                </div>
              );
            })}
          </div>

          <Progress value={percent} color="secondary" classNames={{ track: 'bg-bg-5' }} />

          {error ? (
            <div className="rounded-lg p-2" style={{ background: 'var(--red-soft)', border: '1px solid var(--red-border)' }}>
              <p style={{ fontSize: 12, color: 'var(--red)' }}>{error}</p>
            </div>
          ) : null}

          {taskUpdateMessage ? (
            <div className="rounded-lg p-2" style={{ background: 'var(--green-soft)', border: '1px solid var(--green-border)' }}>
              <p style={{ fontSize: 12, color: 'var(--green)' }}>{taskUpdateMessage}</p>
            </div>
          ) : null}

          {phase === 'setup' ? (
            <div className="space-y-2">
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {QUESTIONS_PER_SUBJECT} questions per subject at mixed difficulty.
              </p>
              <Button
                color="secondary"
                startContent={<Sparkles className="w-4 h-4" />}
                onPress={() => void handleStartMiniSet()}
                isLoading={isLoadingSegment}
              >
                Start Mini-Set
              </Button>
            </div>
          ) : null}

          {(phase === 'playing' || phase === 'review') && activeSession && activeQuestion ? (
            <div className="space-y-3">
              <Divider />
              <div className="flex items-center justify-between">
                <Chip size="sm" variant="flat" color="secondary">
                  {SUBJECT_LABELS[activeSubject]} Q{activeQuestion.question_no}
                </Chip>
                <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  Question {currentQuestionIndex + 1} of {activeSession.questions.length}
                </p>
              </div>

              <p style={{ fontSize: 14, color: 'var(--text-primary)', fontWeight: 500 }}>
                {activeQuestion.question_text}
              </p>

              <RadioGroup
                value={selectedAnswer}
                onValueChange={setSelectedAnswer}
                isDisabled={phase === 'review'}
              >
                {activeQuestion.options.map((option) => (
                  <Radio key={option} value={option}>
                    {option}
                  </Radio>
                ))}
              </RadioGroup>

              {phase === 'playing' ? (
                <Button
                  color="secondary"
                  endContent={<ArrowRight className="w-4 h-4" />}
                  onPress={() => void handleSubmitAnswer()}
                  isDisabled={!selectedAnswer}
                  isLoading={isSubmittingAnswer}
                >
                  Check Answer
                </Button>
              ) : null}

              {phase === 'review' && lastReview ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    {lastReview.correct ? (
                      <CheckCircle2 className="w-4 h-4 text-success" />
                    ) : (
                      <XCircle className="w-4 h-4 text-danger" />
                    )}
                    <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{lastReview.explanation}</p>
                  </div>
                  <Button
                    color="secondary"
                    endContent={<ArrowRight className="w-4 h-4" />}
                    onPress={() => void handleContinueFlow()}
                    isLoading={isFinishingSegment}
                  >
                    {currentQuestionIndex + 1 < activeSession.questions.length
                      ? 'Next Question'
                      : `Finish ${SUBJECT_LABELS[activeSubject]} Segment`}
                  </Button>
                </div>
              ) : null}
            </div>
          ) : null}

          {phase === 'segmentComplete' ? (
            <div className="space-y-2">
              <Divider />
              <p style={{ fontSize: 13, color: 'var(--text-primary)', fontWeight: 500 }}>
                {SUBJECT_LABELS[activeSubject]} segment complete.
              </p>
              <Button
                color="secondary"
                endContent={<ArrowRight className="w-4 h-4" />}
                onPress={() => void handleContinueFlow()}
                isLoading={isLoadingSegment}
              >
                Continue to {SUBJECT_LABELS[SUBJECT_ORDER[subjectIndex + 1]]}
              </Button>
            </div>
          ) : null}

          {phase === 'results' ? (
            <div className="space-y-3">
              <Divider />
              <div className="flex items-center gap-2">
                <Trophy className="w-5 h-5 text-warning" />
                <p style={{ fontSize: 16, color: 'var(--text-primary)', fontWeight: 600 }}>
                  Mini-Set Complete
                </p>
              </div>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                Final score: {totals.correct}/{totals.total} ({percent}%)
              </p>
            </div>
          ) : null}
        </CardBody>
        <CardFooter className="justify-between">
          <Button variant="flat" onPress={() => navigate('/study-plan')}>
            Return to Plan
          </Button>
          {phase === 'results' ? (
            <Button
              color="secondary"
              onPress={() => void handleStartMiniSet()}
              isDisabled={isUpdatingTask}
              isLoading={isLoadingSegment}
            >
              Try Again
            </Button>
          ) : null}
        </CardFooter>
      </Card>

      {(isLoadingSegment || isUpdatingTask) && (
        <div className="flex items-center gap-2" style={{ color: 'var(--text-muted)', fontSize: 12 }}>
          <Spinner size="sm" color="secondary" />
          {isLoadingSegment ? 'Preparing next segment...' : 'Updating planner task...'}
        </div>
      )}
    </motion.div>
  );
}
