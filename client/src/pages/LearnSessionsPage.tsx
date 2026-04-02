import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    BreadcrumbItem,
    Breadcrumbs,
    Button,
    Card,
    Chip,
    Divider,
    Spinner,
} from '@heroui/react';
import { History, MessageSquare, RefreshCw, Trash2 } from 'lucide-react';
import {
    clearLearnMessages,
    deleteLearnMessage,
    deleteLearnSession,
    getLearnMessages,
    getLearnSession,
    listLearnSessionsPaged,
    type LearnMessage,
    type LearnSession,
    type LearnSessionStatus,
} from '../lib/learnSessionService';
import { getApiErrorMessage } from '../lib/api';
import { useToast } from '../hooks/useToast';

type SubjectFilter = 'all' | 'physics' | 'chemistry' | 'biology';
type StatusFilter = 'all' | LearnSessionStatus;

const PAGE_SIZE = 8;

function formatDuration(session: LearnSession) {
    if (!session.duration_minutes || session.duration_minutes <= 0) {
        return 'active';
    }
    return `${Math.max(1, Math.round(session.duration_minutes))} min`;
}

export function LearnSessionsPage() {
    const navigate = useNavigate();
    const { addToast } = useToast();

    const [subjectFilter, setSubjectFilter] = useState<SubjectFilter>('all');
    const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
    const [offset, setOffset] = useState(0);

    const [sessions, setSessions] = useState<LearnSession[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [selectedSession, setSelectedSession] = useState<LearnSession | null>(null);
    const [sessionMessages, setSessionMessages] = useState<LearnMessage[]>([]);
    const [detailsLoading, setDetailsLoading] = useState(false);
    const [busySessionId, setBusySessionId] = useState<string | null>(null);
    const [busyMessageId, setBusyMessageId] = useState<number | null>(null);

    const page = Math.floor(offset / PAGE_SIZE) + 1;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

    const title = useMemo(() => {
        const parts = ['Recent Learn Sessions'];
        if (subjectFilter !== 'all') {
            parts.push(subjectFilter[0].toUpperCase() + subjectFilter.slice(1));
        }
        if (statusFilter !== 'all') {
            parts.push(statusFilter === 'active' ? 'Active' : 'Completed');
        }
        return parts.join(' • ');
    }, [statusFilter, subjectFilter]);

    const loadSessions = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await listLearnSessionsPaged({
                subject: subjectFilter === 'all' ? undefined : subjectFilter,
                status: statusFilter === 'all' ? undefined : statusFilter,
                limit: PAGE_SIZE,
                offset,
            });
            setSessions(response.sessions);
            setTotal(response.total);
        } catch (err) {
            setError(getApiErrorMessage(err, 'Unable to load learning sessions.'));
        } finally {
            setLoading(false);
        }
    }, [offset, statusFilter, subjectFilter]);

    async function loadSessionDetails(sessionId: string) {
        setDetailsLoading(true);
        setError(null);
        try {
            const [meta, messages] = await Promise.all([
                getLearnSession(sessionId),
                getLearnMessages(sessionId, 160),
            ]);
            setSelectedSession(meta);
            setSessionMessages(messages);
        } catch (err) {
            setError(getApiErrorMessage(err, 'Unable to load selected session transcript.'));
        } finally {
            setDetailsLoading(false);
        }
    }

    useEffect(() => {
        void loadSessions();
    }, [loadSessions]);

    function handleSubjectFilter(next: SubjectFilter) {
        setSubjectFilter(next);
        setOffset(0);
        setSelectedSession(null);
        setSessionMessages([]);
    }

    function handleStatusFilter(next: StatusFilter) {
        setStatusFilter(next);
        setOffset(0);
        setSelectedSession(null);
        setSessionMessages([]);
    }

    async function handleDeleteSession(session: LearnSession) {
        if (busySessionId) return;
        setBusySessionId(session.id);
        setError(null);
        try {
            await deleteLearnSession(session.id);
            if (selectedSession?.id === session.id) {
                setSelectedSession(null);
                setSessionMessages([]);
            }
            addToast('Session deleted.', 'success');
            await loadSessions();
        } catch (err) {
            setError(getApiErrorMessage(err, 'Unable to delete this session.'));
        } finally {
            setBusySessionId(null);
        }
    }

    async function handleClearTranscript() {
        if (!selectedSession || busySessionId) return;
        setBusySessionId(selectedSession.id);
        setError(null);
        try {
            await clearLearnMessages(selectedSession.id);
            setSessionMessages([]);
            addToast('All transcript messages cleared.', 'success');
        } catch (err) {
            setError(getApiErrorMessage(err, 'Unable to clear transcript messages.'));
        } finally {
            setBusySessionId(null);
        }
    }

    async function handleDeleteMessage(messageId: number) {
        if (!selectedSession || busyMessageId) return;
        setBusyMessageId(messageId);
        setError(null);
        try {
            await deleteLearnMessage(selectedSession.id, messageId);
            setSessionMessages((prev) => prev.filter((msg) => msg.id !== messageId));
        } catch (err) {
            setError(getApiErrorMessage(err, 'Unable to remove this message.'));
        } finally {
            setBusyMessageId(null);
        }
    }

    function handleReopen(session: LearnSession) {
        const subject = session.subject?.toLowerCase();
        if (!subject || !session.lesson_id) {
            addToast('This session is not linked to a lesson. Open from the subject page instead.', 'info');
            return;
        }

        navigate(`/subject/${subject}/lesson/${session.lesson_id}/learn`, {
            state: { reopenSessionId: session.id },
        });
    }

    return (
        <div className="max-w-4xl mx-auto space-y-4">
            <Breadcrumbs aria-label="Learn sessions breadcrumbs">
                <BreadcrumbItem onPress={() => navigate('/home')}>Home</BreadcrumbItem>
                <BreadcrumbItem>Learn Sessions</BreadcrumbItem>
            </Breadcrumbs>

            <Card className="glass border-border-default">
                <div className="p-4 space-y-3">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div className="flex items-center gap-2">
                            <History className="w-4 h-4 text-primary" />
                            <h1 className="ui-section-title" style={{ fontSize: 16 }}>{title}</h1>
                        </div>
                        <Button
                            size="sm"
                            color="secondary"
                            variant="flat"
                            startContent={<RefreshCw className="w-3 h-3" />}
                            onPress={() => void loadSessions()}
                            isLoading={loading}
                        >
                            Refresh
                        </Button>
                    </div>

                    <div className="space-y-2">
                        <p className="text-xs text-text-muted">Subject</p>
                        <div className="flex items-center gap-2 flex-wrap">
                            {(['all', 'physics', 'chemistry', 'biology'] as SubjectFilter[]).map((item) => (
                                <Button
                                    key={item}
                                    size="sm"
                                    variant={subjectFilter === item ? 'flat' : 'bordered'}
                                    color={subjectFilter === item ? 'secondary' : 'default'}
                                    className="capitalize"
                                    onPress={() => handleSubjectFilter(item)}
                                >
                                    {item}
                                </Button>
                            ))}
                        </div>
                    </div>

                    <div className="space-y-2">
                        <p className="text-xs text-text-muted">Status</p>
                        <div className="flex items-center gap-2 flex-wrap">
                            {(['all', 'active', 'completed'] as StatusFilter[]).map((item) => (
                                <Button
                                    key={item}
                                    size="sm"
                                    variant={statusFilter === item ? 'flat' : 'bordered'}
                                    color={statusFilter === item ? 'secondary' : 'default'}
                                    className="capitalize"
                                    onPress={() => handleStatusFilter(item)}
                                >
                                    {item}
                                </Button>
                            ))}
                        </div>
                    </div>

                    {error ? (
                        <Chip color="danger" variant="flat" size="sm" className="w-full justify-center">
                            {error}
                        </Chip>
                    ) : null}

                    {loading ? (
                        <div className="py-5 flex items-center justify-center">
                            <Spinner size="sm" color="secondary" label="Loading sessions" />
                        </div>
                    ) : sessions.length ? (
                        <div className="space-y-2">
                            {sessions.map((session) => {
                                const isSelected = selectedSession?.id === session.id;
                                const isActive = !session.ended_at;
                                return (
                                    <Card key={session.id} className="glass border border-border-default">
                                        <div className="p-3 space-y-2">
                                            <div className="flex items-start justify-between gap-2">
                                                <div>
                                                    <p className="text-sm font-medium capitalize">{session.subject} session</p>
                                                    <p className="text-xs text-text-muted">
                                                        {new Date(session.started_at).toLocaleString()} • {formatDuration(session)}
                                                    </p>
                                                </div>
                                                <div className="flex items-center gap-1.5">
                                                    <Chip size="sm" variant="flat" color={isActive ? 'warning' : 'success'}>
                                                        {isActive ? 'active' : 'completed'}
                                                    </Chip>
                                                    {session.lesson_id ? (
                                                        <Chip size="sm" variant="flat">lesson {session.lesson_id}</Chip>
                                                    ) : null}
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-1.5 flex-wrap">
                                                <Button
                                                    size="sm"
                                                    variant={isSelected ? 'flat' : 'bordered'}
                                                    color="secondary"
                                                    isLoading={detailsLoading && isSelected}
                                                    onPress={() => {
                                                        if (isSelected) {
                                                            setSelectedSession(null);
                                                            setSessionMessages([]);
                                                            return;
                                                        }
                                                        void loadSessionDetails(session.id);
                                                    }}
                                                >
                                                    {isSelected ? 'Hide Transcript' : 'Review'}
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="flat"
                                                    color="primary"
                                                    onPress={() => handleReopen(session)}
                                                >
                                                    Reopen
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="flat"
                                                    color="danger"
                                                    startContent={<Trash2 className="w-3 h-3" />}
                                                    isLoading={busySessionId === session.id}
                                                    onPress={() => void handleDeleteSession(session)}
                                                >
                                                    Delete Session
                                                </Button>
                                            </div>
                                        </div>
                                    </Card>
                                );
                            })}
                        </div>
                    ) : (
                        <p className="text-sm text-text-muted">No sessions found for these filters.</p>
                    )}

                    <Divider />

                    <div className="flex items-center justify-between gap-2 flex-wrap">
                        <p className="text-xs text-text-muted">Page {page} of {totalPages} • {total} total sessions</p>
                        <div className="flex items-center gap-2">
                            <Button
                                size="sm"
                                variant="bordered"
                                isDisabled={offset === 0 || loading}
                                onPress={() => setOffset((prev) => Math.max(0, prev - PAGE_SIZE))}
                            >
                                Previous
                            </Button>
                            <Button
                                size="sm"
                                variant="bordered"
                                isDisabled={offset + PAGE_SIZE >= total || loading}
                                onPress={() => setOffset((prev) => prev + PAGE_SIZE)}
                            >
                                Next
                            </Button>
                        </div>
                    </div>
                </div>
            </Card>

            {selectedSession ? (
                <Card className="glass border-border-default">
                    <div className="p-4 space-y-3">
                        <div className="flex items-center justify-between gap-2 flex-wrap">
                            <div className="flex items-center gap-2">
                                <MessageSquare className="w-4 h-4 text-secondary" />
                                <h2 className="ui-section-title" style={{ fontSize: 15 }}>Transcript</h2>
                            </div>
                            <div className="flex items-center gap-1.5 flex-wrap">
                                <Button
                                    size="sm"
                                    variant="flat"
                                    color="danger"
                                    isLoading={busySessionId === selectedSession.id}
                                    onPress={() => void handleClearTranscript()}
                                >
                                    Clear All Messages
                                </Button>
                                <Button
                                    size="sm"
                                    variant="flat"
                                    color="secondary"
                                    onPress={() => handleReopen(selectedSession)}
                                >
                                    Reopen This Session
                                </Button>
                            </div>
                        </div>

                        <div className="space-y-2 max-h-105 overflow-y-auto pr-1">
                            {sessionMessages.length ? (
                                sessionMessages.map((msg) => (
                                    <Card key={msg.id} className="glass border border-border-default">
                                        <div className="p-2.5 space-y-1.5">
                                            <div className="flex items-center justify-between gap-2">
                                                <p className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">
                                                    {msg.role === 'assistant' ? 'APXMIND' : 'You'}
                                                </p>
                                                <div className="flex items-center gap-2">
                                                    <p className="text-[11px] text-text-muted">
                                                        {new Date(msg.created_at).toLocaleString()}
                                                    </p>
                                                    <Button
                                                        isIconOnly
                                                        size="sm"
                                                        variant="light"
                                                        color="danger"
                                                        aria-label="Delete message"
                                                        isLoading={busyMessageId === msg.id}
                                                        onPress={() => void handleDeleteMessage(msg.id)}
                                                    >
                                                        <Trash2 className="w-3 h-3" />
                                                    </Button>
                                                </div>
                                            </div>
                                            <p className="text-xs whitespace-pre-wrap">{msg.content}</p>
                                        </div>
                                    </Card>
                                ))
                            ) : (
                                <p className="text-xs text-text-muted">No stored messages in this session.</p>
                            )}
                        </div>
                    </div>
                </Card>
            ) : null}
        </div>
    );
}
