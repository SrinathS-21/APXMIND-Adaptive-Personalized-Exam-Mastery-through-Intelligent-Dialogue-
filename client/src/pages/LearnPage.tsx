import { useState, useRef, useEffect } from 'react';
import { useLocation, useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Button,
  Input,
  Textarea,
  Slider,
  Spinner,
  Breadcrumbs,
  BreadcrumbItem,
  Chip,
  Divider,
} from '@heroui/react';
import { motion } from 'framer-motion';
import { Send, Bot, User, Sparkles, ArrowLeft, History, List, Trash2, MoreHorizontal, Plus } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { processQuery } from '../lib/queryService';
import {
  clearLearnMessages,
  deleteLearnMessage,
  deleteLearnSession,
  endLearnSession,
  getLearnMessages,
  getLearnSession,
  listLearnSessions,
  sendLearnMessage,
  startLearnSession,
  type LearnMessage,
  type LearnSession,
} from '../lib/learnSessionService';
import { submitLessonRecall } from '../lib/retrievalService';
import { completeLesson } from '../lib/subjectService';
import { getApiErrorMessage } from '../lib/api';
import { useToast } from '../hooks/useToast';
import { useGamificationStore } from '../store/gamificationStore';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  tier?: string;
  timestamp: Date;
}

interface LearnLocationState {
  reopenSessionId?: string;
}

const SESSION_TITLES_STORAGE_KEY = 'APXMIND_learn_session_titles_v1';

function buildWelcomeMessage(subjectName?: string): Message {
  return {
    id: '0',
    role: 'assistant',
    content: `Hi! I'm APXMIND, your NEET study companion. Ask me anything about **${subjectName || 'this lesson'}**! I can explain concepts, solve problems, and help you prepare for NEET. 🎯`,
    timestamp: new Date(),
  };
}

const CALLOUT_LABELS = new Set([
  'example',
  'exam tip',
  'key idea',
  'formula',
  'steps',
  'note',
  'remember',
]);

function formatTimestamp(date: Date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function normalizeAssistantMarkdown(content: string) {
  const normalized = content.replace(/\r\n/g, '\n').trim();
  if (!normalized) return '';

  const withCalloutEmphasis = normalized.replace(/^([A-Za-z ]+):/gm, (match, label: string) => {
    if (CALLOUT_LABELS.has(label.trim().toLowerCase())) {
      return `**${label.trim()}:**`;
    }
    return match;
  });

  // Preserve intentional line-by-line flow from model responses.
  return withCalloutEmphasis.replace(/([^\n])\n(?=[^\n])/g, '$1  \n');
}

export function LearnPage() {
  const { subject, lessonId } = useParams<{ subject: string; lessonId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { addToast } = useToast();
  const { recordStudySession, addXP, recordSubjectStudied } = useGamificationStore();
  const parsedLessonId = lessonId ? Number(lessonId) : NaN;
  const numericLessonId = Number.isFinite(parsedLessonId) ? parsedLessonId : undefined;

  const [messages, setMessages] = useState<Message[]>([
    buildWelcomeMessage(subject),
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [recallText, setRecallText] = useState('');
  const [recallScore, setRecallScore] = useState<number>(60);
  const [submittingRecall, setSubmittingRecall] = useState(false);
  const [recallSubmitted, setRecallSubmitted] = useState(false);
  const [recallStartAt, setRecallStartAt] = useState<number>(Date.now());
  const [recentSessions, setRecentSessions] = useState<LearnSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [historySession, setHistorySession] = useState<LearnSession | null>(null);
  const [historyMessages, setHistoryMessages] = useState<LearnMessage[]>([]);
  const [loadingHistorySessionId, setLoadingHistorySessionId] = useState<string | null>(null);
  const [historyBusySessionId, setHistoryBusySessionId] = useState<string | null>(null);
  const [historyBusyMessageId, setHistoryBusyMessageId] = useState<number | null>(null);
  const [isRailCollapsed, setIsRailCollapsed] = useState(false);
  const [menuSessionId, setMenuSessionId] = useState<string | null>(null);
  const [deletedSessionIds, setDeletedSessionIds] = useState<string[]>([]);
  const [creatingSession, setCreatingSession] = useState(false);
  const [sessionTitles, setSessionTitles] = useState<Record<string, string>>(() => {
    if (typeof window === 'undefined') return {};
    try {
      const raw = localStorage.getItem(SESSION_TITLES_STORAGE_KEY);
      if (!raw) return {};
      const parsed = JSON.parse(raw) as Record<string, string>;
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch {
      return {};
    }
  });
  const [draftSessionTitle, setDraftSessionTitle] = useState('');
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const startTimeRef = useRef(Date.now());
  const routeState = location.state as LearnLocationState | null;
  const reopenSessionIdFromRoute = routeState?.reopenSessionId;

  async function loadRecentSessions(subjectFilter?: string) {
    const normalized = (subjectFilter || subject || '').toLowerCase();
    setSessionsLoading(true);
    setSessionsError(null);
    try {
      const sessions = await listLearnSessions(normalized || undefined, 20);
      const candidates = sessions.filter((session) => !deletedSessionIds.includes(session.id));

      const checks = await Promise.all(
        candidates.map(async (session) => {
          if (session.id === sessionId) {
            return { session, hasMessages: true };
          }
          try {
            const rows = await getLearnMessages(session.id, 1);
            return { session, hasMessages: rows.length > 0 };
          } catch {
            return { session, hasMessages: true };
          }
        })
      );

      const emptySessions = checks.filter((item) => !item.hasMessages).map((item) => item.session);
      if (emptySessions.length > 0) {
        await Promise.all(emptySessions.map((item) => deleteLearnSession(item.id).catch(() => undefined)));
        setSessionTitles((prev) => {
          const next = { ...prev };
          for (const item of emptySessions) {
            delete next[item.id];
          }
          return next;
        });
      }

      const filtered = checks
        .filter((item) => item.hasMessages)
        .map((item) => item.session)
        .slice(0, 8);

      setRecentSessions(filtered);
      void hydrateSessionTitles(filtered);
    } catch (error) {
      setSessionsError(getApiErrorMessage(error, 'Unable to load recent sessions.'));
    } finally {
      setSessionsLoading(false);
    }
  }

  async function hydrateSessionTitles(sessions: LearnSession[]) {
    const missing = sessions.filter((session) => !sessionTitles[session.id]);
    if (!missing.length) return;

    const nextTitles: Record<string, string> = {};
    for (const session of missing) {
      try {
        const rows = await getLearnMessages(session.id, 20);
        const firstUser = rows.find((row) => row.role === 'user' && row.content.trim().length > 0);
        if (firstUser) {
          nextTitles[session.id] = firstUser.content.trim().slice(0, 64);
        }
      } catch {
        // ignore title hydration failures and keep fallback title
      }
    }

    if (Object.keys(nextTitles).length) {
      setSessionTitles((prev) => ({ ...prev, ...nextTitles }));
    }
  }

  async function handleViewSessionHistory(targetSessionId: string) {
    if (loadingHistorySessionId) return;
    if (historySession?.id === targetSessionId) {
      setHistorySession(null);
      setHistoryMessages([]);
      return;
    }

    setLoadingHistorySessionId(targetSessionId);
    setSessionsError(null);
    try {
      const [sessionMeta, messages] = await Promise.all([
        getLearnSession(targetSessionId),
        getLearnMessages(targetSessionId, 80),
      ]);
      setHistorySession(sessionMeta);
      setHistoryMessages(messages);
    } catch (error) {
      setSessionsError(getApiErrorMessage(error, 'Unable to load selected session transcript.'));
    } finally {
      setLoadingHistorySessionId(null);
    }
  }

  function mapPersistedMessagesToChat(rows: LearnMessage[]): Message[] {
    return rows.map((msg) => ({
      id: String(msg.id),
      role: msg.role,
      content: msg.content,
      tier: msg.tier || undefined,
      timestamp: msg.created_at ? new Date(msg.created_at) : new Date(),
    }));
  }

  async function handleReopenSession(targetSessionId: string, options?: { showToast?: boolean }) {
    if (loadingHistorySessionId) return;

    setLoadingHistorySessionId(targetSessionId);
    setSessionsError(null);
    try {
      const [sessionMeta, persisted] = await Promise.all([
        getLearnSession(targetSessionId),
        getLearnMessages(targetSessionId, 120),
      ]);

      const remapped = mapPersistedMessagesToChat(persisted);
      setSessionId(sessionMeta.id);
      setDraftSessionTitle(sessionTitles[sessionMeta.id] ?? '');
      setMessages(remapped.length ? remapped : [buildWelcomeMessage(subject)]);
      setHistorySession(sessionMeta);
      setHistoryMessages(persisted);
      if (options?.showToast ?? true) {
        addToast('Previous learning session reopened.', 'success');
      }
    } catch (error) {
      setSessionsError(getApiErrorMessage(error, 'Unable to reopen this session.'));
    } finally {
      setLoadingHistorySessionId(null);
    }
  }

  async function handleDeleteHistorySession(targetSessionId: string) {
    if (historyBusySessionId) return;
    setHistoryBusySessionId(targetSessionId);
    setSessionsError(null);
    setMenuSessionId(null);

    const previousSessions = recentSessions;
    setDeletedSessionIds((prev) => (prev.includes(targetSessionId) ? prev : [...prev, targetSessionId]));
    setSessionTitles((prev) => {
      const next = { ...prev };
      delete next[targetSessionId];
      return next;
    });
    setRecentSessions((prev) => prev.filter((session) => session.id !== targetSessionId));

    if (historySession?.id === targetSessionId) {
      setHistorySession(null);
      setHistoryMessages([]);
    }

    if (sessionId === targetSessionId) {
      setSessionId(null);
      setDraftSessionTitle('');
      setMessages([buildWelcomeMessage(subject)]);
    }

    try {
      await deleteLearnSession(targetSessionId);
      addToast('Session deleted successfully.', 'success');
      await loadRecentSessions(subject);
    } catch (error) {
      setDeletedSessionIds((prev) => prev.filter((id) => id !== targetSessionId));
      setRecentSessions(previousSessions);
      setSessionsError(getApiErrorMessage(error, 'Unable to delete this session.'));
    } finally {
      setHistoryBusySessionId(null);
    }
  }

  async function handleClearHistoryMessages(targetSessionId: string) {
    if (historyBusySessionId) return;
    setHistoryBusySessionId(targetSessionId);
    setSessionsError(null);
    try {
      await clearLearnMessages(targetSessionId);
      if (historySession?.id === targetSessionId) {
        setHistoryMessages([]);
      }
      addToast('Session transcript cleared.', 'success');
    } catch (error) {
      setSessionsError(getApiErrorMessage(error, 'Unable to clear session transcript.'));
    } finally {
      setHistoryBusySessionId(null);
    }
  }

  async function createNewSession(options?: { resetChat?: boolean; showToast?: boolean; endCurrent?: boolean }) {
    if (!subject) {
      addToast('Subject is missing. Please reopen this lesson.', 'error');
      return null;
    }

    setCreatingSession(true);
    setSessionsError(null);
    try {
      const pendingTitle = draftSessionTitle.trim();

      if (options?.endCurrent && sessionId) {
        await endLearnSession(sessionId).catch(() => undefined);
      }

      const session = await startLearnSession(subject, numericLessonId);
      setSessionId(session.id);

      const resolvedTitle = pendingTitle || (sessionTitles[session.id] ?? '');
      setDraftSessionTitle(resolvedTitle);
      if (pendingTitle) {
        setSessionTitles((prev) => ({
          ...prev,
          [session.id]: pendingTitle.slice(0, 80),
        }));
      }

      if (options?.resetChat) {
        setMessages([buildWelcomeMessage(subject)]);
        setInput('');
      }

      if (options?.showToast) {
        addToast('Started a new chat session.', 'success');
      }

      return session.id;
    } catch (error) {
      const message = getApiErrorMessage(error, 'Unable to start a new chat session.');
      setSessionsError(message);
      if (options?.showToast) {
        addToast(message, 'error');
      }
      return null;
    } finally {
      setCreatingSession(false);
    }
  }

  async function handleStartNewChat() {
    if (loading || creatingSession) return;

    if (sessionId) {
      await endLearnSession(sessionId).catch(() => undefined);
    }

    setSessionId(null);
    setDraftSessionTitle('');
    setMessages([buildWelcomeMessage(subject)]);
    setInput('');
    setHistorySession(null);
    setHistoryMessages([]);
    setMenuSessionId(null);
    addToast('Ready for a new chat. A session is created after your first message.', 'success');
  }

  async function handleDeleteHistoryMessage(targetSessionId: string, messageId: number) {
    if (historyBusyMessageId) return;
    setHistoryBusyMessageId(messageId);
    setSessionsError(null);
    try {
      await deleteLearnMessage(targetSessionId, messageId);
      if (historySession?.id === targetSessionId) {
        setHistoryMessages((prev) => prev.filter((msg) => msg.id !== messageId));
      }
    } catch (error) {
      setSessionsError(getApiErrorMessage(error, 'Unable to delete this message.'));
    } finally {
      setHistoryBusyMessageId(null);
    }
  }

  // Track subject studied for badge
  useEffect(() => {
    if (subject) recordSubjectStudied(subject);
  }, [subject, recordSubjectStudied]);

  // Track study time
  useEffect(() => {
    startTimeRef.current = Date.now();
    return () => {
      const minutes = Math.round((Date.now() - startTimeRef.current) / 60000);
      if (minutes >= 1) {
        recordStudySession(minutes);
      }
    };
  }, [recordStudySession]);

  useEffect(() => {
    const el = chatScrollRef.current;
    if (!el) return;
    const raf = requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight;
    });
    return () => cancelAnimationFrame(raf);
  }, [messages, loading]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(SESSION_TITLES_STORAGE_KEY, JSON.stringify(sessionTitles));
    } catch {
      // Ignore storage write issues.
    }
  }, [sessionTitles]);

  useEffect(() => {
    if (!subject) return;

    if (reopenSessionIdFromRoute) {
      void handleReopenSession(reopenSessionIdFromRoute, { showToast: false });
    }
  }, [subject, reopenSessionIdFromRoute]);

  useEffect(() => {
    setRecallText('');
    setRecallScore(60);
    setRecallSubmitted(false);
    setRecallStartAt(Date.now());
    setSessionId(null);
    setDraftSessionTitle('');
    setMessages([buildWelcomeMessage(subject)]);
    setHistorySession(null);
    setHistoryMessages([]);
    setMenuSessionId(null);
    void loadRecentSessions(subject);
  }, [subject, lessonId]);

  async function handleSend() {
    const q = input.trim();
    if (!q || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: q,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      let assistantMsg: Message;
      let activeSessionId = sessionId;

      if (!activeSessionId) {
        activeSessionId = await createNewSession({ resetChat: false, showToast: false, endCurrent: false });
      }

      if (activeSessionId && !sessionTitles[activeSessionId]) {
        setSessionTitles((prev) => ({
          ...prev,
          [activeSessionId as string]: q.slice(0, 64),
        }));
      }

      if (activeSessionId) {
        const persisted = await sendLearnMessage(activeSessionId, q);
        assistantMsg = {
          id: String(persisted.id),
          role: 'assistant',
          content: persisted.content || 'Sorry, I could not process that question.',
          tier: persisted.tier || undefined,
          timestamp: persisted.created_at ? new Date(persisted.created_at) : new Date(),
        };
      } else {
        const res = await processQuery(q, subject);
        assistantMsg = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: res.answer || 'Sorry, I could not process that question.',
          tier: res.metadata?.tier,
          timestamp: new Date(),
        };
      }

      setMessages((prev) => [...prev, assistantMsg]);
      addXP(10);
      void loadRecentSessions(subject);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Oops! Something went wrong. Please make sure the APXMIND backend is running.',
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmitRecallAndComplete() {
    if (!subject || !numericLessonId) {
      addToast('Lesson details are missing. Reload and try again.', 'error');
      return;
    }
    if (recallText.trim().length < 20) {
      addToast('Write at least 20 characters in your recall summary.', 'warning');
      return;
    }

    setSubmittingRecall(true);
    try {
      const subjectKey = subject.toLowerCase();
      const recallSubject =
        subjectKey === 'physics' || subjectKey === 'chemistry' || subjectKey === 'biology'
          ? subjectKey
          : undefined;

      const elapsedSec = Math.max(30, Math.round((Date.now() - recallStartAt) / 1000));
      const recall = await submitLessonRecall({
        lesson_id: numericLessonId,
        subject: recallSubject,
        topic: `${subjectLabels[subject || ''] || subject} lesson ${numericLessonId}`,
        response_text: recallText.trim(),
        self_score: recallScore,
        time_taken_sec: elapsedSec,
      });

      const completion = await completeLesson(subject, numericLessonId);
      if (!completion.success) {
        throw new Error(completion.error || 'Failed to complete lesson');
      }

      setRecallSubmitted(true);
      addToast(`Recall saved (${recall.score_band}). Lesson marked complete.`, 'success');
    } catch (error) {
      addToast(getApiErrorMessage(error, 'Unable to save recall. Please try again.'), 'error');
    } finally {
      setSubmittingRecall(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleSessionTitleChange(value: string) {
    const normalized = value.slice(0, 80);
    setDraftSessionTitle(normalized);

    if (!sessionId) return;

    const title = normalized.trim();
    setSessionTitles((prev) => {
      const next = { ...prev };
      if (title) {
        next[sessionId] = title;
      } else {
        delete next[sessionId];
      }
      return next;
    });
  }

  const subjectLabels: Record<string, string> = {
    physics: 'Physics',
    chemistry: 'Chemistry',
    biology: 'Biology',
  };

  const visibleRecentSessions = recentSessions
    .filter((session) => !deletedSessionIds.includes(session.id))
    .slice(0, 8);

  const groupedRecentSessions = (() => {
    const groups = new Map<string, LearnSession[]>();
    const now = Date.now();

    for (const session of visibleRecentSessions) {
      const started = new Date(session.started_at).getTime();
      const dayDiff = Math.floor((now - started) / (1000 * 60 * 60 * 24));

      let label: string;
      if (dayDiff <= 7) {
        label = '7 Days';
      } else if (dayDiff <= 30) {
        label = '30 Days';
      } else {
        const dt = new Date(session.started_at);
        label = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}`;
      }

      if (!groups.has(label)) {
        groups.set(label, []);
      }
      groups.get(label)!.push(session);
    }

    return Array.from(groups.entries()).map(([label, items]) => ({ label, items }));
  })();

  function getSessionTitle(session: LearnSession) {
    const hydrated = sessionTitles[session.id];
    if (hydrated && hydrated.trim().length > 0) {
      return hydrated;
    }

    if (session.id === sessionId) {
      const latestUser = [...messages].reverse().find((msg) => msg.role === 'user' && msg.content.trim().length > 0);
      if (latestUser) {
        return latestUser.content.trim().slice(0, 64);
      }
    }

    return `Chat ${new Date(session.started_at).toLocaleDateString()} ${new Date(session.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  }

  function renderRecallPanel(cardClassName = 'glass border-border-strong shrink-0', bodyClassName = 'p-4 space-y-3') {
    return (
      <Card className={cardClassName}>
        <div className={bodyClassName}>
          <div className="flex items-center justify-between gap-3">
            <h2 className="ui-section-title" style={{ fontSize: 14 }}>Lesson Recall (Required)</h2>
            <Chip
              size="sm"
              color={recallSubmitted ? 'success' : 'warning'}
              variant="flat"
            >
              {recallSubmitted ? 'Completed' : 'Pending'}
            </Chip>
          </div>
          <p className="text-sm text-text-secondary">
            Summarize what you learned before moving to quiz. This powers spaced revision and closes the learning loop.
          </p>
          <Textarea
            aria-label="Lesson recall"
            minRows={3}
            placeholder="Write the key concepts, one mistake to avoid, and one point you want to revise."
            value={recallText}
            onValueChange={setRecallText}
            isDisabled={submittingRecall || recallSubmitted}
            variant="bordered"
            classNames={{
              inputWrapper: 'border-border-strong hover:border-accent/50 focus-within:!border-accent bg-bg-2',
              input: 'text-text-primary placeholder:text-[#8B7D6D]',
            }}
          />
          <div>
            <label
              style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 5 }}
            >
              Self Score: <span style={{ color: 'var(--accent)', fontWeight: 700 }}>{recallScore}</span> / 100
            </label>
            <Slider
              aria-label="Recall self score"
              step={1}
              minValue={0}
              maxValue={100}
              value={recallScore}
              onChange={(value) => setRecallScore(value as number)}
              isDisabled={submittingRecall || recallSubmitted}
              color="secondary"
              classNames={{
                track: 'bg-bg-5 h-[4px] rounded-[var(--r-pill)]',
                filler: 'bg-accent',
                thumb: 'w-[18px] h-[18px] bg-accent border-2 border-white',
              }}
            />
          </div>
          <Button
            color="secondary"
            onPress={handleSubmitRecallAndComplete}
            isLoading={submittingRecall}
            isDisabled={recallSubmitted}
          >
            {recallSubmitted ? 'Recall Saved' : 'Save Recall & Complete Lesson'}
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <div className="w-full flex flex-col gap-3">
      <div className="shrink-0 space-y-2">
        <Breadcrumbs aria-label="Learn page breadcrumbs">
          <BreadcrumbItem onPress={() => navigate('/home')}>Home</BreadcrumbItem>
          <BreadcrumbItem onPress={() => navigate(`/subject/${subject}`)}>
            {subjectLabels[subject || ''] || subject}
          </BreadcrumbItem>
          <BreadcrumbItem>Learn</BreadcrumbItem>
        </Breadcrumbs>
        <div className="flex items-center">
          <div className="flex items-center gap-2">
            <Button
              isIconOnly
              aria-label="Back to subject"
              variant="light"
              size="sm"
              onPress={() => navigate(`/subject/${subject}`)}
            >
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5" style={{ color: 'var(--accent)' }} />
              <h1 className="ui-section-title">APXMIND AI Tutor</h1>
            </div>
          </div>
        </div>
      </div>

      <div
        className={`grid grid-cols-1 gap-3 items-start ${isRailCollapsed ? '' : 'xl:grid-cols-[340px_minmax(0,1fr)]'
          }`}
      >
        {!isRailCollapsed ? (
          <div className="flex flex-col gap-3 self-start xl:sticky xl:top-3 xl:h-[calc(100dvh-140px)]">
            <Card className="glass border-border-strong overflow-hidden xl:h-[calc(50%-6px)]">
              <div className="p-3.5 space-y-3 h-full flex flex-col">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <History className="w-4 h-4 text-primary" />
                    <h2 className="ui-section-title" style={{ fontSize: 14 }}>Recent Sessions</h2>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Button
                      size="sm"
                      variant="flat"
                      color="default"
                      startContent={<List className="w-3 h-3" />}
                      onPress={() => navigate('/learn-sessions')}
                    >
                      View All
                    </Button>
                    <Button
                      size="sm"
                      variant="bordered"
                      onPress={() => setIsRailCollapsed(true)}
                    >
                      Hide
                    </Button>
                  </div>
                </div>

                <Button
                  size="sm"
                  variant="solid"
                  startContent={<Plus className="w-3 h-3" />}
                  isLoading={creatingSession}
                  isDisabled={loading}
                  onPress={() => {
                    void handleStartNewChat();
                  }}
                  className="w-full bg-[#B66A2E] text-white hover:bg-[#9F5C27]"
                >
                  New chat
                </Button>

                <Button
                  size="sm"
                  variant="flat"
                  color="secondary"
                  onPress={() => void loadRecentSessions(subject)}
                  isLoading={sessionsLoading}
                  className="w-full"
                >
                  Refresh sessions
                </Button>

                {sessionsError ? (
                  <Chip color="danger" variant="flat" size="sm" className="w-full justify-center">
                    {sessionsError}
                  </Chip>
                ) : null}

                {sessionsLoading ? (
                  <div className="py-2 flex items-center justify-center">
                    <Spinner size="sm" color="secondary" label="Loading sessions" />
                  </div>
                ) : groupedRecentSessions.length ? (
                  <div
                    className="space-y-2 h-72 xl:flex-1 xl:min-h-0 overflow-y-scroll pr-1"
                    style={{ scrollbarGutter: 'stable' }}
                  >
                    {groupedRecentSessions.map((group) => (
                      <div key={group.label} className="space-y-2">
                        <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>
                          {group.label}
                        </p>
                        {group.items.map((session) => {
                          const isSelected = session.id === sessionId;
                          return (
                            <div
                              key={session.id}
                              className="rounded-md px-2 py-1.5"
                              style={{
                                border: isSelected ? '1px solid var(--accent-border)' : '1px solid transparent',
                                background: isSelected ? 'var(--accent-soft)' : 'transparent',
                              }}
                            >
                              <div className="flex items-center justify-between gap-2">
                                <button
                                  type="button"
                                  className="flex-1 min-w-0 text-left"
                                  onClick={() => {
                                    void handleReopenSession(session.id, { showToast: false });
                                  }}
                                >
                                  <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                                    {getSessionTitle(session)}
                                  </p>
                                  <p className="text-xs text-text-secondary truncate">
                                    {new Date(session.started_at).toLocaleString()} • {session.duration_minutes ? `${Math.round(session.duration_minutes)} min` : 'active'}
                                  </p>
                                </button>
                                <div className="relative">
                                  <Button
                                    isIconOnly
                                    size="sm"
                                    variant="light"
                                    aria-label="Session options"
                                    isLoading={loadingHistorySessionId === session.id || historyBusySessionId === session.id}
                                    onPress={() => {
                                      setMenuSessionId((prev) => (prev === session.id ? null : session.id));
                                    }}
                                  >
                                    <MoreHorizontal className="w-4 h-4" />
                                  </Button>

                                  {menuSessionId === session.id ? (
                                    <div
                                      className="absolute right-0 top-9 z-50 w-44 rounded-lg p-1"
                                      style={{
                                        background: 'var(--bg-2)',
                                        border: '1px solid var(--border-default)',
                                        boxShadow: '0 10px 24px rgba(0, 0, 0, 0.16)',
                                      }}
                                    >
                                      <button
                                        type="button"
                                        className="w-full text-left px-2.5 py-1.5 rounded-md text-sm"
                                        style={{ color: 'var(--red)' }}
                                        onClick={() => {
                                          setMenuSessionId(null);
                                          void handleDeleteHistorySession(session.id);
                                        }}
                                      >
                                        Delete session
                                      </button>
                                    </div>
                                  ) : null}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-text-secondary">No previous sessions found for this subject yet.</p>
                )}
              </div>
            </Card>

            {renderRecallPanel('glass border-border-strong overflow-hidden xl:h-[calc(50%-6px)]', 'p-4 space-y-3 h-full overflow-y-auto')}
          </div>
        ) : null}

        <div className="min-w-0 flex flex-col gap-3 xl:h-[calc(100dvh-140px)]">
          {isRailCollapsed ? (
            <div className="flex items-center justify-start">
              <Button
                size="sm"
                variant="bordered"
                startContent={<List className="w-3 h-3" />}
                onPress={() => setIsRailCollapsed(false)}
              >
                Show Sessions
              </Button>
            </div>
          ) : null}

          <Card className="glass border-border-strong shrink-0">
            <div className="p-3 flex items-center gap-2">
              <Input
                aria-label="Chat title"
                placeholder="Set chat title before you start"
                value={draftSessionTitle}
                onValueChange={handleSessionTitleChange}
                size="sm"
                variant="bordered"
                className="flex-1"
                classNames={{
                  inputWrapper: 'border-border-strong hover:border-accent/50 focus-within:!border-accent bg-bg-2',
                  input: 'text-text-primary placeholder:text-[#8B7D6D]',
                }}
              />
              <p className="text-xs text-text-secondary whitespace-nowrap px-1">Auto-saved</p>
            </div>
          </Card>

          {isRailCollapsed ? renderRecallPanel() : null}

          {/* Chat area */}
          <Card className="glass border-border-strong flex flex-col flex-1 min-h-[52vh] xl:min-h-0">
            <div ref={chatScrollRef} className="flex-1 overflow-y-auto p-4">
              <div className="chat-thread">
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    {msg.role === 'assistant' && (
                      <div className="shrink-0 w-8 h-8 rounded-full bg-linear-to-br from-emerald-500 to-purple-500 flex items-center justify-center mt-1">
                        <Bot className="w-4 h-4 text-white" />
                      </div>
                    )}
                    <div
                      className={`max-w-[86%] ${msg.role === 'user'
                        ? 'chat-user-card'
                        : 'chat-assistant-card'
                        }`}
                    >
                      <div className="chat-message-meta">
                        <span>{msg.role === 'assistant' ? 'APXMIND' : 'You'}</span>
                        <span>{formatTimestamp(msg.timestamp)}</span>
                      </div>

                      <div className="chat-markdown">
                        {msg.role === 'assistant' ? (
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {normalizeAssistantMarkdown(msg.content)}
                          </ReactMarkdown>
                        ) : (
                          <p className="whitespace-pre-wrap m-0">{msg.content}</p>
                        )}
                      </div>

                      {msg.tier && msg.role === 'assistant' && (
                        <div className="mt-2">
                          <Chip size="sm" variant="flat" className="text-[10px] uppercase tracking-wide">
                            {msg.tier}
                          </Chip>
                        </div>
                      )}
                    </div>
                    {msg.role === 'user' && (
                      <div className="shrink-0 w-8 h-8 rounded-full bg-secondary/20 flex items-center justify-center mt-1">
                        <User className="w-4 h-4 text-secondary" />
                      </div>
                    )}
                  </motion.div>
                ))}
                {loading && (
                  <div className="flex gap-3">
                    <div className="shrink-0 w-8 h-8 rounded-full bg-linear-to-br from-emerald-500 to-purple-500 flex items-center justify-center mt-1">
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                    <div className="chat-assistant-card px-4 py-3">
                      <Spinner size="sm" color="secondary" />
                    </div>
                  </div>
                )}
              </div>
            </div>

            <Divider />

            <div className="p-3 flex gap-2">
              <Input
                aria-label="Message input"
                placeholder={`Ask about ${subjectLabels[subject || ''] || 'any subject'}...`}
                value={input}
                onValueChange={setInput}
                onKeyDown={handleKeyDown}
                variant="bordered"
                size="md"
                className="flex-1"
                isDisabled={loading}
                classNames={{
                  inputWrapper: 'border-border-strong hover:border-accent/50 focus-within:!border-accent bg-bg-2',
                  input: 'text-text-primary placeholder:text-[#8B7D6D]',
                }}
              />
              <Button
                isIconOnly
                aria-label="Send message"
                color="secondary"
                onPress={handleSend}
                isDisabled={!input.trim() || loading}
                isLoading={loading}
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
