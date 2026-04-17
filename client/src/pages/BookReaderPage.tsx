import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Card,
  CardBody,
  Button,
  Breadcrumbs,
  BreadcrumbItem,
  Chip,
  Textarea,
  Spinner,
} from '@heroui/react';
import {
  ArrowLeft,
  Maximize2,
  Minimize2,
  Sparkles,
  Wand2,
  RefreshCw,
  X,
  ChevronDown,
  ChevronUp,
  ChevronsLeft,
  ChevronsRight,
  GripVertical,
  MessageSquare,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';

import { askBookTutor, type TutorTaskMode, type TutorChatTurn } from '../lib/bookTutorService';
import { normalizeLanguage } from '../lib/language';
import { useProfileStore } from '../store/profileStore';

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString();

type SourceType = 'selected_text' | 'ocr' | 'manual' | 'prior_response';

interface TutorTurn {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  task?: TutorTaskMode;
  timestamp: Date;
}

interface ContextSnippet {
  id: string;
  text: string;
  sourceType: SourceType;
  pageNumber?: number;
}

interface FloatingActionState {
  text: string;
  left: number;
  top: number;
  pageNumber?: number;
  sourceType: SourceType;
}

const TASK_OPTIONS: Array<{ key: TutorTaskMode; label: string }> = [
  { key: 'summary', label: 'Summary' },
  { key: 'detailed_explain', label: 'Detailed Explain' },
  { key: 'examples', label: 'Examples' },
  { key: 'key_points', label: 'Key Points' },
  { key: 'questions', label: 'Questions' },
  { key: 'follow_up', label: 'Follow-up Q&A' },
];

const FOLLOW_UP_SUGGESTIONS: Array<{ label: string; query: string; mode: TutorTaskMode }> = [
  {
    label: 'Expand more',
    query: 'Expand this explanation with deeper but still student-friendly detail.',
    mode: 'follow_up',
  },
  {
    label: 'Explain with examples',
    query: 'Explain this with practical examples tied to the context.',
    mode: 'examples',
  },
  {
    label: 'Give practice questions',
    query: 'Generate conceptual and exam-style practice questions from this context.',
    mode: 'questions',
  },
];

const CONTEXT_CAPTURE_HELP_TEXT =
  'Select textbook text first. If direct selection is blocked, copy the text (Ctrl+C) and then click Ask AI or Use Selection.';

const MIN_PDF_ZOOM = 0.7;
const MAX_PDF_ZOOM = 2;
const DEFAULT_PDF_ZOOM = 0.7;

const MIN_TUTOR_PANEL_WIDTH = 420;
const MAX_TUTOR_PANEL_WIDTH = 920;
const DEFAULT_TUTOR_PANEL_WIDTH = 560;
const EXPANDED_TUTOR_PANEL_WIDTH = 760;

function clampTutorPanelWidth(width: number): number {
  if (typeof window === 'undefined') {
    return Math.min(Math.max(width, MIN_TUTOR_PANEL_WIDTH), MAX_TUTOR_PANEL_WIDTH);
  }

  const viewportLimitedMax = Math.min(MAX_TUTOR_PANEL_WIDTH, Math.floor(window.innerWidth * 0.65));
  const effectiveMax = Math.max(MIN_TUTOR_PANEL_WIDTH, viewportLimitedMax);
  return Math.min(Math.max(width, MIN_TUTOR_PANEL_WIDTH), effectiveMax);
}

function formatClock(value: Date) {
  return value.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function taskLabel(task: TutorTaskMode): string {
  return TASK_OPTIONS.find((option) => option.key === task)?.label ?? task;
}

function inferTaskBySelectionLength(text: string): TutorTaskMode {
  return text.trim().length > 700 ? 'summary' : 'detailed_explain';
}

function defaultPromptForTask(task: TutorTaskMode): string {
  const byTask: Record<TutorTaskMode, string> = {
    summary: 'Summarize this clearly in medium length with key ideas first.',
    detailed_explain: 'Explain this step by step in medium length and keep it easy to scan.',
    examples: 'Give practical examples based on this context.',
    key_points: 'Extract concise key points for quick revision.',
    questions: 'Generate conceptual and exam-style questions only.',
    follow_up: 'Answer this follow-up based on the current context and chat history.',
  };
  return byTask[task];
}

function sourceBadgeLabel(snippet: ContextSnippet): string {
  if (snippet.sourceType === 'prior_response') {
    return '[Prior Resp Context]';
  }

  const source =
    snippet.sourceType === 'ocr'
      ? 'Image Snip • OCR'
      : snippet.sourceType === 'manual'
        ? 'Manual Note'
        : 'Selected Text';

  return snippet.pageNumber ? `${source} • Page ${snippet.pageNumber}` : `${source} • Current page`;
}

function buildContextText(snippets: ContextSnippet[]): string {
  return snippets
    .map((snippet, index) => {
      const tag = sourceBadgeLabel(snippet);
      return `[Context ${index + 1}: ${tag}]\n${snippet.text}`;
    })
    .join('\n\n---\n\n');
}

export function BookReaderPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const profile = useProfileStore((s) => s.profile);
  const selectedLanguage = normalizeLanguage(profile?.preferredLanguage);
  const file = params.get('file') || '';
  const pdfFileUrl = `/api/books/${file}`;
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Extract a readable chapter name from the path
  const parts = file.split('/');
  const folder = parts.length > 1 ? parts[parts.length - 2] : '';
  const fileName = parts[parts.length - 1]?.replace('.pdf', '') || 'Book';
  const displayName = folder ? `${folder} / ${fileName}` : fileName;

  const inferredPageNumber = useMemo(() => {
    const raw = Number(params.get('page') || '');
    return Number.isFinite(raw) && raw > 0 ? raw : undefined;
  }, [params]);

  const pdfViewerRef = useRef<HTMLDivElement | null>(null);
  const [pdfNumPages, setPdfNumPages] = useState(0);
  const [pdfPageNumber, setPdfPageNumber] = useState(inferredPageNumber ?? 1);
  const [pdfPageWidth, setPdfPageWidth] = useState(0);
  const [pdfZoom, setPdfZoom] = useState(DEFAULT_PDF_ZOOM);
  const [renderedPageCount, setRenderedPageCount] = useState(1);
  const [didInitialPageScroll, setDidInitialPageScroll] = useState(false);
  const [pdfLoadError, setPdfLoadError] = useState<string | null>(null);

  const [taskMode, setTaskMode] = useState<TutorTaskMode>('detailed_explain');
  const [chatInput, setChatInput] = useState('');
  const [contextSnippets, setContextSnippets] = useState<ContextSnippet[]>([]);
  const [floatingAction, setFloatingAction] = useState<FloatingActionState | null>(null);
  const [isTutorOpen, setIsTutorOpen] = useState(false);
  const [tutorPanelWidth, setTutorPanelWidth] = useState(() => clampTutorPanelWidth(DEFAULT_TUTOR_PANEL_WIDTH));
  const [isTutorPanelExpanded, setIsTutorPanelExpanded] = useState(false);
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
  const [inlineContextExpanded, setInlineContextExpanded] = useState(false);
  const [manualContextDraft, setManualContextDraft] = useState('');
  const [tutorTurns, setTutorTurns] = useState<TutorTurn[]>([]);
  const [isAskingTutor, setIsAskingTutor] = useState(false);
  const [tutorError, setTutorError] = useState<string | null>(null);
  const floatingActionBarRef = useRef<HTMLDivElement | null>(null);
  const isResizingTutorPanelRef = useRef(false);
  const resizeStartXRef = useRef(0);
  const resizeStartWidthRef = useRef(0);

  const lastAssistantTurnId = useMemo(() => {
    for (let i = tutorTurns.length - 1; i >= 0; i -= 1) {
      if (tutorTurns[i].role === 'assistant') return tutorTurns[i].id;
    }
    return null;
  }, [tutorTurns]);

  useEffect(() => {
    if (inferredPageNumber) {
      setPdfPageNumber(inferredPageNumber);
      setRenderedPageCount((prev) => Math.max(prev, inferredPageNumber));
      setDidInitialPageScroll(false);
    }
  }, [inferredPageNumber]);

  useEffect(() => {
    const container = pdfViewerRef.current;
    if (!container) return;

    const updateWidth = () => {
      const next = Math.max(280, Math.floor(container.clientWidth - 18));
      setPdfPageWidth(next);
    };

    updateWidth();

    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', updateWidth);
      return () => window.removeEventListener('resize', updateWidth);
    }

    const observer = new ResizeObserver(updateWidth);
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const onFullscreenChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };

    document.addEventListener('fullscreenchange', onFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', onFullscreenChange);
    };
  }, []);

  useEffect(() => {
    const onWindowResize = () => {
      setTutorPanelWidth((prev) => clampTutorPanelWidth(prev));
    };

    window.addEventListener('resize', onWindowResize);
    return () => window.removeEventListener('resize', onWindowResize);
  }, []);

  useEffect(() => {
    const onMouseMove = (event: MouseEvent) => {
      if (!isResizingTutorPanelRef.current) return;

      const deltaX = event.clientX - resizeStartXRef.current;
      const nextWidth = clampTutorPanelWidth(resizeStartWidthRef.current - deltaX);
      setTutorPanelWidth(nextWidth);
      setIsTutorPanelExpanded(false);
    };

    const onMouseUp = () => {
      if (!isResizingTutorPanelRef.current) return;
      isResizingTutorPanelRef.current = false;
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);

    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };
  }, []);

  function getSelectionPageNumber(selection: Selection | null): number | undefined {
    if (!selection || selection.rangeCount === 0) {
      return undefined;
    }

    const node = selection.anchorNode;
    const element = node instanceof Element ? node : node?.parentElement;
    const host = element?.closest('[data-page-number]');
    const raw = host?.getAttribute('data-page-number');
    const page = raw ? Number(raw) : Number.NaN;
    return Number.isFinite(page) && page > 0 ? page : undefined;
  }

  function inferSelectionSourceType(selection: Selection | null): SourceType {
    if (!selection || selection.rangeCount === 0) {
      return 'selected_text';
    }

    const node = selection.anchorNode;
    const element = node instanceof Element ? node : node?.parentElement;
    if (element?.closest('.chat-thread')) {
      return 'prior_response';
    }

    return 'selected_text';
  }

  useEffect(() => {
    function hideFloatingAction() {
      setFloatingAction(null);
    }

    function updateFloatingActionFromSelection(event: Event) {
      const target = event.target as Node | null;
      if (target && floatingActionBarRef.current?.contains(target)) {
        return;
      }

      const active = document.activeElement as HTMLElement | null;
      if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.isContentEditable)) {
        return;
      }

      const selection = window.getSelection();
      const selectedText = selection?.toString().trim() || '';
      if (!selection || selection.isCollapsed || selectedText.length < 8 || selection.rangeCount === 0) {
        setFloatingAction(null);
        return;
      }

      const rect = selection.getRangeAt(0).getBoundingClientRect();
      if (!rect || (rect.width === 0 && rect.height === 0)) {
        setFloatingAction(null);
        return;
      }

      const left = Math.max(110, Math.min(window.innerWidth - 110, rect.left + rect.width / 2));
      const top = Math.max(14, rect.top - 12);
      const pageNumber = getSelectionPageNumber(selection);
      const sourceType = inferSelectionSourceType(selection);
      if (pageNumber) {
        setPdfPageNumber(pageNumber);
      }
      setFloatingAction({ text: selectedText, left, top, pageNumber, sourceType });
    }

    document.addEventListener('mouseup', updateFloatingActionFromSelection);
    document.addEventListener('keyup', updateFloatingActionFromSelection);
    document.addEventListener('scroll', hideFloatingAction, true);
    window.addEventListener('resize', hideFloatingAction);

    return () => {
      document.removeEventListener('mouseup', updateFloatingActionFromSelection);
      document.removeEventListener('keyup', updateFloatingActionFromSelection);
      document.removeEventListener('scroll', hideFloatingAction, true);
      window.removeEventListener('resize', hideFloatingAction);
    };
  }, []);

  function toggleFullscreen() {
    const el = document.getElementById('pdf-container');
    if (!el) return;
    if (!document.fullscreenElement) {
      el.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => { });
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => { });
    }
  }

  function addSnippet(text: string, sourceType: SourceType, pageNumber?: number): ContextSnippet[] {
    const cleanText = text.trim();
    if (!cleanText) return contextSnippets;

    const snippet: ContextSnippet = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      text: cleanText,
      sourceType,
      pageNumber: pageNumber ?? inferredPageNumber ?? pdfPageNumber,
    };

    // Keep one active context snippet for a clear, predictable Ask AI flow.
    const next = [snippet];
    setContextSnippets(next);
    setInlineContextExpanded(false);
    return next;
  }

  function removeSnippet(snippetId: string) {
    setContextSnippets((prev) => prev.filter((row) => row.id !== snippetId));
    setInlineContextExpanded(false);
  }

  function captureSelectionAsContext() {
    void (async () => {
      const captured = await captureContextFromSelectionOrClipboard();
      if (!captured) {
        setTutorError(CONTEXT_CAPTURE_HELP_TEXT);
        return;
      }

      addSnippet(captured.text, captured.sourceType, captured.pageNumber);
      setIsTutorOpen(true);
      setTutorError(null);
      setFloatingAction(null);
    })();
  }

  async function captureContextFromSelectionOrClipboard(): Promise<{
    text: string;
    sourceType: SourceType;
    pageNumber?: number;
  } | null> {
    const selection = window.getSelection();
    const selectedText = (selection?.toString() || '').trim();
    if (selectedText) {
      return {
        text: selectedText,
        sourceType: inferSelectionSourceType(selection),
        pageNumber: getSelectionPageNumber(selection),
      };
    }

    if (typeof navigator === 'undefined' || !navigator.clipboard?.readText) {
      return null;
    }

    try {
      const clipboardText = (await navigator.clipboard.readText()).trim();
      if (!clipboardText) {
        return null;
      }
      return { text: clipboardText, sourceType: 'selected_text', pageNumber: pdfPageNumber };
    } catch {
      return null;
    }
  }

  async function askTutor(options?: {
    taskOverride?: TutorTaskMode;
    userQueryOverride?: string;
    contextOverride?: string;
    sourceOverride?: SourceType;
    pageNumberOverride?: number;
  }) {
    let snippetsInUse = contextSnippets;
    let contextText = (options?.contextOverride || buildContextText(snippetsInUse)).trim();

    if (!contextText) {
      const captured = await captureContextFromSelectionOrClipboard();
      if (captured) {
        snippetsInUse = addSnippet(captured.text, options?.sourceOverride || captured.sourceType, captured.pageNumber);
        contextText = buildContextText(snippetsInUse).trim();
      }
    }

    if (!contextText) {
      setTutorError(CONTEXT_CAPTURE_HELP_TEXT);
      return;
    }

    if (isAskingTutor) {
      return;
    }

    const effectiveTask = options?.taskOverride || taskMode;
    const effectivePageNumber =
      options?.pageNumberOverride || snippetsInUse[0]?.pageNumber || inferredPageNumber || pdfPageNumber;
    const effectiveUserQuery =
      options?.userQueryOverride?.trim() ||
      chatInput.trim() ||
      defaultPromptForTask(effectiveTask);

    const userTurn: TutorTurn = {
      id: `${Date.now()}-user`,
      role: 'user',
      content: effectiveUserQuery,
      task: effectiveTask,
      timestamp: new Date(),
    };

    const historyUserTurn: TutorChatTurn = {
      role: 'user',
      content: effectiveUserQuery,
      task: effectiveTask,
    };

    const historyPayload: TutorChatTurn[] = [
      ...tutorTurns
        .filter((turn) => turn.id !== 'welcome')
        .map((turn): TutorChatTurn => ({ role: turn.role, content: turn.content, task: turn.task })),
      historyUserTurn,
    ].slice(-8);

    setTutorTurns((prev) => [...prev, userTurn]);
    setChatInput('');
    setTutorError(null);
    setIsTutorOpen(true);
    setIsAskingTutor(true);

    try {
      const latestSource =
        options?.sourceOverride ||
        snippetsInUse[0]?.sourceType ||
        'selected_text';

      const response = await askBookTutor({
        context: contextText,
        task: effectiveTask,
        language: selectedLanguage,
        page_number: effectivePageNumber,
        chat_history: historyPayload,
        user_query: effectiveUserQuery,
        source_type: latestSource,
      });

      const assistantContent = response.caution
        ? `${response.response}\n\n> Note: ${response.caution}`
        : response.response;

      const assistantTurn: TutorTurn = {
        id: `${Date.now()}-assistant`,
        role: 'assistant',
        content: assistantContent,
        task: response.mode,
        timestamp: new Date(),
      };
      setTutorTurns((prev) => [...prev, assistantTurn]);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Tutor request failed.';
      setTutorError(message);
    } finally {
      setIsAskingTutor(false);
    }
  }

  function addManualContext(sourceType: SourceType) {
    if (!manualContextDraft.trim()) return;
    addSnippet(manualContextDraft, sourceType, pdfPageNumber);
    setManualContextDraft('');
    setShowAdvancedOptions(false);
    setTutorError(null);
    setIsTutorOpen(true);
  }

  async function handleFloatingAction(action: 'ask_ai' | 'summary' | 'detailed_explain', selectedText: string) {
    if (!selectedText.trim()) return;

    const selectionSource = floatingAction?.sourceType || 'selected_text';
    const selectedPage = floatingAction?.pageNumber;
    const nextSnippets = addSnippet(selectedText, selectionSource, selectedPage);
    const mode =
      action === 'ask_ai'
        ? inferTaskBySelectionLength(selectedText)
        : action;

    setTaskMode(mode);
    setFloatingAction(null);

    await askTutor({
      taskOverride: mode,
      userQueryOverride:
        action === 'summary'
          ? 'Summarize this context in a concise, readable way.'
          : action === 'detailed_explain'
            ? 'Explain this in clear, step-by-step language.'
            : defaultPromptForTask(mode),
      contextOverride: buildContextText(nextSnippets),
      sourceOverride: selectionSource,
      pageNumberOverride: selectedPage,
    });
  }

  function handlePdfLoadSuccess({ numPages }: { numPages: number }) {
    setPdfLoadError(null);
    setPdfNumPages(numPages);
    const desired = inferredPageNumber || pdfPageNumber || 1;
    const initialCount = Math.min(numPages, Math.max(desired, 4));
    setRenderedPageCount(initialCount);
    setDidInitialPageScroll(false);
    setPdfPageNumber((prev) => {
      const desired = inferredPageNumber || prev;
      return Math.min(Math.max(desired, 1), numPages);
    });
  }

  function handlePdfLoadError(error: Error) {
    setPdfLoadError(error.message || 'Unable to load PDF.');
  }

  function handlePdfScroll(event: React.UIEvent<HTMLDivElement>) {
    const target = event.currentTarget;
    const nearBottom = target.scrollTop + target.clientHeight >= target.scrollHeight - 260;
    if (nearBottom && pdfNumPages > 0) {
      setRenderedPageCount((prev) => Math.min(pdfNumPages, prev + 3));
    }
  }

  useEffect(() => {
    if (!inferredPageNumber || didInitialPageScroll || inferredPageNumber > renderedPageCount) {
      return;
    }

    const target = document.querySelector(`[data-page-number=\"${inferredPageNumber}\"]`) as HTMLElement | null;
    if (target) {
      target.scrollIntoView({ block: 'start' });
      setDidInitialPageScroll(true);
    }
  }, [inferredPageNumber, renderedPageCount, didInitialPageScroll]);

  function clearTutorConversation() {
    setTutorTurns([]);
    setChatInput('');
    setTutorError(null);
  }

  const latestContextSnippet = contextSnippets.length > 0 ? contextSnippets[0] : null;
  const latestContextWordCount = latestContextSnippet
    ? latestContextSnippet.text.trim().split(/\s+/).filter(Boolean).length
    : 0;
  const latestContextCharCount = latestContextSnippet?.text.length ?? 0;

  function startTutorPanelResize(event: React.MouseEvent<HTMLDivElement>) {
    if (event.button !== 0) return;
    isResizingTutorPanelRef.current = true;
    resizeStartXRef.current = event.clientX;
    resizeStartWidthRef.current = tutorPanelWidth;
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';
    event.preventDefault();
  }

  function toggleTutorPanelExpand() {
    if (isTutorPanelExpanded) {
      setTutorPanelWidth(clampTutorPanelWidth(DEFAULT_TUTOR_PANEL_WIDTH));
      setIsTutorPanelExpanded(false);
      return;
    }

    setTutorPanelWidth(clampTutorPanelWidth(EXPANDED_TUTOR_PANEL_WIDTH));
    setIsTutorPanelExpanded(true);
  }

  function handleChatKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void askTutor();
    }
  }

  return (
    <div className="ui-page-shell ui-page-shell-wide space-y-3">
      {/* Breadcrumbs */}
      <Breadcrumbs aria-label="Book reader breadcrumbs">
        <BreadcrumbItem onPress={() => navigate('/home')}>Home</BreadcrumbItem>
        <BreadcrumbItem onPress={() => navigate('/books')}>Books</BreadcrumbItem>
        <BreadcrumbItem>{displayName}</BreadcrumbItem>
      </Breadcrumbs>

      <div>
        <h1 className="ui-page-title">Book Reader</h1>
        <p className="ui-page-subtitle">{displayName}</p>
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <Button
          variant="light"
          size="sm"
          startContent={<ArrowLeft className="w-4 h-4" />}
          onPress={() => navigate('/books')}
        >
          Back to Books
        </Button>

        <div className="flex items-center gap-2">
          <Chip size="sm" variant="flat" className="ui-pill ui-chip-neutral">
            PDF Viewer
          </Chip>
          <Button
            variant="flat"
            size="sm"
            isIconOnly
            aria-label="Toggle fullscreen"
            onPress={toggleFullscreen}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      {/* PDF viewer — react-pdf text layer enables in-app text selection */}
      <div
        className={`book-reader-layout grid gap-3 ${isTutorOpen ? 'book-reader-layout-open' : ''}`}
        style={
          isTutorOpen
            ? ({ '--tutor-panel-width': `${tutorPanelWidth}px` } as React.CSSProperties)
            : undefined
        }
      >
        <div
          id="pdf-container"
          ref={pdfViewerRef}
          className="glass ui-card-md overflow-hidden"
          style={{ height: 'calc(100dvh - 10rem)' }}
        >
          <div className="book-pdf-viewer h-full w-full overflow-auto p-2" onScroll={handlePdfScroll} style={{ background: 'var(--bg-1)' }}>
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Pages loaded {Math.min(renderedPageCount, pdfNumPages || 0)}{pdfNumPages > 0 ? ` / ${pdfNumPages}` : ''}
              </p>
              <div className="flex items-center gap-1">
                <Button
                  size="sm"
                  variant="light"
                  isDisabled={pdfZoom <= MIN_PDF_ZOOM}
                  onPress={() => setPdfZoom((prev) => Math.max(MIN_PDF_ZOOM, Number((prev - 0.1).toFixed(2))))}
                >
                  -
                </Button>
                <Chip size="sm" variant="flat" className="ui-pill ui-chip-neutral">
                  {Math.round(pdfZoom * 100)}%
                </Chip>
                <Button
                  size="sm"
                  variant="light"
                  isDisabled={pdfZoom >= MAX_PDF_ZOOM}
                  onPress={() => setPdfZoom((prev) => Math.min(MAX_PDF_ZOOM, Number((prev + 0.1).toFixed(2))))}
                >
                  +
                </Button>
                <Button
                  size="sm"
                  variant="light"
                  onPress={() => window.open(pdfFileUrl, '_blank', 'noopener,noreferrer')}
                >
                  Open Native
                </Button>
              </div>
            </div>

            {pdfLoadError ? (
              <div className="rounded-md border p-3 text-sm" style={{ borderColor: 'var(--danger-500)', color: 'var(--danger-700)', background: 'var(--danger-100)' }}>
                {pdfLoadError}
              </div>
            ) : (
              <>
                <Document
                  file={pdfFileUrl}
                  onLoadSuccess={handlePdfLoadSuccess}
                  onLoadError={handlePdfLoadError}
                  loading={
                    <div className="py-8 flex items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                      <Spinner size="sm" />
                      Loading PDF...
                    </div>
                  }
                >
                  <div className="space-y-3">
                    {Array.from({ length: Math.min(renderedPageCount, pdfNumPages || 0) }, (_, index) => {
                      const pageNumber = index + 1;
                      return (
                        <div key={pageNumber} data-page-number={pageNumber} className="book-pdf-page-shell">
                          <Page
                            pageNumber={pageNumber}
                            width={pdfPageWidth > 0 ? Math.floor(pdfPageWidth * pdfZoom) : undefined}
                            renderTextLayer
                            renderAnnotationLayer={false}
                            loading={
                              <div className="py-8 flex items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                                <Spinner size="sm" />
                                Rendering page {pageNumber}...
                              </div>
                            }
                          />
                        </div>
                      );
                    })}
                  </div>
                </Document>

                {pdfNumPages > 0 && renderedPageCount < pdfNumPages && (
                  <p className="mt-2 text-xs text-center" style={{ color: 'var(--text-muted)' }}>
                    Scroll down to load more pages...
                  </p>
                )}
              </>
            )}
          </div>
        </div>

        {isTutorOpen && (
          <div
            className="book-reader-splitter"
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize AI tutor panel"
            onMouseDown={startTutorPanelResize}
          >
            <div className="book-reader-splitter-line" />
            <div className="book-reader-splitter-buttons" onMouseDown={(event) => event.stopPropagation()}>
              <Button
                size="sm"
                variant="light"
                isIconOnly
                aria-label={isTutorPanelExpanded ? 'Restore panel width' : 'Expand AI tutor panel'}
                onPress={toggleTutorPanelExpand}
              >
                {isTutorPanelExpanded ? <ChevronsRight className="w-3.5 h-3.5" /> : <ChevronsLeft className="w-3.5 h-3.5" />}
              </Button>
              <GripVertical className="w-3.5 h-3.5" />
            </div>
            <div className="book-reader-splitter-line" />
          </div>
        )}

        {isTutorOpen && (
          <Card
            className="glass book-reader-tutor-panel"
            style={{
              height: 'calc(100dvh - 10rem)',
              border: '1px solid var(--border-subtle)',
              background: 'var(--bg-2)',
            }}
          >
            <CardBody className="p-3 h-full flex flex-col gap-3">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4" style={{ color: 'var(--accent)' }} />
                  <h2 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>AI Tutor</h2>
                </div>
                <div className="flex items-center gap-1">
                  <Chip size="sm" variant="flat" className="ui-pill ui-chip-neutral">Context-first</Chip>
                  <Button
                    variant="light"
                    size="sm"
                    isIconOnly
                    aria-label="Close tutor"
                    onPress={() => setIsTutorOpen(false)}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              <div className="book-reader-mode-row">
                {TASK_OPTIONS.map((option) => (
                  <Button
                    key={option.key}
                    size="sm"
                    variant={taskMode === option.key ? 'solid' : 'flat'}
                    color={taskMode === option.key ? 'primary' : 'default'}
                    onPress={() => setTaskMode(option.key)}
                    className="min-w-fit h-7 min-h-7 px-2 text-[11px]"
                  >
                    {option.label}
                  </Button>
                ))}
              </div>

              <div className="rounded-lg border px-2 py-1.5" style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-1)' }}>
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[10px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Context snippets</p>
                  <div className="flex items-center gap-1">
                    <Button
                      size="sm"
                      variant="light"
                      onPress={captureSelectionAsContext}
                      startContent={<Wand2 className="w-3.5 h-3.5" />}
                      className="h-7 min-h-7 px-2 text-[11px]"
                    >
                      Use Selection
                    </Button>
                    <Button
                      size="sm"
                      variant="light"
                      onPress={() => setShowAdvancedOptions((prev) => !prev)}
                      endContent={showAdvancedOptions ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      className="h-7 min-h-7 px-2 text-[11px]"
                    >
                      Add Context
                    </Button>
                  </div>
                </div>

                <p className="mt-1 text-[11px]" style={{ color: 'var(--text-muted)' }}>
                  {contextSnippets.length > 0
                    ? '1 active snippet. New selections replace the current snippet.'
                    : 'Select text, then click Ask AI, Summarize, or Explain.'}
                </p>

                {showAdvancedOptions && (
                  <div className="mt-1.5 space-y-1.5">
                    <Textarea
                      aria-label="Manual or OCR context"
                      placeholder="Paste OCR text or manual notes"
                      value={manualContextDraft}
                      onValueChange={setManualContextDraft}
                      minRows={2}
                      maxRows={4}
                    />
                    <div className="flex gap-1.5">
                      <Button size="sm" variant="flat" className="h-7 min-h-7 px-2 text-[11px]" onPress={() => addManualContext('ocr')}>Use as OCR snippet</Button>
                      <Button size="sm" variant="flat" className="h-7 min-h-7 px-2 text-[11px]" onPress={() => addManualContext('manual')}>Use as manual note</Button>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex-1 overflow-y-auto rounded-lg border p-2" style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-1)' }}>
                <div className="chat-thread">
                  {tutorTurns.map((turn) => (
                    <div
                      key={turn.id}
                      className={turn.role === 'user' ? 'chat-user-card' : 'chat-assistant-card'}
                    >
                      <div className="chat-message-meta">
                        <span>{turn.role === 'user' ? 'You' : 'Tutor'}</span>
                        {turn.task && <span>{taskLabel(turn.task)}</span>}
                        <span>{formatClock(turn.timestamp)}</span>
                      </div>
                      <div className="chat-markdown">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{turn.content}</ReactMarkdown>
                      </div>

                      {turn.role === 'assistant' && turn.id === lastAssistantTurnId && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {FOLLOW_UP_SUGGESTIONS.map((suggestion) => (
                            <Button
                              key={`${turn.id}-${suggestion.label}`}
                              size="sm"
                              variant="flat"
                              className="text-[11px]"
                              onPress={() => {
                                setTaskMode(suggestion.mode);
                                void askTutor({
                                  taskOverride: suggestion.mode,
                                  userQueryOverride: suggestion.query,
                                });
                              }}
                            >
                              {suggestion.label}
                            </Button>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}

                  {isAskingTutor && (
                    <div className="chat-assistant-card px-4 py-3">
                      <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                        <Spinner size="sm" />
                        Preparing context-grounded explanation...
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {tutorError && (
                <div className="rounded-lg px-3 py-2 text-xs" style={{ background: 'var(--danger-100)', color: 'var(--danger-700)' }}>
                  {tutorError}
                </div>
              )}

              {latestContextSnippet && (
                <div className="rounded-lg border px-2 py-1.5" style={{ borderColor: 'var(--border-subtle)', background: 'var(--bg-1)' }}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-[11px] font-medium" style={{ color: 'var(--text-secondary)' }}>
                        {sourceBadgeLabel(latestContextSnippet)}
                      </p>
                      <p
                        className="mt-0.5 text-xs whitespace-pre-wrap"
                        style={{
                          color: 'var(--text-secondary)',
                          display: '-webkit-box',
                          WebkitLineClamp: inlineContextExpanded ? 3 : 2,
                          WebkitBoxOrient: 'vertical',
                          overflow: 'hidden',
                        }}
                      >
                        {latestContextSnippet.text}
                      </p>
                      <p className="mt-1 text-[10px]" style={{ color: 'var(--text-muted)' }}>
                        {latestContextWordCount} words • {latestContextCharCount} chars
                      </p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <Button
                        size="sm"
                        variant="light"
                        isIconOnly
                        aria-label={inlineContextExpanded ? 'Collapse context preview' : 'Expand context preview'}
                        onPress={() => setInlineContextExpanded((prev) => !prev)}
                      >
                        {inlineContextExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      </Button>
                      <Button
                        size="sm"
                        variant="light"
                        isIconOnly
                        aria-label="Remove active context"
                        onPress={() => removeSnippet(latestContextSnippet.id)}
                      >
                        <X className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex items-end gap-2">
                <Textarea
                  aria-label="Tutor input"
                  placeholder="Ask anything about this..."
                  value={chatInput}
                  onValueChange={setChatInput}
                  minRows={1}
                  maxRows={4}
                  onKeyDown={handleChatKeyDown}
                />
                <div className="flex flex-col gap-1">
                  <Button
                    size="sm"
                    color="primary"
                    onPress={() => void askTutor()}
                    isLoading={isAskingTutor}
                    startContent={<MessageSquare className="w-4 h-4" />}
                  >
                    Ask AI
                  </Button>
                  <Button
                    size="sm"
                    variant="flat"
                    color="danger"
                    onPress={clearTutorConversation}
                    startContent={<RefreshCw className="w-3.5 h-3.5" />}
                  >
                    Clear
                  </Button>
                </div>
              </div>
            </CardBody>
          </Card>
        )}
      </div>

      {!isTutorOpen && (
        <div className="fixed bottom-5 right-5 z-30">
          <Button
            color="primary"
            onPress={() => setIsTutorOpen(true)}
            startContent={<Sparkles className="w-4 h-4" />}
            className="shadow-lg"
          >
            Open AI Tutor
          </Button>
        </div>
      )}

      {floatingAction && (
        <div
          className="fixed z-40"
          style={{
            left: floatingAction.left,
            top: floatingAction.top,
            transform: 'translate(-50%, -100%)',
          }}
        >
          <div
            ref={floatingActionBarRef}
            onMouseDown={(event) => event.preventDefault()}
            className="rounded-full px-2 py-1 flex items-center gap-1.5"
            style={{
              background: 'var(--bg-2)',
              border: '1px solid var(--border-subtle)',
              boxShadow: '0 8px 24px rgba(0,0,0,0.14)',
            }}
          >
            <Button size="sm" variant="light" onPress={() => void handleFloatingAction('ask_ai', floatingAction.text)}>Ask AI</Button>
            <Button size="sm" variant="light" onPress={() => void handleFloatingAction('summary', floatingAction.text)}>Summarize</Button>
            <Button size="sm" variant="light" onPress={() => void handleFloatingAction('detailed_explain', floatingAction.text)}>Explain</Button>
          </div>
        </div>
      )}

      {/* Fallback for browsers without inline PDF support */}
      <noscript>
        <p className="text-center text-default-500">
          Your browser does not support inline PDF viewing.{' '}
          <a href={pdfFileUrl} className="text-primary underline">
            Click here to open the PDF
          </a>
        </p>
      </noscript>
    </div>
  );
}
