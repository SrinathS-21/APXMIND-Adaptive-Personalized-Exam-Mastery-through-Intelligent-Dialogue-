import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  CardBody,
  CardHeader,
  Button,
  Chip,
  Input,
  Tabs,
  Tab,
  Textarea,
  Divider,
  Tooltip,
} from '@heroui/react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Library,
  BookMarked,
  StickyNote,
  Clock,
  Search,
  Plus,
  Trash2,
  BookOpen,
  ExternalLink,
} from 'lucide-react';
import apiClient, { getApiErrorMessage } from '../lib/api';
import { useToast } from '../hooks/useToast';

interface BookmarkItem {
  id: string;
  title: string;
  subject: string;
  lessonId?: number;
  path?: string;
  savedAt: string;
}

interface StudyNoteItem {
  id: string;
  title: string;
  content: string;
  subject?: string;
  createdAt: string;
  updatedAt: string;
}

interface BookmarkApiItem {
  id: string;
  title: string;
  subject: string;
  lesson_id?: number;
  path?: string;
  saved_at: string;
}

interface StudyNoteApiItem {
  id: string;
  title: string;
  content: string;
  subject?: string | null;
  created_at: string;
  updated_at: string;
}

const isTemporaryId = (value: string) => value.startsWith('tmp-');

export function LibraryPage() {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [bookmarks, setBookmarks] = useState<BookmarkItem[]>([]);
  const [notes, setNotes] = useState<StudyNoteItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [isSavingNote, setIsSavingNote] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [requestKey, setRequestKey] = useState(0);

  const [search, setSearch] = useState('');
  const [showAddNote, setShowAddNote] = useState(false);
  const [newNoteTitle, setNewNoteTitle] = useState('');
  const [newNoteContent, setNewNoteContent] = useState('');
  const [newNoteSubject, setNewNoteSubject] = useState('');

  useEffect(() => {
    let active = true;

    async function loadLibrary() {
      setIsLoading(true);
      setLoadError(null);
      try {
        const [bookmarksRes, notesRes] = await Promise.all([
          apiClient.get<{ bookmarks?: BookmarkApiItem[] }>('/api/library/bookmarks'),
          apiClient.get<{ notes?: StudyNoteApiItem[] }>('/api/library/notes'),
        ]);

        if (!active) return;

        const bookmarksData = bookmarksRes.data?.bookmarks ?? [];
        const notesData = notesRes.data?.notes ?? [];

        setBookmarks(
          bookmarksData.map((item) => ({
            id: item.id,
            title: item.title,
            subject: item.subject,
            lessonId: item.lesson_id,
            path: item.path,
            savedAt: item.saved_at,
          }))
        );

        setNotes(
          notesData.map((item) => ({
            id: item.id,
            title: item.title,
            content: item.content,
            subject: item.subject ?? undefined,
            createdAt: item.created_at,
            updatedAt: item.updated_at,
          }))
        );
        if (requestKey > 0) {
          addToast('Library refreshed successfully.', 'success');
        }
      } catch (error) {
        if (active) {
          const message = getApiErrorMessage(error, 'Unable to load library data.');
          setLoadError(message);
          addToast(message, 'error');
        }
      } finally {
        if (active) setIsLoading(false);
      }
    }

    void loadLibrary();
    return () => {
      active = false;
    };
  }, [addToast, requestKey]);

  // Filter by search
  const filteredBookmarks = bookmarks.filter(
    (b) =>
      b.title.toLowerCase().includes(search.toLowerCase()) ||
      b.subject.toLowerCase().includes(search.toLowerCase())
  );

  const filteredNotes = notes.filter(
    (n) =>
      n.title.toLowerCase().includes(search.toLowerCase()) ||
      n.content.toLowerCase().includes(search.toLowerCase()) ||
      (n.subject || '').toLowerCase().includes(search.toLowerCase())
  );

  async function handleAddNote() {
    if (!newNoteTitle.trim()) return;

    const normalizedSubject = newNoteSubject.trim().toLowerCase();
    const validSubject = ['physics', 'chemistry', 'biology'].includes(normalizedSubject)
      ? normalizedSubject
      : undefined;

    setOperationError(null);
    setIsSavingNote(true);
    const nowIso = new Date().toISOString();
    const temporaryId = `tmp-${Date.now()}`;
    const optimisticNote: StudyNoteItem = {
      id: temporaryId,
      title: newNoteTitle.trim(),
      content: newNoteContent.trim() || '-',
      subject: validSubject,
      createdAt: nowIso,
      updatedAt: nowIso,
    };

    setNotes((prev) => [optimisticNote, ...prev]);
    try {
      const response = await apiClient.post('/api/library/notes', {
        title: newNoteTitle.trim(),
        content: newNoteContent.trim() || '-',
        subject: validSubject,
      });

      const note = response.data;
      if (note?.id) {
        setNotes((prev) =>
          prev.map((item) =>
            item.id === temporaryId
              ? {
                id: note.id,
                title: note.title,
                content: note.content,
                subject: note.subject ?? undefined,
                createdAt: note.created_at,
                updatedAt: note.updated_at,
              }
              : item
          )
        );
      } else {
        setNotes((prev) => prev.filter((item) => item.id !== temporaryId));
      }

      setNewNoteTitle('');
      setNewNoteContent('');
      setNewNoteSubject('');
      setShowAddNote(false);
      addToast('Note saved successfully.', 'success');
    } catch (error) {
      setNotes((prev) => prev.filter((item) => item.id !== temporaryId));
      const message = getApiErrorMessage(error, 'Unable to save note. Please try again.');
      setOperationError(message);
      addToast(message, 'error');
    } finally {
      setIsSavingNote(false);
    }
  }

  async function handleRemoveBookmark(id: string) {
    setOperationError(null);
    setPendingDeleteId(id);
    const bookmarkToRestore = bookmarks.find((item) => item.id === id);
    setBookmarks((prev) => prev.filter((item) => item.id !== id));
    try {
      await apiClient.delete(`/api/library/bookmarks/${id}`);
      addToast('Bookmark removed successfully.', 'success');
    } catch (error) {
      if (bookmarkToRestore) {
        setBookmarks((prev) => [bookmarkToRestore, ...prev]);
      }
      const message = getApiErrorMessage(error, 'Unable to remove bookmark.');
      setOperationError(message);
      addToast(message, 'error');
    } finally {
      setPendingDeleteId(null);
    }
  }

  async function handleRemoveNote(id: string) {
    setOperationError(null);
    setPendingDeleteId(id);
    const noteToRestore = notes.find((item) => item.id === id);
    setNotes((prev) => prev.filter((item) => item.id !== id));

    if (isTemporaryId(id)) {
      setPendingDeleteId(null);
      return;
    }

    try {
      await apiClient.delete(`/api/library/notes/${id}`);
      addToast('Note deleted successfully.', 'success');
    } catch (error) {
      if (noteToRestore) {
        setNotes((prev) => [noteToRestore, ...prev]);
      }
      const message = getApiErrorMessage(error, 'Unable to delete note.');
      setOperationError(message);
      addToast(message, 'error');
    } finally {
      setPendingDeleteId(null);
    }
  }

  const subjectColors: Record<string, 'success' | 'primary' | 'warning'> = {
    biology: 'success',
    chemistry: 'primary',
    physics: 'warning',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-4xl mx-auto space-y-5"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2" style={{ fontFamily: 'var(--font-heading)', fontSize: 20, fontWeight: 600, color: 'var(--text-primary)' }}>
            <Library className="w-6 h-6 text-primary" />
            My Library
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            {bookmarks.length} bookmarks · {notes.length} notes
          </p>
        </div>
        <Button
          color="secondary"
          variant="flat"
          startContent={<Plus className="w-4 h-4" />}
          onPress={() => setShowAddNote(true)}
          size="sm"
        >
          New Note
        </Button>
      </div>

      {/* Search */}
      <Input
        aria-label="Search bookmarks and notes"
        placeholder="Search bookmarks & notes..."
        value={search}
        onValueChange={setSearch}
        startContent={<Search className="w-4 h-4 text-default-400" />}
        variant="bordered"
        size="sm"
        isClearable
        onClear={() => setSearch('')}
        classNames={{
          inputWrapper: 'bg-bg-3 border-border-default rounded-[var(--r-md)]',
          input: 'text-text-primary text-[13px]',
        }}
      />

      {(loadError || operationError) && (
        <Card className="glass" style={{ borderRadius: 'var(--r-md)' }}>
          <CardBody className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3" style={{ padding: 14 }}>
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>{operationError ?? loadError}</p>
            {loadError && (
              <Button
                size="sm"
                variant="flat"
                color="secondary"
                isLoading={isLoading}
                onPress={() => setRequestKey((value) => value + 1)}
              >
                Retry
              </Button>
            )}
          </CardBody>
        </Card>
      )}

      {/* Tabs */}
      <Tabs variant="underlined" color="secondary" aria-label="Library sections" classNames={{ tabList: 'border-b border-border-subtle mb-5', tab: 'text-[13px]' }}>
        {/* Bookmarks Tab */}
        <Tab
          key="bookmarks"
          title={
            <span className="flex items-center gap-1.5">
              <BookMarked className="w-4 h-4" />
              Bookmarks ({filteredBookmarks.length})
            </span>
          }
        >
          <div className="space-y-3 mt-3">
            {isLoading ? (
              <Card className="glass">
                <CardBody className="text-center" style={{ padding: '40px 20px' }}>
                  <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Loading bookmarks...</p>
                </CardBody>
              </Card>
            ) : filteredBookmarks.length === 0 ? (
              <Card className="glass">
                <CardBody className="text-center" style={{ padding: '56px 20px' }}>
                  <BookMarked className="w-10 h-10 text-text-faint mx-auto mb-3" />
                  <p style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>No bookmarks yet</p>
                  <p className="mt-1" style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                    Bookmark lessons from subject pages to save them here
                  </p>
                </CardBody>
              </Card>
            ) : (
              <AnimatePresence>
                {filteredBookmarks.map((bm) => (
                  <motion.div
                    key={bm.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }}
                  >
                    <Card className="glass" style={{ padding: '14px 16px' }}>
                      <CardBody className="flex flex-row items-center gap-3 py-3 px-4">
                        <BookOpen className="w-5 h-5 text-secondary shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate text-text-primary">{bm.title}</p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <Chip
                              size="sm"
                              variant="flat"
                              color={subjectColors[bm.subject] || 'default'}
                              className="text-[10px]"
                            >
                              {bm.subject}
                            </Chip>
                            <span className="text-[11px] text-default-400">
                              <Clock className="w-3 h-3 inline mr-0.5" />
                              {new Date(bm.savedAt).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                        <div className="flex gap-1">
                          {bm.path && (
                            <Tooltip content="Go to lesson">
                              <Button
                                isIconOnly
                                aria-label="Go to lesson"
                                variant="light"
                                size="sm"
                                onPress={() => navigate(bm.path!)}
                              >
                                <ExternalLink className="w-4 h-4" />
                              </Button>
                            </Tooltip>
                          )}
                          <Tooltip content="Remove bookmark">
                            <Button
                              isIconOnly
                              aria-label="Remove bookmark"
                              variant="light"
                              color="danger"
                              size="sm"
                              isLoading={pendingDeleteId === bm.id}
                              onPress={() => void handleRemoveBookmark(bm.id)}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </Tooltip>
                        </div>
                      </CardBody>
                    </Card>
                  </motion.div>
                ))}
              </AnimatePresence>
            )}
          </div>
        </Tab>

        {/* Notes Tab */}
        <Tab
          key="notes"
          title={
            <span className="flex items-center gap-1.5">
              <StickyNote className="w-4 h-4" />
              Notes ({filteredNotes.length})
            </span>
          }
        >
          <div className="space-y-3 mt-3">
            {/* Add note form */}
            <AnimatePresence>
              {showAddNote && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <Card className="glass border-secondary/30">
                    <CardHeader className="text-sm font-semibold pb-0" style={{ color: 'var(--text-primary)' }}>New Note</CardHeader>
                    <CardBody className="space-y-3 pt-2">
                      <Input
                        aria-label="Note title"
                        placeholder="Title"
                        value={newNoteTitle}
                        onValueChange={setNewNoteTitle}
                        variant="bordered"
                        size="sm"
                      />
                      <Input
                        aria-label="Note subject"
                        placeholder="Subject (optional)"
                        value={newNoteSubject}
                        onValueChange={setNewNoteSubject}
                        variant="bordered"
                        size="sm"
                      />
                      <Textarea
                        aria-label="Note content"
                        placeholder="Write your study notes..."
                        value={newNoteContent}
                        onValueChange={setNewNoteContent}
                        variant="bordered"
                        minRows={3}
                      />
                      <div className="flex gap-2 justify-end">
                        <Button
                          variant="flat"
                          size="sm"
                          onPress={() => setShowAddNote(false)}
                        >
                          Cancel
                        </Button>
                        <Button
                          color="secondary"
                          size="sm"
                          isLoading={isSavingNote}
                          onPress={() => void handleAddNote()}
                          isDisabled={!newNoteTitle.trim()}
                        >
                          Save Note
                        </Button>
                      </div>
                    </CardBody>
                  </Card>
                </motion.div>
              )}
            </AnimatePresence>

            {isLoading ? (
              <Card className="glass">
                <CardBody className="text-center" style={{ padding: '40px 20px' }}>
                  <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Loading notes...</p>
                </CardBody>
              </Card>
            ) : filteredNotes.length === 0 && !showAddNote ? (
              <Card className="glass">
                <CardBody className="text-center" style={{ padding: '56px 20px' }}>
                  <StickyNote className="w-10 h-10 text-text-faint mx-auto mb-3" />
                  <p style={{ fontFamily: 'var(--font-heading)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>No notes yet</p>
                  <p className="mt-1" style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                    Create study notes to keep track of key concepts
                  </p>
                  <Button
                    color="secondary"
                    variant="flat"
                    size="sm"
                    className="mt-3"
                    startContent={<Plus className="w-4 h-4" />}
                    onPress={() => setShowAddNote(true)}
                  >
                    Create your first note
                  </Button>
                </CardBody>
              </Card>
            ) : (
              <AnimatePresence>
                {filteredNotes.map((note) => (
                  <motion.div
                    key={note.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }}
                  >
                    <Card className="glass" style={{ padding: '14px 16px' }}>
                      <CardBody className="py-3 px-4">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <p className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>{note.title}</p>
                            <div className="flex items-center gap-2 mt-1">
                              {note.subject && (
                                <Chip
                                  size="sm"
                                  variant="flat"
                                  color={subjectColors[note.subject] || 'default'}
                                  className="text-[10px]"
                                >
                                  {note.subject}
                                </Chip>
                              )}
                              <span className="text-[11px] text-default-400">
                                {new Date(note.updatedAt).toLocaleDateString()}
                              </span>
                            </div>
                          </div>
                          <Tooltip content="Delete note">
                            <Button
                              isIconOnly
                              aria-label="Delete note"
                              variant="light"
                              color="danger"
                              size="sm"
                              isLoading={pendingDeleteId === note.id}
                              onPress={() => void handleRemoveNote(note.id)}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </Tooltip>
                        </div>
                        {note.content && (
                          <>
                            <Divider className="my-2" />
                            <p className="text-sm whitespace-pre-wrap leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                              {note.content}
                            </p>
                          </>
                        )}
                      </CardBody>
                    </Card>
                  </motion.div>
                ))}
              </AnimatePresence>
            )}
          </div>
        </Tab>
      </Tabs>
    </motion.div>
  );
}
