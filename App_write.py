file_path = 'client/src/App.tsx'

content = '''import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useProfileStore } from './store/profileStore';
import { AppShell } from './components/AppShell';
import { WelcomeScreen } from './pages/WelcomeScreen';
import { ProfileSetup } from './pages/ProfileSetup';
import { DashboardPage } from './pages/DashboardPage';
import { SubjectPage } from './pages/SubjectPage';
import { LearnPage } from './pages/LearnPage';
import { QuizPage } from './pages/QuizPage';
import { AchievementsPage } from './pages/AchievementsPage';
import { BooksPage } from './pages/BooksPage';
import { BookReaderPage } from './pages/BookReaderPage';
import { ResourcesPage } from './pages/ResourcesPage';
import { StudyPlanPage } from './pages/StudyPlanPage';
import { ProfilePage } from './pages/ProfilePage';
import { LibraryPage } from './pages/LibraryPage';

/** Show a minimal loading state while Zustand rehydrates from localStorage */
function HydrationGate({ children }: { children: React.ReactNode }) {
  const hasHydrated = useProfileStore((s) => s._hasHydrated);
  if (!hasHydrated) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-secondary border-t-transparent rounded-full animate-spin" />
          <p className="text-default-500 text-sm">Loading...</p>
        </div>
      </div>
    );
  }
  return <>{children}</>;
}

/** Guard: redirect to /login if not authenticated or not setup */
function RequireAuth({ children }: { children: React.ReactNode }) {
  const isSetupComplete = useProfileStore((s) => s.isSetupComplete);
  const isAuthenticated = useProfileStore((s) => s.isAuthenticated);
  
  if (!isSetupComplete || !isAuthenticated) return <Navigate to="/login" replace />;
  
  return <>{children}</>;
}

/** Guard: redirect to /dashboard if already authenticated */
function RedirectIfAuth({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useProfileStore((s) => s.isAuthenticated);
  const isSetupComplete = useProfileStore((s) => s.isSetupComplete);

  if (isAuthenticated && isSetupComplete) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

function App() {
  return (
    <HydrationGate>
      <Router>
        <Routes>
        
        {/* Welcome / Login screen */}
        <Route
          path="/login"
          element={
            <RedirectIfAuth>
              <WelcomeScreen />
            </RedirectIfAuth>
          }
        />

        {/* Profile setup — shown only on first launch or if they select Create New */}
        <Route
          path="/setup"
          element={
            <RedirectIfAuth>
              <ProfileSetup />
            </RedirectIfAuth>
          }
        />

        {/* All app pages inside the AppShell (sidebar + navbar) */}
        <Route
          element={
            <RequireAuth>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/subject/:subject" element={<SubjectPage />} />
          <Route path="/subject/:subject/lesson/:lessonId/learn" element={<LearnPage />} />
          <Route path="/subject/:subject/lesson/:lessonId/quiz" element={<QuizPage />} />
          <Route path="/subject/:subject/quiz" element={<QuizPage />} />
          <Route path="/achievements" element={<AchievementsPage />} />
          <Route path="/books" element={<BooksPage />} />
          <Route path="/books/reader" element={<BookReaderPage />} />
          <Route path="/resources" element={<ResourcesPage />} />
          <Route path="/study-plan" element={<StudyPlanPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/library" element={<LibraryPage />} />
        </Route>

        {/* Default redirect */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Router>
    </HydrationGate>
  );
}

export default App;
'''

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Rewrote App.tsx")
