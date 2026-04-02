import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Button,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  Chip,
  Input,
  Progress,
  Spinner,
  Textarea,
} from '@heroui/react';
import { motion } from 'framer-motion';
import { ArrowLeft, Play, Timer, Trophy } from 'lucide-react';

import { getApiErrorMessage } from '../lib/api';
import {
  finishStaminaSession,
  startStaminaSession,
  type FinishStaminaBlockResult,
  type FinishStaminaSessionResponse,
  type StaminaErrorReason,
  type StaminaMode,
  type StartStaminaSessionResponse,
} from '../lib/examService';
import { updatePlannerTask } from '../lib/plannerInsightsService';

const SUBJECTS = ['physics', 'chemistry', 'biology'] as const;
const ERROR_REASONS: StaminaErrorReason[] = [
  'formula_error',
  'concept_confusion',
  'misread',
  'time_pressure',
  'other',
];

function formatCountdown(seconds: number) {
  const mins = Math.floor(Math.max(0, seconds) / 60)
    .toString()
    .padStart(2, '0');
  const secs = Math.floor(Math.max(0, seconds) % 60)
    .toString()
    .padStart(2, '0');
  return `${mins}:${secs}`;
}

export function ExamStaminaPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const taskId = searchParams.get('taskId')?.trim() || '';
  const plannerSubjectRaw = searchParams.get('subject')?.trim().toLowerCase() || '';
  const plannerTopicRaw = searchParams.get('topic')?.trim() || '';

  const plannerSubject = useMemo(() => {
    return SUBJECTS.find((item) => item === plannerSubjectRaw);
  }, [plannerSubjectRaw]);

  const [mode, setMode] = useState<StaminaMode>(plannerSubject ? 'subject' : 'mixed');
  const [subject, setSubject] = useState<(typeof SUBJECTS)[number]>(plannerSubject ?? 'physics');
  const [topic, setTopic] = useState(plannerTopicRaw);
  const [durationMinutes, setDurationMinutes] = useState('30');
  const [plannedQuestions, setPlannedQuestions] = useState('30');
  const [blockCount, setBlockCount] = useState('3');

  const [session, setSession] = useState<StartStaminaSessionResponse | null>(null);
  const [activeBlockIndex, setActiveBlockIndex] = useState(0);
  const [blockResults, setBlockResults] = useState<FinishStaminaBlockResult[]>([]);
  const [countdownSec, setCountdownSec] = useState(0);

  const [attemptedQuestions, setAttemptedQuestions] = useState('10');
  const [correctAnswers, setCorrectAnswers] = useState('7');
  const [dominantError, setDominantError] = useState<StaminaErrorReason>('concept_confusion');
  const [notes, setNotes] = useState('');

  const [phase, setPhase] = useState<'setup' | 'running' | 'results'>('setup');
  const [result, setResult] = useState<FinishStaminaSessionResponse | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [isStarting, setIsStarting] = useState(false);
  const [isFinishing, setIsFinishing] = useState(false);

  const activePlanBlock = session?.block_plan?.[activeBlockIndex];

  useEffect(() => {
    if (phase !== 'running') {
      return;
    }

    const timer = window.setInterval(() => {
      setCountdownSec((prev) => {
        if (prev <= 1) {
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => window.clearInterval(timer);
  }, [phase]);

  async function handleStart() {
    const duration = Number.parseInt(durationMinutes, 10);
    const questions = Number.parseInt(plannedQuestions, 10);
    const blocks = Number.parseInt(blockCount, 10);

    if (!Number.isFinite(duration) || duration < 10 || duration > 180) {
      setError('Duration must be between 10 and 180 minutes.');
      return;
    }
    if (!Number.isFinite(questions) || questions < 5 || questions > 300) {
      setError('Planned questions must be between 5 and 300.');
      return;
    }
    if (!Number.isFinite(blocks) || blocks < 1 || blocks > 6) {
      setError('Block count must be between 1 and 6.');
      return;
    }

    setIsStarting(true);
    setError(null);
    setStatusMessage(null);

    try {
      const started = await startStaminaSession({
        mode,
        subject: mode === 'subject' ? subject : undefined,
        topic: topic.trim() || undefined,
        durationMinutes: duration,
        plannedQuestions: questions,
        blockCount: blocks,
      });

      setSession(started);
      setActiveBlockIndex(0);
      setBlockResults([]);
      setCountdownSec((started.block_plan?.[0]?.planned_minutes ?? 1) * 60);
      setAttemptedQuestions(String(started.block_plan?.[0]?.planned_questions ?? 10));
      setCorrectAnswers('0');
      setDominantError('concept_confusion');
      setResult(null);
      setPhase('running');
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to start stamina drill.'));
    } finally {
      setIsStarting(false);
    }
  }

  async function handleCompleteBlock() {
    if (!session || !activePlanBlock) {
      return;
    }

    const attempted = Number.parseInt(attemptedQuestions, 10);
    const correct = Number.parseInt(correctAnswers, 10);

    if (!Number.isFinite(attempted) || attempted < 0) {
      setError('Attempted questions must be 0 or higher.');
      return;
    }
    if (!Number.isFinite(correct) || correct < 0 || correct > attempted) {
      setError('Correct answers must be between 0 and attempted questions.');
      return;
    }

    setError(null);
    const plannedSec = activePlanBlock.planned_minutes * 60;
    const elapsedSec = Math.max(1, plannedSec - countdownSec);

    const nextResults = [
      ...blockResults,
      {
        block_no: activePlanBlock.block_no,
        attempted_questions: attempted,
        correct_answers: correct,
        elapsed_sec: elapsedSec,
        dominant_error: dominantError,
      },
    ];

    const hasNext = activeBlockIndex + 1 < session.block_plan.length;
    if (hasNext) {
      const nextIndex = activeBlockIndex + 1;
      const nextBlock = session.block_plan[nextIndex];
      setBlockResults(nextResults);
      setActiveBlockIndex(nextIndex);
      setCountdownSec(nextBlock.planned_minutes * 60);
      setAttemptedQuestions(String(nextBlock.planned_questions));
      setCorrectAnswers('0');
      setDominantError('concept_confusion');
      return;
    }

    setIsFinishing(true);
    try {
      const finished = await finishStaminaSession(session.session_id, {
        blockResults: nextResults,
        notes: notes.trim() || undefined,
      });
      setResult(finished);
      setPhase('results');

      if (taskId) {
        try {
          await updatePlannerTask(taskId, 'completed');
          setStatusMessage('Stamina drill complete and planner task marked done.');
        } catch (taskErr) {
          setStatusMessage(getApiErrorMessage(taskErr, 'Stamina completed, but planner task update failed.'));
        }
      }
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to finish stamina drill.'));
    } finally {
      setIsFinishing(false);
    }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-3xl mx-auto space-y-4">
      <div className="flex items-center justify-between gap-2">
        <Button variant="flat" size="sm" startContent={<ArrowLeft className="w-4 h-4" />} onPress={() => navigate('/study-plan')}>
          Back to Study Plan
        </Button>
        <Chip color="secondary" variant="flat">Exam Stamina Drill</Chip>
      </div>

      <Card className="glass">
        <CardHeader className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Timer className="w-5 h-5 text-secondary" />
            <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>
              Timed Stamina Mode
            </h1>
          </div>
          {phase === 'running' ? (
            <Chip color={countdownSec <= 60 ? 'danger' : 'warning'} variant="flat">{formatCountdown(countdownSec)}</Chip>
          ) : null}
        </CardHeader>

        <CardBody className="space-y-3">
          {error ? (
            <div className="rounded-lg p-2" style={{ background: 'var(--red-soft)', border: '1px solid var(--red-border)' }}>
              <p style={{ fontSize: 12, color: 'var(--red)' }}>{error}</p>
            </div>
          ) : null}

          {statusMessage ? (
            <div className="rounded-lg p-2" style={{ background: 'var(--green-soft)', border: '1px solid var(--green-border)' }}>
              <p style={{ fontSize: 12, color: 'var(--green)' }}>{statusMessage}</p>
            </div>
          ) : null}

          {phase === 'setup' ? (
            <>
              <div className="flex items-center gap-2 flex-wrap">
                <Button size="sm" color={mode === 'mixed' ? 'secondary' : 'default'} variant={mode === 'mixed' ? 'solid' : 'flat'} onPress={() => setMode('mixed')}>
                  Mixed
                </Button>
                <Button size="sm" color={mode === 'subject' ? 'secondary' : 'default'} variant={mode === 'subject' ? 'solid' : 'flat'} onPress={() => setMode('subject')}>
                  Subject Focus
                </Button>
              </div>

              {mode === 'subject' ? (
                <div className="flex items-center gap-2 flex-wrap">
                  {SUBJECTS.map((item) => (
                    <Button
                      key={item}
                      size="sm"
                      variant={subject === item ? 'solid' : 'flat'}
                      color={subject === item ? 'secondary' : 'default'}
                      onPress={() => setSubject(item)}
                      className="capitalize"
                    >
                      {item}
                    </Button>
                  ))}
                </div>
              ) : null}

              <Input type="number" label="Duration (minutes)" min={10} max={180} value={durationMinutes} onValueChange={setDurationMinutes} size="sm" variant="bordered" />
              <Input type="number" label="Planned questions" min={5} max={300} value={plannedQuestions} onValueChange={setPlannedQuestions} size="sm" variant="bordered" />
              <Input type="number" label="Block count" min={1} max={6} value={blockCount} onValueChange={setBlockCount} size="sm" variant="bordered" />
              <Input label="Optional focus topic" value={topic} onValueChange={setTopic} size="sm" variant="bordered" />

              <Button color="secondary" startContent={<Play className="w-4 h-4" />} onPress={() => void handleStart()} isLoading={isStarting}>
                Start Drill
              </Button>
            </>
          ) : null}

          {phase === 'running' && session && activePlanBlock ? (
            <>
              <div className="flex items-center justify-between gap-2">
                <Chip variant="flat" color="secondary">Block {activePlanBlock.block_no} of {session.block_plan.length}</Chip>
                <Chip variant="flat">Target: {activePlanBlock.planned_questions} Q / {activePlanBlock.planned_minutes} min</Chip>
              </div>

              <Progress
                value={((activeBlockIndex + 1) / session.block_plan.length) * 100}
                color="secondary"
                classNames={{ track: 'bg-bg-5' }}
              />

              <Input
                type="number"
                label="Attempted questions"
                min={0}
                max={500}
                value={attemptedQuestions}
                onValueChange={setAttemptedQuestions}
                size="sm"
                variant="bordered"
              />
              <Input
                type="number"
                label="Correct answers"
                min={0}
                max={500}
                value={correctAnswers}
                onValueChange={setCorrectAnswers}
                size="sm"
                variant="bordered"
              />

              <div className="space-y-1">
                <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Dominant error for this block</p>
                <div className="flex items-center gap-2 flex-wrap">
                  {ERROR_REASONS.map((item) => (
                    <Button
                      key={item}
                      size="sm"
                      variant={dominantError === item ? 'solid' : 'flat'}
                      color={dominantError === item ? 'secondary' : 'default'}
                      onPress={() => setDominantError(item)}
                    >
                      {item.replace('_', ' ')}
                    </Button>
                  ))}
                </div>
              </div>

              <Textarea label="Session notes (optional)" value={notes} onValueChange={setNotes} minRows={2} maxRows={4} variant="bordered" />

              <Button color="secondary" onPress={() => void handleCompleteBlock()} isLoading={isFinishing}>
                {activeBlockIndex + 1 < session.block_plan.length ? 'Complete Block' : 'Finish Drill'}
              </Button>
            </>
          ) : null}

          {phase === 'results' && result ? (
            <>
              <div className="flex items-center gap-2">
                <Trophy className="w-5 h-5 text-warning" />
                <p style={{ fontSize: 16, color: 'var(--text-primary)', fontWeight: 600 }}>Drill Complete</p>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <Chip variant="flat">Score {result.score_percent.toFixed(1)}%</Chip>
                <Chip variant="flat">Pacing {result.pacing_qph.toFixed(1)} q/h</Chip>
                <Chip variant="flat" color={result.fatigue_detected ? 'danger' : 'success'}>
                  Fatigue dip {result.fatigue_accuracy_dip.toFixed(1)}%
                </Chip>
                <Chip variant="flat" color="warning">+{result.xp_awarded} XP</Chip>
              </div>

              {Object.keys(result.error_clusters || {}).length ? (
                <div className="space-y-1">
                  <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Error clusters</p>
                  <div className="flex items-center gap-2 flex-wrap">
                    {Object.entries(result.error_clusters).map(([key, count]) => (
                      <Chip key={key} size="sm" variant="flat">{key.replace('_', ' ')}: {count}</Chip>
                    ))}
                  </div>
                </div>
              ) : null}
            </>
          ) : null}
        </CardBody>

        <CardFooter className="justify-between">
          <Button variant="flat" onPress={() => navigate('/study-plan')}>Return to Plan</Button>
          {phase === 'results' ? (
            <Button color="secondary" onPress={() => setPhase('setup')}>Start Another Drill</Button>
          ) : null}
        </CardFooter>
      </Card>

      {(isStarting || isFinishing) ? (
        <div className="flex items-center gap-2" style={{ color: 'var(--text-muted)', fontSize: 12 }}>
          <Spinner size="sm" color="secondary" />
          {isStarting ? 'Preparing stamina session...' : 'Saving drill results...'}
        </div>
      ) : null}
    </motion.div>
  );
}
