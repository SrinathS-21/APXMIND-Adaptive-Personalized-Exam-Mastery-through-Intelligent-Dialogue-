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
import { Send, Bot, User, Sparkles, ArrowLeft, History, List, MoreHorizontal, Plus, BookText, FileDown, ShieldCheck, Languages } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { processQuery } from '../lib/queryService';
import {
  convertLearnSessionToNotes,
  deleteLearnSession,
  generateLearnChapterBrief,
  generateLearnRevisionSheet,
  endLearnSession,
  getLearnSessionSourceLock,
  getLearnSessionSummary,
  getLearnSessionMode,
  getLessonMissionContext,
  getLearnMessages,
  getLearnSession,
  listLearnSessions,
  sendLearnMessage,
  setLearnSessionSourceLock,
  setLearnSessionMode,
  submitLearnCheckpoint,
  startLearnSession,
  type LearnMessageMetadata,
  type LearnSourceCitation,
  type LearnSessionSummary,
  type LessonMissionContext,
  type LearnMessage,
  type LearnSession,
  type TutorMode,
} from '../lib/learnSessionService';
import { submitLessonRecall } from '../lib/retrievalService';
import { completeLesson } from '../lib/subjectService';
import { getApiErrorMessage } from '../lib/api';
import { useToast } from '../hooks/useToast';
import { useGamificationStore } from '../store/gamificationStore';
import { useProfileStore } from '../store/profileStore';
import { normalizeLanguage } from '../lib/language';
import { TutorModeSelector } from '../components/learn/TutorModeSelector';
import { LessonMissionCard } from '../components/learn/LessonMissionCard';
import { CheckpointPulseCard } from '../components/learn/CheckpointPulseCard';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  tier?: string;
  msgMetadata?: LearnMessageMetadata | null;
  timestamp: Date;
}

interface LearnLocationState {
  reopenSessionId?: string;
}

const SESSION_TITLES_STORAGE_KEY = 'APXMIND_learn_session_titles_v1';

const TUTOR_MODE_LABELS: Record<TutorMode, string> = {
  guided: 'Guided Learn',
  revision: 'Rapid Revision',
  drill: 'Exam Drill',
};

const CHECKPOINT_INTERVAL_TURNS = 4;
const SHOW_NOTEBOOK_FEATURES_IN_LEARN = false;

type OutputLanguage = 'en' | 'ta';

function parseOutputLanguage(value: string | null | undefined): OutputLanguage {
  return value === 'ta' ? 'ta' : 'en';
}

function outputLanguageLabel(value: OutputLanguage): string {
  return value === 'ta' ? 'Tamil' : 'English';
}

function extractCitations(metadata: LearnMessageMetadata | null | undefined): LearnSourceCitation[] {
  if (!metadata || typeof metadata !== 'object') {
    return [];
  }

  const raw = metadata.citations;
  if (!Array.isArray(raw)) {
    return [];
  }

  return raw.filter((item): item is LearnSourceCitation => {
    return !!item && typeof item === 'object' && typeof item.source_id === 'string' && typeof item.title === 'string';
  });
}

function parseTutorMode(value: unknown): TutorMode | null {
  if (value === 'guided' || value === 'revision' || value === 'drill') {
    return value;
  }
  return null;
}

function buildCheckpointPrompt(mode: TutorMode, conceptKey: string): string {
  if (mode === 'revision') {
    return `In 2-3 lines, summarize the highest-yield points for ${conceptKey} and one exam trap to avoid.`;
  }
  if (mode === 'drill') {
    return `Answer this quick check for ${conceptKey}: what is the core rule and how would you apply it in a NEET-style question?`;
  }
  return `Teach back ${conceptKey} in your own words with one simple example.`;
}

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
  const profile = useProfileStore((s) => s.profile);
  const selectedLanguage = normalizeLanguage(profile?.preferredLanguage);
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
  const [loadingHistorySessionId, setLoadingHistorySessionId] = useState<string | null>(null);
  const [historyBusySessionId, setHistoryBusySessionId] = useState<string | null>(null);
  const [isRailCollapsed, setIsRailCollapsed] = useState(false);
  const [menuSessionId, setMenuSessionId] = useState<string | null>(null);
  const [deletedSessionIds, setDeletedSessionIds] = useState<string[]>([]);
  const [creatingSession, setCreatingSession] = useState(false);
  const [tutorMode, setTutorMode] = useState<TutorMode>('guided');
  const [lessonContext, setLessonContext] = useState<LessonMissionContext | null>(null);
  const [lessonContextLoading, setLessonContextLoading] = useState(false);
  const [lessonContextError, setLessonContextError] = useState<string | null>(null);
  const [checkpointPrompt, setCheckpointPrompt] = useState<string | null>(null);
  const [checkpointConceptKey, setCheckpointConceptKey] = useState<string | null>(null);
  const [checkpointResponse, setCheckpointResponse] = useState('');
  const [checkpointConfidence, setCheckpointConfidence] = useState(60);
  const [checkpointSubmitting, setCheckpointSubmitting] = useState(false);
  const [lastCheckpointTurn, setLastCheckpointTurn] = useState(0);
  const [latestCheckpointScore, setLatestCheckpointScore] = useState<number | null>(null);
  const [latestCheckpointFeedback, setLatestCheckpointFeedback] = useState<string | null>(null);
  const [sourceLocked, setSourceLocked] = useState(false);
  const [outputLanguage, setOutputLanguage] = useState<OutputLanguage>(parseOutputLanguage(selectedLanguage));
  const [expandedCitationKey, setExpandedCitationKey] = useState<string | null>(null);
  const [sessionSummary, setSessionSummary] = useState<LearnSessionSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [chapterBriefLoading, setChapterBriefLoading] = useState(false);
  const [revisionSheetLoading, setRevisionSheetLoading] = useState(false);
  const [notesConverting, setNotesConverting] = useState(false);
  const [lastGeneratedArtifact, setLastGeneratedArtifact] = useState<string | null>(null);
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

  async function loadLessonContext(targetLessonId?: number) {
    if (!targetLessonId || !Number.isFinite(targetLessonId)) {
      setLessonContext(null);
      setLessonContextError(null);
      setLessonContextLoading(false);
      return;
    }

    setLessonContextLoading(true);
    setLessonContextError(null);
    try {
      const context = await getLessonMissionContext(targetLessonId);
      setLessonContext(context);
    } catch (error) {
      setLessonContext(null);
      setLessonContextError(getApiErrorMessage(error, 'Unable to load lesson mission.'));
    } finally {
      setLessonContextLoading(false);
    }
  }

  async function refreshSessionSummary(targetSessionId?: string) {
    const activeSessionId = targetSessionId ?? sessionId;
    if (!activeSessionId) {
      setSessionSummary(null);
      setSummaryLoading(false);
      return;
    }

    setSummaryLoading(true);
    try {
      const summary = await getLearnSessionSummary(activeSessionId);
      setSessionSummary(summary);
    } catch {
      // Summary should not block learning flow.
    } finally {
      setSummaryLoading(false);
    }
  }

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

  function mapPersistedMessagesToChat(rows: LearnMessage[]): Message[] {
    return rows.map((msg) => ({
      id: String(msg.id),
      role: msg.role,
      content: msg.content,
      tier: msg.tier || undefined,
      msgMetadata: msg.msg_metadata || null,
      timestamp: msg.created_at ? new Date(msg.created_at) : new Date(),
    }));
  }

  function resolveTutorModeFromHistory(rows: LearnMessage[]): TutorMode {
    for (let index = rows.length - 1; index >= 0; index -= 1) {
      const metadata = rows[index].msg_metadata;
      if (!metadata || typeof metadata !== 'object') {
        continue;
      }
      const resolved = parseTutorMode((metadata as { mode?: unknown }).mode);
      if (resolved) {
        return resolved;
      }
    }

    return 'guided';
  }

  async function handleReopenSession(targetSessionId: string, options?: { showToast?: boolean }) {
    if (loadingHistorySessionId) return;

    setLoadingHistorySessionId(targetSessionId);
    setSessionsError(null);
    try {
      const [sessionMeta, persisted, persistedMode, persistedSourceLock, summary] = await Promise.all([
        getLearnSession(targetSessionId),
        getLearnMessages(targetSessionId, 120),
        getLearnSessionMode(targetSessionId).catch(() => null),
        getLearnSessionSourceLock(targetSessionId).catch(() => null),
        getLearnSessionSummary(targetSessionId).catch(() => null),
      ]);

      const remapped = mapPersistedMessagesToChat(persisted);
      setSessionId(sessionMeta.id);
      setDraftSessionTitle(sessionTitles[sessionMeta.id] ?? '');
      setTutorMode(persistedMode?.mode ?? resolveTutorModeFromHistory(persisted));
      setSourceLocked(Boolean(persistedSourceLock?.enabled));
      setSessionSummary(summary);
      setMessages(remapped.length ? remapped : [buildWelcomeMessage(subject)]);
      setHistorySession(sessionMeta);
      setCheckpointPrompt(null);
      setCheckpointConceptKey(null);
      setCheckpointResponse('');
      setCheckpointSubmitting(false);
      setExpandedCitationKey(null);
      setLastCheckpointTurn(remapped.filter((msg) => msg.role === 'user').length);
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
    }

    if (sessionId === targetSessionId) {
      setSessionId(null);
      setDraftSessionTitle('');
      setTutorMode('guided');
      setSourceLocked(false);
      setSessionSummary(null);
      setExpandedCitationKey(null);
      setLastGeneratedArtifact(null);
      setMessages([buildWelcomeMessage(subject)]);
      setCheckpointPrompt(null);
      setCheckpointConceptKey(null);
      setCheckpointResponse('');
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
      await setLearnSessionMode(session.id, tutorMode).catch(() => undefined);
      await setLearnSessionSourceLock(session.id, sourceLocked).catch(() => undefined);
      setSessionSummary(null);

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
    setTutorMode('guided');
    setSourceLocked(false);
    setSessionSummary(null);
    setExpandedCitationKey(null);
    setLastGeneratedArtifact(null);
    setMessages([buildWelcomeMessage(subject)]);
    setInput('');
    setHistorySession(null);
    setMenuSessionId(null);
    setCheckpointPrompt(null);
    setCheckpointConceptKey(null);
    setCheckpointResponse('');
    setLastCheckpointTurn(0);
    setLatestCheckpointScore(null);
    setLatestCheckpointFeedback(null);
    addToast('Ready for a new chat. A session is created after your first message.', 'success');
  }

  // Track subject studied for badge
  useEffect(() => {
    if (subject) recordSubjectStudied(subject);
  }, [subject, recordSubjectStudied]);

  useEffect(() => {
    setOutputLanguage(parseOutputLanguage(selectedLanguage));
  }, [selectedLanguage]);

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
    void refreshSessionSummary(sessionId ?? undefined);
  }, [sessionId]);

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
    setMenuSessionId(null);
    setTutorMode('guided');
    setSourceLocked(false);
    setSessionSummary(null);
    setExpandedCitationKey(null);
    setLastGeneratedArtifact(null);
    setCheckpointPrompt(null);
    setCheckpointConceptKey(null);
    setCheckpointResponse('');
    setCheckpointSubmitting(false);
    setLastCheckpointTurn(0);
    setLatestCheckpointScore(null);
    setLatestCheckpointFeedback(null);
    void loadRecentSessions(subject);
    void loadLessonContext(numericLessonId);
  }, [subject, lessonId]);

  useEffect(() => {
    if (!sessionId || loading || checkpointPrompt) return;

    const userTurns = messages.filter((msg) => msg.role === 'user').length;
    if (userTurns < CHECKPOINT_INTERVAL_TURNS) return;
    if (userTurns % CHECKPOINT_INTERVAL_TURNS !== 0) return;
    if (userTurns === lastCheckpointTurn) return;

    const concept = lessonContext?.focus_topics?.[0] || lessonContext?.lesson_title || 'Current lesson concept';
    setCheckpointConceptKey(concept);
    setCheckpointPrompt(buildCheckpointPrompt(tutorMode, concept));
    setCheckpointResponse('');
    setCheckpointConfidence(60);
    setLastCheckpointTurn(userTurns);
  }, [checkpointPrompt, lastCheckpointTurn, lessonContext, loading, messages, sessionId, tutorMode]);

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
        const persisted = await sendLearnMessage(activeSessionId, q, selectedLanguage, tutorMode, sourceLocked);
        assistantMsg = {
          id: String(persisted.id),
          role: 'assistant',
          content: persisted.content || 'Sorry, I could not process that question.',
          tier: persisted.tier || undefined,
          msgMetadata: persisted.msg_metadata || null,
          timestamp: persisted.created_at ? new Date(persisted.created_at) : new Date(),
        };
      } else {
        const res = await processQuery(q, subject, undefined, selectedLanguage);
        assistantMsg = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: res.answer || 'Sorry, I could not process that question.',
          tier: res.metadata?.tier,
          msgMetadata: null,
          timestamp: new Date(),
        };
      }

      setMessages((prev) => [...prev, assistantMsg]);
      addXP(10);
      void loadRecentSessions(subject);
      if (activeSessionId) {
        void refreshSessionSummary(activeSessionId);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Oops! Something went wrong. Please make sure the APXMIND backend is running.',
          msgMetadata: null,
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
      addToast('Write at least 20 characters in your recall summary.', 'info');
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

  function handleUseStarterPrompt(prompt: string, mode: string) {
    const nextMode = parseTutorMode(mode);
    if (nextMode) {
      handleTutorModeChange(nextMode);
    }
    setInput(prompt);
  }

  async function handleSubmitCheckpoint() {
    if (!sessionId || !checkpointPrompt || !checkpointConceptKey) {
      return;
    }
    if (checkpointResponse.trim().length < 8) {
      addToast('Write a short checkpoint response before submitting.', 'info');
      return;
    }

    setCheckpointSubmitting(true);
    try {
      const result = await submitLearnCheckpoint(sessionId, {
        concept_key: checkpointConceptKey,
        prompt: checkpointPrompt,
        response_text: checkpointResponse.trim(),
        confidence: checkpointConfidence,
      });

      setLatestCheckpointScore(result.score_percent);
      setLatestCheckpointFeedback(result.feedback);
      setCheckpointPrompt(null);
      setCheckpointConceptKey(null);
      setCheckpointResponse('');
      addToast(`Checkpoint saved: ${result.score_percent}%`, 'success');
      void refreshSessionSummary(sessionId);
    } catch (error) {
      addToast(getApiErrorMessage(error, 'Unable to save checkpoint right now.'), 'error');
    } finally {
      setCheckpointSubmitting(false);
    }
  }

  function handleSkipCheckpoint() {
    setCheckpointPrompt(null);
    setCheckpointConceptKey(null);
    setCheckpointResponse('');
  }

  function handleTutorModeChange(mode: TutorMode) {
    setTutorMode(mode);
    if (!sessionId) return;

    void setLearnSessionMode(sessionId, mode).catch(() => {
      // Best effort persistence; mode stays active in UI for current session.
    });
  }

  function handleToggleOutputLanguage() {
    setOutputLanguage((prev) => (prev === 'en' ? 'ta' : 'en'));
  }

  function handleSourceLockChange(enabled: boolean) {
    setSourceLocked(enabled);
    if (!sessionId) return;

    void setLearnSessionSourceLock(sessionId, enabled)
      .then(() => refreshSessionSummary(sessionId))
      .catch(() => {
        // Best effort persistence; local state remains active.
      });
  }

  async function ensureActiveSessionForArtifacts() {
    if (sessionId) {
      return sessionId;
    }
    return createNewSession({ resetChat: false, showToast: false, endCurrent: false });
  }

  async function handleGenerateChapterBrief() {
    if (chapterBriefLoading) return;

    setChapterBriefLoading(true);
    try {
      const activeSessionId = await ensureActiveSessionForArtifacts();
      if (!activeSessionId) {
        addToast('Unable to start a learning session for chapter brief.', 'error');
        return;
      }

      const brief = await generateLearnChapterBrief(activeSessionId, {
        language: outputLanguage,
        source_locked: sourceLocked,
      });

      setMessages((prev) => [
        ...prev,
        {
          id: `brief-${Date.now()}`,
          role: 'assistant',
          content: brief.markdown,
          tier: 'artifact',
          msgMetadata: {
            citations: brief.citations,
            output_language: brief.language,
            source_locked: sourceLocked,
            artifact_type: 'chapter_brief',
          },
          timestamp: new Date(),
        },
      ]);

      setLastGeneratedArtifact(`Chapter brief (${outputLanguageLabel(parseOutputLanguage(brief.language))})`);
      addToast('Chapter brief generated from lesson sources.', 'success');
      void refreshSessionSummary(activeSessionId);
    } catch (error) {
      addToast(getApiErrorMessage(error, 'Unable to generate chapter brief right now.'), 'error');
    } finally {
      setChapterBriefLoading(false);
    }
  }

  async function handleConvertSessionToNotes() {
    if (notesConverting) return;

    setNotesConverting(true);
    try {
      const activeSessionId = await ensureActiveSessionForArtifacts();
      if (!activeSessionId) {
        addToast('Unable to start a learning session for notes conversion.', 'error');
        return;
      }

      const notes = await convertLearnSessionToNotes(activeSessionId, {
        language: outputLanguage,
      });

      setMessages((prev) => [
        ...prev,
        {
          id: `notes-${Date.now()}`,
          role: 'assistant',
          content: `### Session Notes Saved\n\n**Title:** ${notes.title}\n**Language:** ${outputLanguageLabel(parseOutputLanguage(notes.language))}\n\n${notes.markdown}`,
          tier: 'artifact',
          msgMetadata: {
            output_language: notes.language,
            artifact_type: 'session_notes',
            note_id: notes.note_id,
          },
          timestamp: new Date(),
        },
      ]);

      setLastGeneratedArtifact(`Session notes (${outputLanguageLabel(parseOutputLanguage(notes.language))})`);
      addToast('Session converted into structured study notes.', 'success');
      void refreshSessionSummary(activeSessionId);
    } catch (error) {
      addToast(getApiErrorMessage(error, 'Unable to convert this session into notes.'), 'error');
    } finally {
      setNotesConverting(false);
    }
  }

  async function handleGenerateRevisionSheet() {
    if (revisionSheetLoading) return;

    setRevisionSheetLoading(true);
    try {
      if (!sessionId) {
        addToast('Start chatting first to generate a revision sheet from checkpoints.', 'info');
        return;
      }

      const revisionSheet = await generateLearnRevisionSheet(sessionId, {
        language: outputLanguage,
      });

      setMessages((prev) => [
        ...prev,
        {
          id: `revision-${Date.now()}`,
          role: 'assistant',
          content: revisionSheet.markdown,
          tier: 'artifact',
          msgMetadata: {
            output_language: revisionSheet.language,
            artifact_type: 'revision_sheet',
          },
          timestamp: new Date(),
        },
      ]);

      setLastGeneratedArtifact(`Revision sheet (${outputLanguageLabel(parseOutputLanguage(revisionSheet.language))})`);
      addToast('Revision sheet generated from checkpoint analytics.', 'success');
      void refreshSessionSummary(sessionId);
    } catch (error) {
      addToast(getApiErrorMessage(error, 'Unable to generate revision sheet right now.'), 'error');
    } finally {
      setRevisionSheetLoading(false);
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

          <div className="grid grid-cols-1 gap-2 xl:grid-cols-[minmax(0,1fr)_360px] xl:items-start">
            <LessonMissionCard
              context={lessonContext}
              isLoading={lessonContextLoading}
              error={lessonContextError}
              onUsePrompt={handleUseStarterPrompt}
              compact
            />

            <TutorModeSelector
              selectedMode={tutorMode}
              onChange={handleTutorModeChange}
              isDisabled={loading}
              compact
            />
          </div>

          {SHOW_NOTEBOOK_FEATURES_IN_LEARN ? (
            <Card className="glass border-border-strong shrink-0">
              <div className="p-2.5 flex flex-wrap items-center gap-2">
                <Button
                  size="sm"
                  variant={sourceLocked ? 'solid' : 'flat'}
                  color={sourceLocked ? 'secondary' : 'default'}
                  startContent={<ShieldCheck className="w-3.5 h-3.5" />}
                  onPress={() => handleSourceLockChange(!sourceLocked)}
                >
                  {sourceLocked ? 'Source Locked' : 'Source Open'}
                </Button>

                <Button
                  size="sm"
                  variant="flat"
                  startContent={<BookText className="w-3.5 h-3.5" />}
                  isLoading={chapterBriefLoading}
                  onPress={() => void handleGenerateChapterBrief()}
                >
                  Chapter Brief
                </Button>

                <Button
                  size="sm"
                  variant="flat"
                  startContent={<FileDown className="w-3.5 h-3.5" />}
                  isLoading={notesConverting}
                  onPress={() => void handleConvertSessionToNotes()}
                >
                  Session Notes
                </Button>

                <Button
                  size="sm"
                  variant="flat"
                  color="secondary"
                  isLoading={revisionSheetLoading}
                  onPress={() => void handleGenerateRevisionSheet()}
                >
                  Revision Sheet
                </Button>

                <Button
                  size="sm"
                  variant="light"
                  startContent={<Languages className="w-3.5 h-3.5" />}
                  onPress={handleToggleOutputLanguage}
                >
                  Output: {outputLanguageLabel(outputLanguage)}
                </Button>

                {sessionSummary ? (
                  <>
                    <Chip size="sm" variant="flat" className="text-[10px] uppercase tracking-wide">
                      {summaryLoading ? 'Summary...' : `Msgs: ${sessionSummary.message_count}`}
                    </Chip>
                    <Chip size="sm" variant="flat" className="text-[10px] uppercase tracking-wide">
                      Checkpoints: {sessionSummary.checkpoint_count}
                    </Chip>
                    {sessionSummary.avg_checkpoint_score !== null && sessionSummary.avg_checkpoint_score !== undefined ? (
                      <Chip size="sm" variant="flat" color="secondary" className="text-[10px] uppercase tracking-wide">
                        Avg: {Math.round(sessionSummary.avg_checkpoint_score)}%
                      </Chip>
                    ) : null}
                  </>
                ) : null}

                {lastGeneratedArtifact ? (
                  <p className="text-[11px] text-text-secondary">Latest: {lastGeneratedArtifact}</p>
                ) : null}
              </div>
            </Card>
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
            {checkpointPrompt && checkpointConceptKey ? (
              <div className="p-3 border-b border-border-subtle shrink-0">
                <CheckpointPulseCard
                  conceptKey={checkpointConceptKey}
                  prompt={checkpointPrompt}
                  responseText={checkpointResponse}
                  confidence={checkpointConfidence}
                  isSubmitting={checkpointSubmitting}
                  onResponseChange={setCheckpointResponse}
                  onConfidenceChange={setCheckpointConfidence}
                  onSubmit={handleSubmitCheckpoint}
                  onSkip={handleSkipCheckpoint}
                />
              </div>
            ) : null}

            <div ref={chatScrollRef} className="chat-surface flex-1 overflow-y-auto p-4 md:p-5">
              <div className="chat-thread mx-auto w-full max-w-[980px]">
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`chat-row ${msg.role === 'user' ? 'chat-row-user' : 'chat-row-assistant'}`}
                  >
                    {msg.role === 'assistant' && (
                      <div className="chat-avatar chat-avatar-assistant">
                        <Bot className="w-4 h-4 text-white" />
                      </div>
                    )}
                    <div
                      className={`${msg.role === 'user' ? 'chat-user-card chat-bubble-user' : 'chat-assistant-card chat-bubble-assistant'}`}
                    >
                      <div className="chat-message-meta">
                        <span className="chat-meta-role">{msg.role === 'assistant' ? 'APXMIND' : 'You'}</span>
                        <time className="chat-meta-time">{formatTimestamp(msg.timestamp)}</time>
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

                      {SHOW_NOTEBOOK_FEATURES_IN_LEARN && msg.role === 'assistant' && extractCitations(msg.msgMetadata).length > 0 ? (
                        <div className="mt-2 space-y-1.5">
                          <div className="flex flex-wrap gap-1.5">
                            {extractCitations(msg.msgMetadata).map((citation, index) => {
                              const citationKey = `${msg.id}:${citation.source_id}:${index}`;
                              const isOpen = expandedCitationKey === citationKey;
                              return (
                                <Button
                                  key={citationKey}
                                  size="sm"
                                  variant={isOpen ? 'solid' : 'flat'}
                                  color={isOpen ? 'secondary' : 'default'}
                                  onPress={() => setExpandedCitationKey(isOpen ? null : citationKey)}
                                  className="h-6 px-2 min-w-0"
                                >
                                  <span className="truncate max-w-[220px] text-[10px]">
                                    {citation.title}{citation.page ? ` · p.${citation.page}` : ''}
                                  </span>
                                </Button>
                              );
                            })}
                          </div>

                          {(() => {
                            const opened = extractCitations(msg.msgMetadata).find((citation, index) => {
                              const citationKey = `${msg.id}:${citation.source_id}:${index}`;
                              return citationKey === expandedCitationKey;
                            });

                            if (!opened) {
                              return null;
                            }

                            return (
                              <div
                                className="rounded-md p-2"
                                style={{
                                  background: 'var(--bg-2)',
                                  border: '1px solid var(--border-subtle)',
                                }}
                              >
                                <p className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>
                                  Source Evidence
                                </p>
                                <p className="text-[12px] mt-1" style={{ color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                                  {opened.snippet || 'No snippet available for this citation.'}
                                </p>
                                {opened.source ? (
                                  <p className="text-[10px] mt-1" style={{ color: 'var(--text-faint)' }}>
                                    {opened.source}
                                  </p>
                                ) : null}
                              </div>
                            );
                          })()}
                        </div>
                      ) : null}
                    </div>
                    {msg.role === 'user' && (
                      <div className="chat-avatar chat-avatar-user">
                        <User className="w-4 h-4 text-secondary" />
                      </div>
                    )}
                  </motion.div>
                ))}
                {loading && (
                  <div className="chat-row chat-row-assistant">
                    <div className="chat-avatar chat-avatar-assistant">
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                    <div className="chat-assistant-card chat-bubble-assistant px-4 py-3">
                      <Spinner size="sm" color="secondary" />
                    </div>
                  </div>
                )}
              </div>
            </div>

            <Divider />

            <div className="px-3 pt-2 flex flex-wrap items-center gap-2">
              <Chip
                size="sm"
                variant="flat"
                color="secondary"
                className="text-[10px] uppercase tracking-wide"
              >
                Mode: {TUTOR_MODE_LABELS[tutorMode]}
              </Chip>

              {SHOW_NOTEBOOK_FEATURES_IN_LEARN ? (
                <Chip
                  size="sm"
                  variant="flat"
                  color={sourceLocked ? 'warning' : 'default'}
                  className="text-[10px] uppercase tracking-wide"
                >
                  Source: {sourceLocked ? 'Locked' : 'Open'}
                </Chip>
              ) : null}

              {latestCheckpointScore !== null ? (
                <Chip
                  size="sm"
                  variant="flat"
                  color={latestCheckpointScore >= 70 ? 'success' : 'warning'}
                  className="text-[10px] uppercase tracking-wide"
                >
                  Checkpoint: {latestCheckpointScore}%
                </Chip>
              ) : null}

              {latestCheckpointFeedback ? (
                <p className="text-[11px] text-text-secondary">{latestCheckpointFeedback}</p>
              ) : null}

              {SHOW_NOTEBOOK_FEATURES_IN_LEARN && sessionSummary?.latest_checkpoint_score !== null && sessionSummary?.latest_checkpoint_score !== undefined ? (
                <p className="text-[11px] text-text-secondary">
                  Latest summary score: {sessionSummary.latest_checkpoint_score}%
                </p>
              ) : null}
            </div>

            <div className="p-3 pt-2 flex gap-2">
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
