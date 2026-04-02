import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  CardBody,
  CardHeader,
  CardFooter,
  Button,
  Chip,
  Progress,
  RadioGroup,
  Radio,
  Breadcrumbs,
  BreadcrumbItem,
  Divider,
} from '@heroui/react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BrainCircuit,
  CheckCircle2,
  XCircle,
  ArrowRight,
  RotateCcw,
  Trophy,
  ArrowLeft,
  Zap,
} from 'lucide-react';
import {
  abandonQuiz,
  deleteQuiz,
  finishQuiz,
  getQuiz,
  getQuizQuestions,
  getQuizResults,
  listQuizHistoryPaged,
  updateQuizAnswer,
  type QuizQuestion,
  type QuizDifficulty,
  type QuizMeta,
  type QuizResultsPayload,
  startQuiz as startQuizAttempt,
  submitQuizAnswer,
  type QuizSummary,
} from '../lib/quizService';
import { getApiErrorMessage } from '../lib/api';
import { useGamificationStore } from '../store/gamificationStore';

type Phase = 'setup' | 'playing' | 'review' | 'results' | 'history';
const HISTORY_PAGE_SIZE = 8;

function buildExplanation(params: {
  isCorrect: boolean;
  userAnswer: string;
  correctAnswer: string;
  backendExplanation?: string;
  questionExplanation?: string;
}) {
  const fromBackend = params.backendExplanation?.trim();
  if (fromBackend && fromBackend.toLowerCase() !== 'explanation not available.') {
    return fromBackend;
  }

  const fromQuestion = params.questionExplanation?.trim();
  if (fromQuestion) {
    return fromQuestion;
  }

  if (params.isCorrect) {
    if (params.correctAnswer) {
      return `Correct. ${params.correctAnswer} is the right answer for this question.`;
    }
    return 'Correct. Your chosen option matches the expected answer.';
  }

  if (params.correctAnswer) {
    return `Incorrect. You selected ${params.userAnswer}, but the correct answer is ${params.correctAnswer}.`;
  }

  return 'Incorrect. Review the concept and compare each option carefully.';
}

export function QuizPage() {
  const { subject } = useParams<{ subject: string; lessonId: string }>();
  const navigate = useNavigate();
  const { recordQuizComplete } = useGamificationStore();

  const [phase, setPhase] = useState<Phase>('setup');
  const [difficulty, setDifficulty] = useState<QuizDifficulty>('medium');
  const [questionCount, setQuestionCount] = useState(5);
  const [quizId, setQuizId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [currentQ, setCurrentQ] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState('');
  const [answers, setAnswers] = useState<Array<{
    question: QuizQuestion;
    userAnswer: string;
    correctAnswer?: string;
    correct: boolean;
    explanation: string;
  }>>([]);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [abandoning, setAbandoning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<{ correct: boolean; explanation: string } | null>(null);
  const [finalSummary, setFinalSummary] = useState<QuizSummary | null>(null);
  const [quizHistory, setQuizHistory] = useState<QuizMeta[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [selectedHistoryQuizId, setSelectedHistoryQuizId] = useState<string | null>(null);
  const [selectedHistoryMeta, setSelectedHistoryMeta] = useState<QuizMeta | null>(null);
  const [selectedHistoryResults, setSelectedHistoryResults] = useState<QuizResultsPayload | null>(null);
  const [selectedHistoryQuestions, setSelectedHistoryQuestions] = useState<QuizQuestion[]>([]);
  const [historyDetailLoading, setHistoryDetailLoading] = useState(false);
  const [historyQuestionLoading, setHistoryQuestionLoading] = useState(false);
  const [historyDeleteLoading, setHistoryDeleteLoading] = useState<string | null>(null);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyOffset, setHistoryOffset] = useState(0);
  const [historyStatus, setHistoryStatus] = useState<'all' | 'active' | 'completed' | 'abandoned'>('completed');
  const [historyDifficulty, setHistoryDifficulty] = useState<'all' | QuizDifficulty>('all');

  const historyPage = Math.floor(historyOffset / HISTORY_PAGE_SIZE) + 1;
  const totalHistoryPages = Math.max(1, Math.ceil(historyTotal / HISTORY_PAGE_SIZE));

  async function loadQuizHistoryDetails(quizIdToView: string) {
    const [meta, result] = await Promise.all([
      getQuiz(quizIdToView),
      getQuizResults(quizIdToView),
    ]);
    setSelectedHistoryQuizId(quizIdToView);
    setSelectedHistoryMeta(meta);
    setSelectedHistoryResults(result);
    setSelectedHistoryQuestions([]);
  }

  async function loadQuizQuestionDetails(quizIdToView: string) {
    const [meta, questionsPayload] = await Promise.all([
      getQuiz(quizIdToView),
      getQuizQuestions(quizIdToView),
    ]);
    setSelectedHistoryQuizId(quizIdToView);
    setSelectedHistoryMeta(meta);
    setSelectedHistoryQuestions(questionsPayload);
    setSelectedHistoryResults(null);
  }

  async function loadQuizHistory() {
    const normalizedSubject = subject?.toLowerCase();
    const quizSubject =
      normalizedSubject === 'physics' || normalizedSubject === 'chemistry' || normalizedSubject === 'biology'
        ? normalizedSubject
        : undefined;

    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const response = await listQuizHistoryPaged({
        subject: quizSubject,
        status: historyStatus === 'all' ? undefined : historyStatus,
        difficulty: historyDifficulty === 'all' ? undefined : historyDifficulty,
        limit: HISTORY_PAGE_SIZE,
        offset: historyOffset,
      });
      setQuizHistory(response.quizzes);
      setHistoryTotal(response.total);

      if (
        selectedHistoryQuizId &&
        !response.quizzes.some((quiz) => quiz.id === selectedHistoryQuizId)
      ) {
        setSelectedHistoryQuizId(null);
        setSelectedHistoryMeta(null);
        setSelectedHistoryResults(null);
        setSelectedHistoryQuestions([]);
      }
    } catch (err) {
      setHistoryError(getApiErrorMessage(err, 'Unable to load quiz history.'));
    } finally {
      setHistoryLoading(false);
    }
  }

  useEffect(() => {
    void loadQuizHistory();
  }, [subject, historyStatus, historyDifficulty, historyOffset]);

  useEffect(() => {
    const activeQuestion = questions[currentQ];
    if (!activeQuestion) return;
    const existing = answers.find((entry) => entry.question.id === activeQuestion.id);
    setSelectedAnswer(existing?.userAnswer ?? '');
  }, [answers, currentQ, questions]);

  async function handleStartQuiz() {
    setLoading(true);
    setError(null);
    try {
      const normalizedSubject = subject?.toLowerCase();
      const quizSubject =
        normalizedSubject === 'physics' || normalizedSubject === 'chemistry' || normalizedSubject === 'biology'
          ? normalizedSubject
          : 'biology';

      const res = await startQuizAttempt(quizSubject, difficulty, questionCount);
      setQuizId(res.quiz.id);
      setQuestions(res.questions || []);
      setCurrentQ(0);
      setSelectedAnswer('');
      setAnswers([]);
      setFinalSummary(null);
      setPhase('playing');
    } catch (err) {
      console.error('Failed to generate quiz:', err);
      setError(getApiErrorMessage(err, 'Failed to generate quiz right now.'));
    } finally {
      setLoading(false);
    }
  }

  async function handleViewHistory(quizIdToView: string) {
    if (historyDetailLoading) return;

    if (selectedHistoryQuizId === quizIdToView) {
      setSelectedHistoryQuizId(null);
      setSelectedHistoryMeta(null);
      setSelectedHistoryResults(null);
      setSelectedHistoryQuestions([]);
      return;
    }

    setHistoryDetailLoading(true);
    setHistoryError(null);
    try {
      await loadQuizHistoryDetails(quizIdToView);
    } catch (err) {
      setHistoryError(getApiErrorMessage(err, 'Unable to load selected quiz results.'));
    } finally {
      setHistoryDetailLoading(false);
    }
  }

  async function handleViewHistoryQuestions(quizIdToView: string) {
    if (historyQuestionLoading) return;

    if (selectedHistoryQuizId === quizIdToView && selectedHistoryQuestions.length) {
      setSelectedHistoryQuizId(null);
      setSelectedHistoryMeta(null);
      setSelectedHistoryQuestions([]);
      setSelectedHistoryResults(null);
      return;
    }

    setHistoryQuestionLoading(true);
    setHistoryError(null);
    try {
      await loadQuizQuestionDetails(quizIdToView);
    } catch (err) {
      setHistoryError(getApiErrorMessage(err, 'Unable to load selected quiz questions.'));
    } finally {
      setHistoryQuestionLoading(false);
    }
  }

  async function handleDeleteHistoryQuiz(quizIdToDelete: string) {
    if (historyDeleteLoading) return;
    setHistoryDeleteLoading(quizIdToDelete);
    setHistoryError(null);
    try {
      await deleteQuiz(quizIdToDelete);
      if (selectedHistoryQuizId === quizIdToDelete) {
        setSelectedHistoryQuizId(null);
        setSelectedHistoryMeta(null);
        setSelectedHistoryResults(null);
        setSelectedHistoryQuestions([]);
      }
      await loadQuizHistory();
    } catch (err) {
      setHistoryError(getApiErrorMessage(err, 'Unable to delete this quiz attempt.'));
    } finally {
      setHistoryDeleteLoading(null);
    }
  }

  async function handleOpenHistoryResults(quizIdToView: string) {
    if (historyDetailLoading) return;
    setHistoryDetailLoading(true);
    setHistoryError(null);
    try {
      await loadQuizHistoryDetails(quizIdToView);
      setPhase('history');
    } catch (err) {
      setHistoryError(getApiErrorMessage(err, 'Unable to open quiz results.'));
    } finally {
      setHistoryDetailLoading(false);
    }
  }

  async function handleSubmitAnswer() {
    if (!quizId || !questions[currentQ] || !selectedAnswer) return;
    const question = questions[currentQ];
    const hasExistingAnswer = answers.some((entry) => entry.question.id === question.id);
    setChecking(true);

    try {
      const res = hasExistingAnswer
        ? await updateQuizAnswer(quizId, question.id, selectedAnswer, 3)
        : await submitQuizAnswer(quizId, question.id, selectedAnswer, 3);

      const result = {
        question,
        userAnswer: selectedAnswer,
        correctAnswer: res.result.correct_answer,
        correct: res.result.is_correct,
        explanation: buildExplanation({
          isCorrect: res.result.is_correct,
          userAnswer: selectedAnswer,
          correctAnswer: res.result.correct_answer,
          backendExplanation: res.result.explanation || undefined,
        }),
      };
      setAnswers((prev) => {
        const existingIndex = prev.findIndex((entry) => entry.question.id === question.id);
        if (existingIndex === -1) {
          return [...prev, result];
        }
        const next = [...prev];
        next[existingIndex] = result;
        return next;
      });
      setLastResult({ correct: res.result.is_correct, explanation: result.explanation });
      setPhase('review');
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to submit answer. Please try again.'));
    } finally {
      setChecking(false);
    }
  }

  async function nextQuestion() {
    if (!questions.length) return;
    setSelectedAnswer('');
    setLastResult(null);
    if (currentQ + 1 < questions.length) {
      setCurrentQ(currentQ + 1);
      setPhase('playing');
    } else {
      const score = answers.filter((a) => a.correct).length;
      const total = answers.length;
      try {
        if (quizId) {
          const finish = await finishQuiz(quizId);
          setFinalSummary(finish.summary);
        }
      } catch (err) {
        setError(getApiErrorMessage(err, 'Unable to finalize quiz summary. Showing local results.'));
      }
      recordQuizComplete(score, total);
      void loadQuizHistory();
      setPhase('results');
    }
  }

  function goToPreviousQuestion() {
    if (currentQ === 0) return;
    setLastResult(null);
    setPhase('playing');
    setCurrentQ((prev) => Math.max(0, prev - 1));
  }

  async function handleAbandonActiveQuiz() {
    if (!quizId || abandoning) return;
    setAbandoning(true);
    setError(null);
    try {
      await abandonQuiz(quizId);
      setQuizId(null);
      setQuestions([]);
      setCurrentQ(0);
      setSelectedAnswer('');
      setAnswers([]);
      setLastResult(null);
      setFinalSummary(null);
      setPhase('setup');
      await loadQuizHistory();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to abandon the active quiz.'));
    } finally {
      setAbandoning(false);
    }
  }

  const subjectLabels: Record<string, string> = {
    physics: 'Physics',
    chemistry: 'Chemistry',
    biology: 'Biology',
  };

  const localScore = answers.filter((a) => a.correct).length;
  const localTotal = answers.length;
  const score = finalSummary?.correct_answers ?? localScore;
  const total = finalSummary?.total_questions ?? localTotal;
  const scorePercent = Math.round(finalSummary?.score_percent ?? (total > 0 ? (score / total) * 100 : 0));

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <Breadcrumbs aria-label="Quiz page breadcrumbs">
        <BreadcrumbItem onPress={() => navigate('/home')}>Home</BreadcrumbItem>
        <BreadcrumbItem onPress={() => navigate(`/subject/${subject}`)}>
          {subjectLabels[subject || ''] || subject}
        </BreadcrumbItem>
        <BreadcrumbItem>Quiz</BreadcrumbItem>
      </Breadcrumbs>

      <AnimatePresence mode="wait">
        {/* Setup phase */}
        {phase === 'setup' && (
          <motion.div key="setup" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}>
            <Card className="glass">
              <CardHeader className="flex items-center gap-2 pb-2">
                <BrainCircuit className="w-5 h-5 text-secondary" />
                <h2 className="ui-section-title" style={{ fontSize: 18 }}>Quiz Setup</h2>
              </CardHeader>
              <CardBody className="gap-5">
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">Difficulty</label>
                  <div className="flex gap-2">
                    {(['easy', 'medium', 'hard'] as QuizDifficulty[]).map((d) => (
                      <Button
                        key={d}
                        variant={difficulty === d ? 'solid' : 'bordered'}
                        color={
                          d === 'easy' ? 'success' : d === 'medium' ? 'warning' : 'danger'
                        }
                        size="sm"
                        onPress={() => setDifficulty(d)}
                        className="capitalize"
                      >
                        {d}
                      </Button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-text-secondary mb-2 block">Questions</label>
                  <div className="flex gap-2">
                    {[5, 10, 15, 20].map((n) => (
                      <Button
                        key={n}
                        variant={questionCount === n ? 'solid' : 'bordered'}
                        color={questionCount === n ? 'secondary' : 'default'}
                        size="sm"
                        onPress={() => setQuestionCount(n)}
                      >
                        {n}
                      </Button>
                    ))}
                  </div>
                </div>

                <Divider />

                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <label className="text-sm font-medium text-text-secondary">
                      Recent Attempts ({historyTotal})
                    </label>
                    <Button
                      size="sm"
                      variant="light"
                      color="secondary"
                      isLoading={historyLoading}
                      onPress={() => void loadQuizHistory()}
                    >
                      Refresh
                    </Button>
                  </div>

                  <div className="space-y-1.5">
                    <p className="text-xs text-text-muted">Status</p>
                    <div className="flex items-center gap-2 flex-wrap">
                      {(['all', 'completed', 'active', 'abandoned'] as const).map((statusValue) => (
                        <Button
                          key={statusValue}
                          size="sm"
                          variant={historyStatus === statusValue ? 'flat' : 'bordered'}
                          color={historyStatus === statusValue ? 'secondary' : 'default'}
                          className="capitalize"
                          onPress={() => {
                            setHistoryStatus(statusValue);
                            setHistoryOffset(0);
                          }}
                        >
                          {statusValue}
                        </Button>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <p className="text-xs text-text-muted">Difficulty</p>
                    <div className="flex items-center gap-2 flex-wrap">
                      {(['all', 'easy', 'medium', 'hard', 'mixed'] as const).map((difficultyValue) => (
                        <Button
                          key={difficultyValue}
                          size="sm"
                          variant={historyDifficulty === difficultyValue ? 'flat' : 'bordered'}
                          color={historyDifficulty === difficultyValue ? 'secondary' : 'default'}
                          className="capitalize"
                          onPress={() => {
                            setHistoryDifficulty(difficultyValue);
                            setHistoryOffset(0);
                          }}
                        >
                          {difficultyValue}
                        </Button>
                      ))}
                    </div>
                  </div>

                  {historyError ? (
                    <Chip color="danger" variant="flat" size="sm" className="w-full justify-center">
                      {historyError}
                    </Chip>
                  ) : null}

                  {historyLoading ? (
                    <p className="text-xs text-text-muted">Loading recent attempts...</p>
                  ) : quizHistory.length ? (
                    <div className="space-y-2">
                      {quizHistory.map((quiz) => {
                        const isSelected = selectedHistoryQuizId === quiz.id;
                        return (
                          <Card key={quiz.id} className="glass border border-border-default">
                            <CardBody className="p-3 space-y-2">
                              <div className="flex items-center justify-between gap-2">
                                <div>
                                  <p className="text-sm font-medium capitalize">{quiz.subject} • {quiz.difficulty}</p>
                                  <p className="text-xs text-text-muted">
                                    {new Date(quiz.started_at).toLocaleString()} • {quiz.question_count} questions
                                  </p>
                                </div>
                                <div className="flex items-center gap-1.5 flex-wrap justify-end">
                                  <Button
                                    size="sm"
                                    variant={isSelected ? 'flat' : 'bordered'}
                                    color="secondary"
                                    isLoading={historyDetailLoading && isSelected}
                                    onPress={() => void handleViewHistory(quiz.id)}
                                  >
                                    {isSelected ? 'Hide' : 'Review'}
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="bordered"
                                    color="default"
                                    isLoading={historyQuestionLoading && selectedHistoryQuizId === quiz.id}
                                    onPress={() => void handleViewHistoryQuestions(quiz.id)}
                                  >
                                    Questions
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="flat"
                                    color="primary"
                                    isLoading={historyDetailLoading && selectedHistoryQuizId === quiz.id}
                                    onPress={() => void handleOpenHistoryResults(quiz.id)}
                                  >
                                    Results
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="flat"
                                    color="danger"
                                    isLoading={historyDeleteLoading === quiz.id}
                                    onPress={() => void handleDeleteHistoryQuiz(quiz.id)}
                                  >
                                    Delete
                                  </Button>
                                </div>
                              </div>

                              {isSelected && selectedHistoryMeta && selectedHistoryResults ? (
                                <div className="space-y-2 rounded-lg border border-border-default p-2">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <Chip size="sm" variant="flat" color="secondary">
                                      status: {selectedHistoryMeta.status}
                                    </Chip>
                                    <Chip size="sm" variant="flat">
                                      score: {Math.round(selectedHistoryResults.summary?.score_percent ?? 0)}%
                                    </Chip>
                                    <Chip size="sm" variant="flat" color="success">
                                      {selectedHistoryResults.summary?.correct_answers ?? 0}/{selectedHistoryResults.summary?.total_questions ?? 0} correct
                                    </Chip>
                                  </div>
                                  <div className="space-y-1">
                                    {selectedHistoryResults.questions.slice(0, 3).map((q) => (
                                      <div key={`${selectedHistoryMeta.id}-${q.question_no}`} className="rounded-md border border-border-default p-2">
                                        <p className="text-xs font-medium">Q{q.question_no}. {q.question_text}</p>
                                        <p className="text-[11px] text-text-muted mt-1">
                                          You: {q.user_answer || 'Not answered'} • Correct: {q.correct_answer}
                                        </p>
                                      </div>
                                    ))}
                                  </div>
                                  <Button
                                    size="sm"
                                    variant="light"
                                    color="secondary"
                                    onPress={() => void handleOpenHistoryResults(quiz.id)}
                                  >
                                    Open Full Results
                                  </Button>
                                </div>
                              ) : null}

                              {isSelected && selectedHistoryMeta && selectedHistoryQuestions.length ? (
                                <div className="space-y-2 rounded-lg border border-border-default p-2">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <Chip size="sm" variant="flat" color="secondary">
                                      Question set
                                    </Chip>
                                    <Chip size="sm" variant="flat">
                                      {selectedHistoryQuestions.length} questions
                                    </Chip>
                                  </div>
                                  <div className="space-y-1">
                                    {selectedHistoryQuestions.slice(0, 4).map((q) => (
                                      <div key={`${selectedHistoryMeta.id}-${q.question_no}-set`} className="rounded-md border border-border-default p-2">
                                        <p className="text-xs font-medium">Q{q.question_no}. {q.question_text}</p>
                                        <p className="text-[11px] text-text-muted mt-1">
                                          {q.options.join(' | ')}
                                        </p>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              ) : null}
                            </CardBody>
                          </Card>
                        );
                      })}

                      <div className="flex items-center justify-between gap-2 flex-wrap pt-1">
                        <p className="text-xs text-text-muted">
                          Page {historyPage} of {totalHistoryPages}
                        </p>
                        <div className="flex items-center gap-2 flex-wrap justify-end">
                          <Button
                            size="sm"
                            variant="bordered"
                            isDisabled={historyOffset === 0 || historyLoading}
                            onPress={() => setHistoryOffset((prev) => Math.max(0, prev - HISTORY_PAGE_SIZE))}
                          >
                            Previous
                          </Button>
                          <Button
                            size="sm"
                            variant="bordered"
                            isDisabled={historyOffset + HISTORY_PAGE_SIZE >= historyTotal || historyLoading}
                            onPress={() => setHistoryOffset((prev) => prev + HISTORY_PAGE_SIZE)}
                          >
                            Next
                          </Button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-text-muted">No quizzes found for current filters.</p>
                  )}
                </div>
              </CardBody>
              {error && (
                <div className="px-4 pb-2">
                  <Chip color="danger" variant="flat" size="sm" className="w-full justify-center">
                    {error}
                  </Chip>
                </div>
              )}
              <CardFooter>
                <Button
                  color="secondary"
                  fullWidth
                  onPress={handleStartQuiz}
                  isLoading={loading}
                  startContent={!loading && <BrainCircuit className="w-4 h-4" />}
                >
                  Start Quiz
                </Button>
              </CardFooter>
            </Card>
          </motion.div>
        )}

        {/* Playing phase */}
        {phase === 'playing' && questions.length > 0 && (
          <motion.div key="playing" initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }}>
            <Card className="glass">
              <CardHeader className="flex flex-col gap-2 pb-2">
                <div className="w-full flex items-center justify-between">
                  <div className="flex items-center gap-2 flex-wrap justify-end">
                    <Chip size="sm" color="secondary" variant="flat">
                      Q {currentQ + 1} / {questions.length}
                    </Chip>
                    <Chip size="sm" variant="flat" color={
                      questions[currentQ].difficulty === 'easy' ? 'success' :
                        questions[currentQ].difficulty === 'medium' ? 'warning' : 'danger'
                    }>
                      {questions[currentQ].difficulty || difficulty}
                    </Chip>
                  </div>
                  <Button
                    size="sm"
                    variant="flat"
                    color="danger"
                    isLoading={abandoning}
                    onPress={() => void handleAbandonActiveQuiz()}
                  >
                    Abandon
                  </Button>
                </div>
                <Progress
                  value={((currentQ + 1) / questions.length) * 100}
                  color="secondary"
                  size="sm"
                  className="w-full"
                />
              </CardHeader>
              <CardBody className="gap-4">
                <h3 className="text-md font-semibold leading-relaxed">
                  {questions[currentQ].question_text}
                </h3>
                <RadioGroup
                  value={selectedAnswer}
                  onValueChange={setSelectedAnswer}
                  color="secondary"
                >
                  {questions[currentQ].options.map((opt, i) => (
                    <Radio key={i} value={opt} className="max-w-full">
                      <span className="text-sm">{opt}</span>
                    </Radio>
                  ))}
                </RadioGroup>
              </CardBody>
              <CardFooter className="gap-2">
                {currentQ > 0 ? (
                  <Button
                    variant="bordered"
                    onPress={goToPreviousQuestion}
                    isDisabled={checking || abandoning}
                  >
                    Previous
                  </Button>
                ) : null}
                <Button
                  color="secondary"
                  fullWidth={currentQ === 0}
                  onPress={handleSubmitAnswer}
                  isDisabled={!selectedAnswer || abandoning}
                  isLoading={checking}
                >
                  {answers.some((entry) => entry.question.id === questions[currentQ].id)
                    ? 'Update Answer'
                    : 'Submit Answer'}
                </Button>
              </CardFooter>
            </Card>
          </motion.div>
        )}

        {/* Review phase */}
        {phase === 'review' && lastResult && (
          <motion.div key="review" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}>
            <Card className={`glass ${lastResult.correct ? 'border-success/40' : 'border-danger/40'}`}>
              <CardBody className="gap-3 text-center py-6">
                {lastResult.correct ? (
                  <CheckCircle2 className="w-12 h-12 text-success mx-auto" />
                ) : (
                  <XCircle className="w-12 h-12 text-danger mx-auto" />
                )}
                <h3 className={`text-xl font-bold ${lastResult.correct ? 'text-success' : 'text-danger'}`}>
                  {lastResult.correct ? 'Correct! 🎉' : 'Incorrect'}
                </h3>
                {lastResult.correct && (
                  <Chip color="warning" variant="flat" startContent={<Zap className="w-3 h-3" />}>
                    +10 XP
                  </Chip>
                )}
                {lastResult.explanation && (
                  <>
                    <Divider />
                    <p className="text-sm text-left whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
                      {lastResult.explanation}
                    </p>
                  </>
                )}
              </CardBody>
              <CardFooter>
                <Button
                  color="secondary"
                  fullWidth
                  onPress={() => void nextQuestion()}
                  endContent={<ArrowRight className="w-4 h-4" />}
                >
                  {currentQ + 1 < questions.length ? 'Next Question' : 'See Results'}
                </Button>
              </CardFooter>
            </Card>
          </motion.div>
        )}

        {/* Results phase */}
        {phase === 'results' && (
          <motion.div key="results" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
            <Card className="glass text-center">
              <CardBody className="py-8 gap-3">
                <Trophy className="w-14 h-14 text-warning mx-auto" />
                <h2 className="ui-page-title" style={{ justifyContent: 'center', fontSize: 24 }}>Quiz Complete!</h2>
                <p className="text-4xl font-bold" style={{ color: 'var(--accent)' }}>{scorePercent}%</p>
                <p className="text-text-muted">{score} / {total} correct</p>
                <div className="flex gap-2 justify-center mt-2">
                  <Chip color="warning" variant="flat" startContent={<Zap className="w-3 h-3" />}>
                    +{finalSummary?.xp_awarded ?? (50 + Math.round((score / Math.max(total, 1)) * 100))} XP
                  </Chip>
                </div>
              </CardBody>
              <CardFooter className="flex gap-2 justify-center">
                <Button
                  variant="flat"
                  onPress={() => {
                    setPhase('setup');
                    setQuizId(null);
                    setQuestions([]);
                    setAnswers([]);
                    setCurrentQ(0);
                    setSelectedAnswer('');
                    setLastResult(null);
                    setFinalSummary(null);
                    setError(null);
                  }}
                  startContent={<RotateCcw className="w-4 h-4" />}
                >
                  Retry
                </Button>
                <Button
                  color="secondary"
                  onPress={() => navigate(`/subject/${subject}`)}
                  startContent={<ArrowLeft className="w-4 h-4" />}
                >
                  Back to Lessons
                </Button>
              </CardFooter>
            </Card>

            {/* Answer review */}
            <div className="space-y-2">
              <h3 className="ui-section-title" style={{ fontSize: 14 }}>Answer Review</h3>
              {answers.map((a, i) => (
                <Card key={i} className={`glass ${a.correct ? 'border-success/40' : 'border-danger/40'}`}>
                  <CardBody className="p-3">
                    <div className="flex items-start gap-2">
                      {a.correct ? (
                        <CheckCircle2 className="w-4 h-4 text-success shrink-0 mt-0.5" />
                      ) : (
                        <XCircle className="w-4 h-4 text-danger shrink-0 mt-0.5" />
                      )}
                      <div>
                        <p className="text-sm font-medium">{a.question.question_text}</p>
                        <p className="text-xs text-default-500 mt-1">
                          Your answer: <span className={a.correct ? 'text-success' : 'text-danger'}>{a.userAnswer}</span>
                          {!a.correct && a.correctAnswer ? <> • Correct: <span className="text-success">{a.correctAnswer}</span></> : null}
                        </p>
                      </div>
                    </div>
                  </CardBody>
                </Card>
              ))}
            </div>
          </motion.div>
        )}

        {/* History results phase */}
        {phase === 'history' && (
          <motion.div key="history" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
            <Card className="glass">
              <CardHeader className="flex items-center justify-between gap-2 pb-2">
                <div>
                  <h2 className="ui-section-title" style={{ fontSize: 18 }}>Quiz History Results</h2>
                  <p className="text-xs text-text-muted">
                    {selectedHistoryMeta
                      ? `${selectedHistoryMeta.subject} • ${new Date(selectedHistoryMeta.started_at).toLocaleString()}`
                      : 'Select an attempt from setup to view results.'}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="flat"
                  color="secondary"
                  startContent={<ArrowLeft className="w-4 h-4" />}
                  onPress={() => setPhase('setup')}
                >
                  Back
                </Button>
              </CardHeader>
              <CardBody className="space-y-3">
                {selectedHistoryMeta && selectedHistoryResults ? (
                  <>
                    <div className="flex items-center gap-2 flex-wrap">
                      <Chip size="sm" variant="flat" color="secondary">
                        status: {selectedHistoryMeta.status}
                      </Chip>
                      <Chip size="sm" variant="flat" color="success">
                        {selectedHistoryResults.summary?.correct_answers ?? 0}/{selectedHistoryResults.summary?.total_questions ?? 0} correct
                      </Chip>
                      <Chip size="sm" variant="flat">
                        score: {Math.round(selectedHistoryResults.summary?.score_percent ?? 0)}%
                      </Chip>
                      <Chip size="sm" variant="flat" color="warning">
                        +{selectedHistoryResults.summary?.xp_awarded ?? 0} XP
                      </Chip>
                    </div>

                    <div className="space-y-2">
                      {selectedHistoryResults.questions.map((q) => (
                        <Card key={`${selectedHistoryMeta.id}-${q.question_no}`} className="glass border border-border-default">
                          <CardBody className="p-3 space-y-1.5">
                            <div className="flex items-start justify-between gap-2">
                              <p className="text-sm font-medium">Q{q.question_no}. {q.question_text}</p>
                              <Chip
                                size="sm"
                                variant="flat"
                                color={q.is_correct ? 'success' : 'danger'}
                              >
                                {q.is_correct ? 'Correct' : 'Incorrect'}
                              </Chip>
                            </div>
                            <p className="text-xs text-text-muted">Your answer: {q.user_answer || 'Not answered'}</p>
                            <p className="text-xs text-text-muted">Correct answer: {q.correct_answer}</p>
                            {q.explanation ? (
                              <p className="text-xs text-text-secondary whitespace-pre-wrap">{q.explanation}</p>
                            ) : null}
                          </CardBody>
                        </Card>
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-text-muted">No history attempt selected yet.</p>
                )}
              </CardBody>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
