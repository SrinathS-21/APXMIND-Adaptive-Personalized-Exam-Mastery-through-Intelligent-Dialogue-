import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ── Types ──
export interface Bookmark {
  id: string;
  title: string;
  subject: string;
  lessonId?: number;
  path?: string;
  savedAt: string;
}

export interface StudyNote {
  id: string;
  title: string;
  content: string;
  subject?: string;
  createdAt: string;
  updatedAt: string;
}

interface LibraryState {
  bookmarks: Bookmark[];
  notes: StudyNote[];
  _hasHydrated: boolean;
  setHasHydrated: (v: boolean) => void;
  addBookmark: (bm: Omit<Bookmark, 'id' | 'savedAt'>) => void;
  removeBookmark: (id: string) => void;
  isBookmarked: (title: string, subject: string) => boolean;
  addNote: (note: Omit<StudyNote, 'id' | 'createdAt' | 'updatedAt'>) => void;
  removeNote: (id: string) => void;
  updateNote: (id: string, updates: Partial<Pick<StudyNote, 'title' | 'content' | 'subject'>>) => void;
}

// ── Store ──
export const useLibraryStore = create<LibraryState>()(
  persist(
    (set, get) => ({
      bookmarks: [],
      notes: [],
      _hasHydrated: false,
      setHasHydrated: (v) => set({ _hasHydrated: v }),

      addBookmark: (bm) =>
        set((s) => ({
          bookmarks: [
            { ...bm, id: crypto.randomUUID(), savedAt: new Date().toISOString() },
            ...s.bookmarks,
          ],
        })),

      removeBookmark: (id) =>
        set((s) => ({ bookmarks: s.bookmarks.filter((b) => b.id !== id) })),

      isBookmarked: (title, subject) =>
        get().bookmarks.some((b) => b.title === title && b.subject === subject),

      addNote: (note) => {
        const now = new Date().toISOString();
        set((s) => ({
          notes: [
            { ...note, id: crypto.randomUUID(), createdAt: now, updatedAt: now },
            ...s.notes,
          ],
        }));
      },

      removeNote: (id) =>
        set((s) => ({ notes: s.notes.filter((n) => n.id !== id) })),

      updateNote: (id, updates) =>
        set((s) => ({
          notes: s.notes.map((n) =>
            n.id === id
              ? { ...n, ...updates, updatedAt: new Date().toISOString() }
              : n
          ),
        })),
    }),
    { name: 'APXMIND-library', onRehydrateStorage: () => (state) => { state?.setHasHydrated(true); } }
  )
);
