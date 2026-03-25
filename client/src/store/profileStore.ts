import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface UserProfile {
  name: string;
  dateOfBirth: string | null;          // ISO date string  YYYY-MM-DD
  currentClass: string | null;
  attemptNumber: number | null;        // 1, 2, 3+
  targetYear: number | null;           // e.g., 2026
  targetScore: number | null;          // out of 720
  strongSubjects: string[];     // ['physics', 'chemistry', 'biology']
  weakSubjects: string[];
  dailyStudyTarget: number | null;     // hours per day
  preferredLanguage: string | null;
}

export interface ApiUserProfile {
  name: string;
  dob?: string | null;
  current_class?: string | null;
  attempt_number?: number | null;
  target_year?: string | null;
  target_score?: number | null;
  strong_subjects?: string[] | null;
  weak_subjects?: string[] | null;
  daily_study_target?: number | null;
  preferred_language?: string | null;
}

export function normalizeApiUserProfile(user: ApiUserProfile): UserProfile {
  const nowYear = new Date().getFullYear() + 1;
  return {
    name: user.name,
    dateOfBirth: user.dob ?? null,
    currentClass: user.current_class ?? '12th',
    attemptNumber: user.attempt_number ?? 1,
    targetYear: user.target_year ? Number(user.target_year) : nowYear,
    targetScore: user.target_score ?? 650,
    strongSubjects: user.strong_subjects ?? [],
    weakSubjects: user.weak_subjects ?? [],
    dailyStudyTarget: user.daily_study_target ?? 4,
    preferredLanguage: user.preferred_language ?? 'english',
  };
}

interface ProfileState {
  profile: UserProfile | null;
  isSetupComplete: boolean;
  isAuthenticated: boolean;
  _hasHydrated: boolean;
  setProfile: (profile: UserProfile) => void;
  updateProfile: (updates: Partial<UserProfile>) => void;
  clearProfile: () => void;
  setHasHydrated: (v: boolean) => void;
  setAuthenticated: (v: boolean) => void;
}

export const useProfileStore = create<ProfileState>()(
  persist(
    (set) => ({
      profile: null,
      isSetupComplete: false,
      isAuthenticated: false,
      _hasHydrated: false,
      setProfile: (profile) => set({ profile, isSetupComplete: true, isAuthenticated: true }),
      updateProfile: (updates) =>
        set((state) => ({
          profile: state.profile ? { ...state.profile, ...updates } : null,
        })),
      clearProfile: () => {
        set({ profile: null, isSetupComplete: false, isAuthenticated: false });
        localStorage.removeItem('APXMIND_token');
      },
      setHasHydrated: (v) => set({ _hasHydrated: v }),
      setAuthenticated: (v) => set({ isAuthenticated: v }),
    }),
    {
      name: 'APXMIND-profile',
      partialize: (state) => ({
        profile: state.profile,
        // we persist profile, but authentication requires login each session
        isSetupComplete: state.isSetupComplete,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
