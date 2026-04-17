import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Button,
  Card,
  Chip,
  Divider,
  Spinner,
  Textarea,
} from '@heroui/react';
import {
  BookText,
  FileUp,
  FileDown,
  Languages,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Trash2,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  clearLearnMessages,
  convertLearnSessionToNotes,
  deleteLearnSession,
  deleteLearnNotebookSource,
  generateLearnChapterBrief,
  generateLearnRevisionSheet,
  getLearnMessages,
  getLearnSessionSourceLock,
  getLearnSessionSummary,
  listLearnNotebookSources,
  listLearnSessionsPaged,
  sendLearnMessage,
  setLearnSessionSourceLock,
  startLearnSession,
  type LearnMessage,
  type LearnMessageMetadata,
  type LearnNotebookSource,
  type LearnSession,
  type LearnSessionSummary,
  type LearnSourceCitation,
  type NotebookUploadMode,
  uploadLearnNotebookSource,
} from '../lib/learnSessionService';
import { getApiErrorMessage } from '../lib/api';
import { getAllSubjects, getSubjectLessons, type Lesson, type Subject } from '../lib/subjectService';
import { useToast } from '../hooks/useToast';

type OutputLanguage = 'en' | 'ta';

interface NotebookChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  tier?: string | null;
  msgMetadata?: LearnMessageMetadata | null;
  createdAt: string;
}

interface NotebookArtifact {
  title: string;
  markdown: string;
  metadataLine?: string;
  citations?: LearnSourceCitation[];
}

function parseOutputLanguage(value: string | null | undefined): OutputLanguage {
  return value === 'ta' ? 'ta' : 'en';
}

function outputLanguageLabel(value: OutputLanguage): string {
  return value === 'ta' ? 'Tamil' : 'English';
}

function formatTimestamp(raw: string): string {
  const dt = new Date(raw);
  if (Number.isNaN(dt.getTime())) {
    return '--:--';
  }
  return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function mapPersistedMessage(message: LearnMessage): NotebookChatMessage {
  return {
    id: String(message.id),
    role: message.role,
    content: message.content,
    tier: message.tier,
    msgMetadata: message.msg_metadata || null,
    createdAt: message.created_at,
  };
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

export function NotebookStudioPage() {
  const { addToast } = useToast();

  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubject, setSelectedSubject] = useState<string>('biology');
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [selectedLessonId, setSelectedLessonId] = useState<number | null>(null);

  const [sessions, setSessions] = useState<LearnSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<NotebookChatMessage[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);

  const [sourceLocked, setSourceLocked] = useState(false);
  const [useUploadedSources, setUseUploadedSources] = useState(false);
  const [uploadMode, setUploadMode] = useState<NotebookUploadMode>('quick');
  const [outputLanguage, setOutputLanguage] = useState<OutputLanguage>('en');
  const [sessionSummary, setSessionSummary] = useState<LearnSessionSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [notebookSources, setNotebookSources] = useState<LearnNotebookSource[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(false);
  const [uploadingSource, setUploadingSource] = useState(false);
  const [clearingSession, setClearingSession] = useState(false);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);

  const [composer, setComposer] = useState('');
  const [sending, setSending] = useState(false);
  const [creatingSession, setCreatingSession] = useState(false);

  const [chapterBriefLoading, setChapterBriefLoading] = useState(false);
  const [notesConverting, setNotesConverting] = useState(false);
  const [revisionSheetLoading, setRevisionSheetLoading] = useState(false);
  const [artifact, setArtifact] = useState<NotebookArtifact | null>(null);
  const [expandedCitationKey, setExpandedCitationKey] = useState<string | null>(null);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) ?? null,
    [activeSessionId, sessions]
  );

  async function refreshSessions() {
    setSessionsLoading(true);
    try {
      const result = await listLearnSessionsPaged({ limit: 20, offset: 0 });
      setSessions(result.sessions);
    } catch (error) {
      addToast(getApiErrorMessage(error, 'Unable to load learning sessions.'), 'error');
    } finally {
      setSessionsLoading(false);
    }
  }

  async function refreshSummary(targetSessionId: string | null) {
    if (!targetSessionId) {
      setSessionSummary(null);
      return;
    }

    setSummaryLoading(true);
    try {
      const summary = await getLearnSessionSummary(targetSessionId);
      setSessionSummary(summary);
    } catch {
      setSessionSummary(null);
    } finally {
      setSummaryLoading(false);
    }
  }

  async function refreshNotebookSources(targetSessionId: string | null) {
    if (!targetSessionId) {
      setNotebookSources([]);
      return;
    }

    setSourcesLoading(true);
    try {
      const sources = await listLearnNotebookSources(targetSessionId);
      setNotebookSources(sources);
    } catch {
      setNotebookSources([]);
    } finally {
      setSourcesLoading(false);
    }
  }

  async function openSession(sessionId: string) {
    setActiveSessionId(sessionId);
    setLoadingMessages(true);
    setExpandedCitationKey(null);

    try {
      const [messages, sourceState, summary, sources] = await Promise.all([
        getLearnMessages(sessionId, 120),
        getLearnSessionSourceLock(sessionId).catch(() => null),
        getLearnSessionSummary(sessionId).catch(() => null),
        listLearnNotebookSources(sessionId).catch(() => [] as LearnNotebookSource[]),
      ]);

      setChatMessages(messages.map(mapPersistedMessage));
      setSourceLocked(Boolean(sourceState?.enabled));
      setSessionSummary(summary);
      setNotebookSources(sources);
    } catch (error) {
      addToast(getApiErrorMessage(error, 'Unable to open selected session.'), 'error');
    } finally {
      setLoadingMessages(false);
    }
  }

  async function loadSubjects() {
    const result = await getAllSubjects();
    if (result.success && result.data && result.data.length > 0) {
      setSubjects(result.data);
      if (!result.data.find((item) => item.name === selectedSubject)) {
        setSelectedSubject(result.data[0].name);
      }
      return;
    }
    addToast(result.error || 'Unable to load subjects.', 'error');
  }

  async function loadLessons(subject: string) {
    const response = await getSubjectLessons(subject);
    if (response.success && response.data) {
      setLessons(response.data);
      setSelectedLessonId(response.data[0]?.id ?? null);
      return;
    }

    setLessons([]);
    setSelectedLessonId(null);
  }

  useEffect(() => {
    void loadSubjects();
    void refreshSessions();
  }, []);

  useEffect(() => {
    if (!selectedSubject) {
      setLessons([]);
      setSelectedLessonId(null);
      return;
    }

    void loadLessons(selectedSubject);
  }, [selectedSubject]);

  async function ensureActiveSession(): Promise<string | null> {
    if (activeSessionId) {
      return activeSessionId;
    }

    if (!selectedSubject) {
      addToast('Select a subject first.', 'info');
      return null;
    }

    setCreatingSession(true);
    try {
      const created = await startLearnSession(selectedSubject, selectedLessonId ?? undefined);
      setSessions((prev) => [created, ...prev.filter((session) => session.id !== created.id)]);
      await openSession(created.id);
      return created.id;
    } catch (error) {
      addToast(getApiErrorMessage(error, 'Unable to create a notebook session.'), 'error');
      return null;
    } finally {
      setCreatingSession(false);
    }
  }

  async function handleCreateSession() {
    const sessionId = await ensureActiveSession();
    if (sessionId) {
      addToast('Notebook session is ready.', 'success');
    }
  }

  async function handleSendMessage() {
    const question = composer.trim();
    if (!question || sending) {
      return;
    }

    setSending(true);
    setComposer('');

    const sid = await ensureActiveSession();
    if (!sid) {
      setSending(false);
      return;
    }

    const optimisticMessage: NotebookChatMessage = {
      id: `local-user-${Date.now()}`,
      role: 'user',
      content: question,
      createdAt: new Date().toISOString(),
    };

    setChatMessages((prev) => [...prev, optimisticMessage]);

    try {
      const shouldUseUploads = useUploadedSources && notebookSources.length > 0;
      if (useUploadedSources && notebookSources.length === 0) {
        addToast('Uploaded source mode is enabled, but no PDF is attached to this session yet.', 'info');
      }

      const persisted = await sendLearnMessage(
        sid,
        question,
        outputLanguage,
        'guided',
        sourceLocked,
        shouldUseUploads,
        shouldUseUploads ? uploadMode : undefined
      );
      setChatMessages((prev) => [...prev, mapPersistedMessage(persisted)]);
      await refreshSummary(sid);
      await refreshSessions();
    } catch (error) {
      addToast(getApiErrorMessage(error, 'Unable to send message right now.'), 'error');
    } finally {
      setSending(false);
    }
  }

  async function handleUploadPdf(file: File) {
    if (uploadingSource) {
      return;
    }

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      addToast('Please select a PDF file.', 'info');
      return;
    }

    const sid = await ensureActiveSession();
    if (!sid) {
      return;
    }

    setUploadingSource(true);
    try {
      const uploaded = await uploadLearnNotebookSource(sid, file, uploadMode, outputLanguage);
      await refreshNotebookSources(sid);

      const updatedMessages = await getLearnMessages(sid, 120);
      setChatMessages(updatedMessages.map(mapPersistedMessage));

      addToast(
        `${uploaded.file_name} uploaded and summarized (${uploaded.index_mode.toUpperCase()} mode, ${uploaded.chunk_count} chunks).`,
        'success'
      );
    } catch (error) {
      addToast(getApiErrorMessage(error, 'Unable to upload PDF source.'), 'error');
    } finally {
      setUploadingSource(false);
      if (uploadInputRef.current) {
        uploadInputRef.current.value = '';
      }
    }
  }

  async function handleDeleteSource(sourceId: string) {
    if (!activeSessionId) {
      return;
    }

    try {
      await deleteLearnNotebookSource(activeSessionId, sourceId);
      await refreshNotebookSources(activeSessionId);
      addToast('Notebook source removed.', 'success');
    } catch (error) {
      addToast(getApiErrorMessage(error, 'Unable to remove source.'), 'error');
    }
  }

  async function handleDeleteSession(sessionId: string) {
    if (deletingSessionId) {
      return;
    }

    const confirmed = window.confirm(
      'Delete this entire session? This removes transcript and uploaded PDFs for that session.'
    );
    if (!confirmed) {
      return;
    }

    setDeletingSessionId(sessionId);
    try {
      await deleteLearnSession(sessionId);

      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
        setChatMessages([]);
        setSourceLocked(false);
        setSessionSummary(null);
        setNotebookSources([]);
        setArtifact(null);
        setExpandedCitationKey(null);
        setComposer('');
      }

      await refreshSessions();
      addToast('Session deleted.', 'success');
    } catch (error) {
      addToast(getApiErrorMessage(error, 'Unable to delete this session.'), 'error');
    } finally {
      setDeletingSessionId(null);
    }
  }

  async function handleClearSession() {
    if (!activeSessionId || clearingSession) {
      return;
    }

    const confirmed = window.confirm(
      'Clear all messages in this session? Uploaded PDFs will remain attached.'
    );
    if (!confirmed) {
      return;
    }

    setClearingSession(true);
    try {
      await clearLearnMessages(activeSessionId);
      setChatMessages([]);
      setArtifact(null);
      setExpandedCitationKey(null);
      setComposer('');
      await refreshSummary(activeSessionId);
      await refreshSessions();
      addToast('Session transcript cleared.', 'success');
    } catch (error) {
      addToast(getApiErrorMessage(error, 'Unable to clear this session.'), 'error');
    } finally {
      setClearingSession(false);
    }
  }

  async function handleToggleSourceLock() {
    const next = !sourceLocked;
    setSourceLocked(next);

    if (!activeSessionId) {
      return;
    }

    try {
      await setLearnSessionSourceLock(activeSessionId, next);
      await refreshSummary(activeSessionId);
    } catch (error) {
      setSourceLocked(!next);
      addToast(getApiErrorMessage(error, 'Unable to update source lock state.'), 'error');
    }
  }

  async function handleGenerateChapterBrief() {
    if (chapterBriefLoading) {
      return;
    }

    setChapterBriefLoading(true);
    try {
      const sid = await ensureActiveSession();
      if (!sid) return;

      const brief = await generateLearnChapterBrief(sid, {
        language: outputLanguage,
        source_locked: sourceLocked,
      });

      setArtifact({
        title: 'Chapter Brief',
        markdown: brief.markdown,
        metadataLine: `${outputLanguageLabel(parseOutputLanguage(brief.language))} output • ${brief.citations.length} citations`,
        citations: brief.citations,
      });

      await refreshSummary(sid);
      addToast('Chapter brief generated.', 'success');
    } catch (error) {
      addToast(getApiErrorMessage(error, 'Unable to generate chapter brief.'), 'error');
    } finally {
      setChapterBriefLoading(false);
    }
  }

  async function handleConvertSessionToNotes() {
    if (notesConverting) {
      return;
    }

    setNotesConverting(true);
    try {
      const sid = await ensureActiveSession();
      if (!sid) return;

      const notes = await convertLearnSessionToNotes(sid, { language: outputLanguage });
      setArtifact({
        title: 'Session Notes',
        markdown: notes.markdown,
        metadataLine: `Saved note: ${notes.title} (${notes.note_id})`,
      });

      await refreshSummary(sid);
      addToast('Session converted to notes.', 'success');
    } catch (error) {
      addToast(getApiErrorMessage(error, 'Unable to convert this session into notes.'), 'error');
    } finally {
      setNotesConverting(false);
    }
  }

  async function handleGenerateRevisionSheet() {
    if (revisionSheetLoading) {
      return;
    }

    setRevisionSheetLoading(true);
    try {
      const sid = await ensureActiveSession();
      if (!sid) return;

      const revision = await generateLearnRevisionSheet(sid, { language: outputLanguage });
      setArtifact({
        title: 'Revision Sheet',
        markdown: revision.markdown,
        metadataLine: `${revision.items.length} tracked concepts`,
      });

      await refreshSummary(sid);
      addToast('Revision sheet generated.', 'success');
    } catch (error) {
      addToast(getApiErrorMessage(error, 'Unable to generate revision sheet.'), 'error');
    } finally {
      setRevisionSheetLoading(false);
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      <Card className="glass border-border-strong">
        <div className="p-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5" style={{ color: 'var(--accent)' }} />
            <div>
              <h1 className="ui-section-title">Notebook Studio</h1>
              <p className="text-sm text-text-secondary">Standalone workspace for source lock, citations, briefs, notes, and revision sheets.</p>
            </div>
          </div>
          <Chip size="sm" variant="flat" color="secondary">
            {sessionsLoading ? 'Loading sessions' : `${sessions.length} sessions`}
          </Chip>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[320px_minmax(0,1fr)] xl:items-start">
        <Card className="glass border-border-strong">
          <div className="p-3 space-y-3">
            <div className="space-y-1.5">
              <p className="text-xs uppercase tracking-wide text-text-secondary">Subject</p>
              <select
                value={selectedSubject}
                onChange={(event) => setSelectedSubject(event.target.value)}
                className="w-full rounded-md border px-2 py-2 text-sm"
                style={{
                  background: 'var(--bg-2)',
                  borderColor: 'var(--border-default)',
                  color: 'var(--text-primary)',
                }}
              >
                {subjects.map((subject) => (
                  <option key={subject.id} value={subject.name}>
                    {subject.display_name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <p className="text-xs uppercase tracking-wide text-text-secondary">Lesson</p>
              <select
                value={selectedLessonId ?? ''}
                onChange={(event) => {
                  const next = Number(event.target.value);
                  setSelectedLessonId(Number.isFinite(next) ? next : null);
                }}
                className="w-full rounded-md border px-2 py-2 text-sm"
                style={{
                  background: 'var(--bg-2)',
                  borderColor: 'var(--border-default)',
                  color: 'var(--text-primary)',
                }}
              >
                {lessons.length ? (
                  lessons.map((lesson) => (
                    <option key={lesson.id} value={lesson.id}>
                      {lesson.title}
                    </option>
                  ))
                ) : (
                  <option value="">No lessons</option>
                )}
              </select>
            </div>

            <Button
              color="secondary"
              onPress={() => void handleCreateSession()}
              isLoading={creatingSession}
              className="w-full"
            >
              Start Notebook Session
            </Button>

            <Button
              variant="flat"
              startContent={<RefreshCw className="w-4 h-4" />}
              onPress={() => void refreshSessions()}
              isLoading={sessionsLoading}
              className="w-full"
            >
              Refresh Sessions
            </Button>

            <Divider />

            <div className="space-y-1.5 max-h-[360px] overflow-y-auto pr-1">
              {sessions.map((session) => {
                const isActive = session.id === activeSessionId;
                return (
                  <div key={session.id} className="flex items-start gap-1.5">
                    <button
                      type="button"
                      onClick={() => {
                        void openSession(session.id);
                      }}
                      className="w-full text-left rounded-md px-2 py-2"
                      style={{
                        background: isActive ? 'var(--accent-soft)' : 'var(--bg-2)',
                        border: `1px solid ${isActive ? 'var(--accent-border)' : 'var(--border-subtle)'}`,
                      }}
                    >
                      <p className="text-sm font-medium capitalize" style={{ color: 'var(--text-primary)' }}>
                        {session.subject} session
                      </p>
                      <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                        {new Date(session.started_at).toLocaleString()}
                      </p>
                    </button>

                    <Button
                      size="sm"
                      variant="light"
                      isIconOnly
                      aria-label={`Delete ${session.subject} session`}
                      isLoading={deletingSessionId === session.id}
                      isDisabled={Boolean(deletingSessionId)}
                      onPress={() => void handleDeleteSession(session.id)}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                );
              })}
              {!sessionsLoading && sessions.length === 0 ? (
                <p className="text-sm text-text-secondary">No sessions yet.</p>
              ) : null}
            </div>

            <Divider />

            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs uppercase tracking-wide text-text-secondary">Uploaded PDFs</p>
                <Chip size="sm" variant="flat" className="text-[10px] uppercase tracking-wide">
                  {sourcesLoading ? 'Loading' : notebookSources.length}
                </Chip>
              </div>

              <div className="space-y-1.5 max-h-[190px] overflow-y-auto pr-1">
                {notebookSources.map((source) => (
                  <div
                    key={source.source_id}
                    className="rounded-md p-2"
                    style={{
                      background: 'var(--bg-2)',
                      border: '1px solid var(--border-subtle)',
                    }}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-xs font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                          {source.file_name}
                        </p>
                        <p className="text-[10px]" style={{ color: 'var(--text-faint)' }}>
                          {source.index_mode.toUpperCase()} • {source.chunk_count} chunks • {source.page_count} pages
                        </p>
                      </div>
                      <Button
                        size="sm"
                        variant="light"
                        isIconOnly
                        onPress={() => void handleDeleteSource(source.source_id)}
                        aria-label={`Remove ${source.file_name}`}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>
                ))}

                {!sourcesLoading && notebookSources.length === 0 ? (
                  <p className="text-xs text-text-secondary">No PDF uploaded for this session.</p>
                ) : null}
              </div>
            </div>
          </div>
        </Card>

        <div className="space-y-4 min-w-0">
          <Card className="glass border-border-strong">
            <div className="p-3 flex flex-wrap items-center gap-2">
              <input
                ref={uploadInputRef}
                type="file"
                accept="application/pdf,.pdf"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) {
                    void handleUploadPdf(file);
                  }
                }}
              />

              <Button
                size="sm"
                variant={sourceLocked ? 'solid' : 'flat'}
                color={sourceLocked ? 'secondary' : 'default'}
                startContent={<ShieldCheck className="w-3.5 h-3.5" />}
                onPress={() => void handleToggleSourceLock()}
              >
                {sourceLocked ? 'Source Locked' : 'Source Open'}
              </Button>

              <Button
                size="sm"
                variant="light"
                startContent={<Languages className="w-3.5 h-3.5" />}
                onPress={() => setOutputLanguage((prev) => (prev === 'en' ? 'ta' : 'en'))}
              >
                Output: {outputLanguageLabel(outputLanguage)}
              </Button>

              <Button
                size="sm"
                variant={useUploadedSources ? 'solid' : 'flat'}
                color={useUploadedSources ? 'secondary' : 'default'}
                startContent={<BookText className="w-3.5 h-3.5" />}
                onPress={() => setUseUploadedSources((prev) => !prev)}
              >
                Uploaded Context: {useUploadedSources ? 'On' : 'Off'}
              </Button>

              <Button
                size="sm"
                variant="flat"
                color={uploadMode === 'full' ? 'secondary' : 'default'}
                onPress={() => setUploadMode((prev) => (prev === 'quick' ? 'full' : 'quick'))}
              >
                Upload Mode: {uploadMode.toUpperCase()}
              </Button>

              <Button
                size="sm"
                variant="flat"
                startContent={<FileUp className="w-3.5 h-3.5" />}
                isLoading={uploadingSource}
                onPress={() => uploadInputRef.current?.click()}
              >
                Upload PDF
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
                variant="flat"
                startContent={<RefreshCw className="w-3.5 h-3.5" />}
                isLoading={summaryLoading}
                isDisabled={!activeSessionId}
                onPress={() => void refreshSummary(activeSessionId)}
              >
                Refresh Summary
              </Button>

              <Button
                size="sm"
                variant="flat"
                color="danger"
                startContent={<Trash2 className="w-3.5 h-3.5" />}
                isLoading={clearingSession}
                isDisabled={!activeSessionId}
                onPress={() => void handleClearSession()}
              >
                Clear Transcript
              </Button>

              {sessionSummary ? (
                <>
                  <Chip size="sm" variant="flat" className="text-[10px] uppercase tracking-wide">
                    Messages: {sessionSummary.message_count}
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
            </div>
          </Card>

          <Card className="glass border-border-strong flex flex-col min-h-[56vh]">
            <div className="p-3 border-b border-border-subtle">
              <p className="text-sm text-text-secondary">
                {activeSession
                  ? `Working session: ${activeSession.subject} • ${new Date(activeSession.started_at).toLocaleString()}`
                  : 'Open an existing session or create a new one to start.'}
              </p>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {loadingMessages ? (
                <div className="py-10 flex items-center justify-center">
                  <Spinner size="sm" color="secondary" label="Loading session" />
                </div>
              ) : chatMessages.length === 0 ? (
                <p className="text-sm text-text-secondary">No transcript yet. Ask a question to begin.</p>
              ) : (
                chatMessages.map((msg) => {
                  const citations = extractCitations(msg.msgMetadata);
                  return (
                    <div
                      key={msg.id}
                      className="rounded-lg p-3"
                      style={{
                        background: msg.role === 'user' ? 'var(--accent-soft)' : 'var(--bg-2)',
                        border: '1px solid var(--border-subtle)',
                      }}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>
                          {msg.role === 'assistant' ? 'Tutor' : 'You'}
                        </p>
                        <p className="text-xs" style={{ color: 'var(--text-faint)' }}>
                          {formatTimestamp(msg.createdAt)}
                        </p>
                      </div>

                      {msg.role === 'assistant' ? (
                        <div className="chat-markdown">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                        </div>
                      ) : (
                        <p className="text-sm whitespace-pre-wrap" style={{ color: 'var(--text-primary)' }}>
                          {msg.content}
                        </p>
                      )}

                      {msg.tier ? (
                        <Chip size="sm" variant="flat" className="mt-2 text-[10px] uppercase tracking-wide">
                          {msg.tier}
                        </Chip>
                      ) : null}

                      {msg.role === 'assistant' && citations.length > 0 ? (
                        <div className="mt-2 space-y-1.5">
                          <div className="flex flex-wrap gap-1.5">
                            {citations.map((citation, index) => {
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
                            const opened = citations.find((citation, index) => {
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
                                  background: 'var(--bg-1)',
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
                  );
                })
              )}
            </div>

            <Divider />

            <div className="p-3 flex gap-2">
              <Textarea
                aria-label="Notebook message"
                minRows={1}
                maxRows={3}
                placeholder="Ask a source-grounded question..."
                value={composer}
                onValueChange={setComposer}
                className="flex-1"
                variant="bordered"
                isDisabled={sending}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    void handleSendMessage();
                  }
                }}
              />
              <Button
                color="secondary"
                onPress={() => void handleSendMessage()}
                isDisabled={!composer.trim() || sending}
                isLoading={sending}
              >
                Send
              </Button>
            </div>
          </Card>

          {artifact ? (
            <Card className="glass border-border-strong">
              <div className="p-3 space-y-2">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <h2 className="ui-section-title" style={{ fontSize: 15 }}>
                    {artifact.title}
                  </h2>
                  {artifact.metadataLine ? (
                    <Chip size="sm" variant="flat" className="text-[10px] uppercase tracking-wide">
                      {artifact.metadataLine}
                    </Chip>
                  ) : null}
                </div>

                <div className="chat-markdown">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{artifact.markdown}</ReactMarkdown>
                </div>

                {artifact.citations && artifact.citations.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {artifact.citations.map((citation, index) => (
                      <Chip key={`${citation.source_id}:${index}`} size="sm" variant="flat" className="text-[10px]">
                        {citation.title}{citation.page ? ` · p.${citation.page}` : ''}
                      </Chip>
                    ))}
                  </div>
                ) : null}
              </div>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
