import { useState } from 'react';
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
  generateQuiz,
  submitAnswer,
  type QuizData,
  type QuizQuestion,
  type QuizDifficulty,
} from '../lib/trainerService';
import { useGamificationStore } from '../store/gamificationStore';

type Phase = 'setup' | 'playing' | 'review' | 'results';

export function QuizPage() {
  const { subject } = useParams<{ subject: string; lessonId: string }>();
  const navigate = useNavigate();
  const { recordQuizComplete } = useGamificationStore();

  const [phase, setPhase] = useState<Phase>('setup');
  const [difficulty, setDifficulty] = useState<QuizDifficulty>('medium');
  const [questionCount, setQuestionCount] = useState(5);
  const [quiz, setQuiz] = useState<QuizData | null>(null);
  const [currentQ, setCurrentQ] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState('');
  const [answers, setAnswers] = useState<Array<{
    question: QuizQuestion;
    userAnswer: string;
    correct: boolean;
    explanation: string;
  }>>([]);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<{ correct: boolean; explanation: string } | null>(null);

  async function startQuiz() {
    setLoading(true);
    setError(null);
    try {
      const res = await generateQuiz(
        subject || 'biology',
        difficulty,
        questionCount,
      );
      if (res.success && res.quiz) {
        setQuiz(res.quiz);
        setCurrentQ(0);
        setAnswers([]);
        setPhase('playing');
      } else {
        setError(res.error || 'Failed to generate quiz — is the AI backend running?');
      }
    } catch (err) {
      console.error('Failed to generate quiz:', err);
      setError('Network error — check your connection and try again');
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmitAnswer() {
    if (!quiz || !selectedAnswer) return;
    const question = quiz.questions[currentQ];
    setChecking(true);

    try {
      const res = await submitAnswer(
        quiz.quiz_id,
        question.id,
        selectedAnswer,
        question.correct_answer,
        question.question,
      );

      const result = {
        question,
        userAnswer: selectedAnswer,
        correct: res.correct,
        explanation: res.explanation || question.explanation || '',
      };
      setAnswers((prev) => [...prev, result]);
      setLastResult({ correct: res.correct, explanation: result.explanation });
      setPhase('review');
    } catch {
      // Fallback: check locally
      const isCorrect = selectedAnswer === question.correct_answer;
      const result = {
        question,
        userAnswer: selectedAnswer,
        correct: isCorrect,
        explanation: question.explanation || '',
      };
      setAnswers((prev) => [...prev, result]);
      setLastResult({ correct: isCorrect, explanation: result.explanation });
      setPhase('review');
    } finally {
      setChecking(false);
    }
  }

  function nextQuestion() {
    if (!quiz) return;
    setSelectedAnswer('');
    setLastResult(null);
    if (currentQ + 1 < quiz.questions.length) {
      setCurrentQ(currentQ + 1);
      setPhase('playing');
    } else {
      // Quiz finished
      const score = answers.filter((a) => a.correct).length;
      recordQuizComplete(score, answers.length);
      setPhase('results');
    }
  }

  const subjectLabels: Record<string, string> = {
    physics: 'Physics',
    chemistry: 'Chemistry',
    biology: 'Biology',
  };

  const score = answers.filter((a) => a.correct).length;
  const total = answers.length;
  const scorePercent = total > 0 ? Math.round((score / total) * 100) : 0;

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <Breadcrumbs aria-label="Quiz page breadcrumbs">
        <BreadcrumbItem onPress={() => navigate('/dashboard')}>Dashboard</BreadcrumbItem>
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
                  onPress={startQuiz}
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
        {phase === 'playing' && quiz && (
          <motion.div key="playing" initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }}>
            <Card className="glass">
              <CardHeader className="flex flex-col gap-2 pb-2">
                <div className="w-full flex items-center justify-between">
                  <Chip size="sm" color="secondary" variant="flat">
                    Q {currentQ + 1} / {quiz.questions.length}
                  </Chip>
                  <Chip size="sm" variant="flat" color={
                    quiz.questions[currentQ].difficulty === 'easy' ? 'success' :
                    quiz.questions[currentQ].difficulty === 'medium' ? 'warning' : 'danger'
                  }>
                    {quiz.questions[currentQ].difficulty}
                  </Chip>
                </div>
                <Progress
                  value={((currentQ + 1) / quiz.questions.length) * 100}
                  color="secondary"
                  size="sm"
                  className="w-full"
                />
              </CardHeader>
              <CardBody className="gap-4">
                <h3 className="text-md font-semibold leading-relaxed">
                  {quiz.questions[currentQ].question}
                </h3>
                <RadioGroup
                  value={selectedAnswer}
                  onValueChange={setSelectedAnswer}
                  color="secondary"
                >
                  {quiz.questions[currentQ].options.map((opt, i) => (
                    <Radio key={i} value={opt} className="max-w-full">
                      <span className="text-sm">{opt}</span>
                    </Radio>
                  ))}
                </RadioGroup>
              </CardBody>
              <CardFooter>
                <Button
                  color="secondary"
                  fullWidth
                  onPress={handleSubmitAnswer}
                  isDisabled={!selectedAnswer}
                  isLoading={checking}
                >
                  Submit Answer
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
                  onPress={nextQuestion}
                  endContent={<ArrowRight className="w-4 h-4" />}
                >
                  {quiz && currentQ + 1 < quiz.questions.length ? 'Next Question' : 'See Results'}
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
                    +{50 + Math.round((score / total) * 100)} XP
                  </Chip>
                </div>
              </CardBody>
              <CardFooter className="flex gap-2 justify-center">
                <Button
                  variant="flat"
                  onPress={() => {
                    setPhase('setup');
                    setAnswers([]);
                    setCurrentQ(0);
                    setSelectedAnswer('');
                    setLastResult(null);
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
                        <p className="text-sm font-medium">{a.question.question}</p>
                        <p className="text-xs text-default-500 mt-1">
                          Your answer: <span className={a.correct ? 'text-success' : 'text-danger'}>{a.userAnswer}</span>
                          {!a.correct && (
                            <> • Correct: <span className="text-success">{a.question.correct_answer}</span></>
                          )}
                        </p>
                      </div>
                    </div>
                  </CardBody>
                </Card>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
