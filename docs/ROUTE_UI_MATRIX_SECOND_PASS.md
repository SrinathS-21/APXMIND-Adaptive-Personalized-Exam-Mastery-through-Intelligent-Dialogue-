# APXMIND Route-to-UI Rationalization Matrix (Second Pass)

Date: 2026-03-29

## Scope
- Endpoint-by-endpoint mapping for backend domains.
- UI entrypoint tracked to current frontend services/pages.
- Auth requirement and current status included for each endpoint.

## Status Legend
- Connected: UI has an active call path.
- Partial: Domain is wired, but endpoint is not used in current UI flow.
- Backend-only: Endpoint exists and is mounted, but no current frontend call path.
- Disabled: Router file exists, but router is not mounted in app.
- Removed: Domain is intentionally absent from mounted runtime API; requests return 404.

## Auth Legend
- Public: No JWT required.
- User JWT: `get_current_user` required.

## Matrix

### System

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| GET /health | none (helper exists in `client/src/lib/api.ts`) | Public | Backend-only |
| GET /api | none | Public | Backend-only |

### Auth

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| POST /api/auth/register | `client/src/pages/ProfileSetup.tsx` | Public | Connected |
| POST /api/auth/login | `client/src/pages/WelcomeScreen.tsx` | Public | Connected |
| GET /api/auth/me | none | User JWT | Backend-only |
| PUT /api/auth/profile | `client/src/pages/ProfilePage.tsx` | User JWT | Connected |
| GET /api/auth/users | `client/src/pages/WelcomeScreen.tsx` | Public | Connected |
| POST /api/auth/profile | none | Public | Backend-only |

### Subjects

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| GET /api/subjects | none (`getAllSubjects` exported but not used) | Public | Backend-only |
| GET /api/subjects/{subject}/lessons | `client/src/pages/SubjectPage.tsx` via `client/src/lib/subjectService.ts` | Public | Connected |
| POST /api/subjects/{subject}/lessons/{lesson_id}/complete | `client/src/lib/subjectService.ts` used by `client/src/pages/LearnPage.tsx` | User JWT | Connected |

### Books

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| GET /api/books/{file_path} | `client/src/pages/BookReaderPage.tsx` | Public | Connected |

### Query (AI)

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| POST /api/query | `client/src/pages/LearnPage.tsx` fallback via `client/src/lib/queryService.ts` | Public | Partial |

### Trainer (legacy quiz API)

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| POST /api/trainer/generate-quiz | none (legacy `client/src/lib/trainerService.ts` retained but not used by active pages) | Public | Backend-only |
| POST /api/trainer/submit-answer | none (legacy `client/src/lib/trainerService.ts` retained but not used by active pages) | Public | Backend-only |

### Dashboard and Progress

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| GET /api/dashboard/summary | `client/src/pages/DashboardPage.tsx` | User JWT | Connected |
| GET /api/progress/daily | `client/src/lib/progressService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |
| GET /api/progress/gamification | `client/src/pages/AchievementsPage.tsx` | User JWT | Connected |
| POST /api/progress/study-minutes | `client/src/lib/progressService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |

### Quiz v2 (stateful quiz)

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| POST /api/quiz | `client/src/lib/quizService.ts` used by `client/src/pages/QuizPage.tsx` | User JWT | Connected |
| GET /api/quiz | `client/src/lib/quizService.ts` used by `client/src/pages/QuizPage.tsx` (filtered/paginated recent attempts list) | User JWT | Connected |
| GET /api/quiz/{quiz_id} | `client/src/lib/quizService.ts` used by `client/src/pages/QuizPage.tsx` (selected attempt metadata) | User JWT | Connected |
| GET /api/quiz/{quiz_id}/questions | `client/src/lib/quizService.ts` used by `client/src/pages/QuizPage.tsx` (question set preview) | User JWT | Connected |
| POST /api/quiz/{quiz_id}/answers | `client/src/lib/quizService.ts` used by `client/src/pages/QuizPage.tsx` | User JWT | Connected |
| PUT /api/quiz/{quiz_id}/answers/{question_id} | `client/src/lib/quizService.ts` used by `client/src/pages/QuizPage.tsx` (answer change before finish) | User JWT | Connected |
| POST /api/quiz/{quiz_id}/finish | `client/src/lib/quizService.ts` used by `client/src/pages/QuizPage.tsx` | User JWT | Connected |
| PATCH /api/quiz/{quiz_id}/abandon | `client/src/lib/quizService.ts` used by `client/src/pages/QuizPage.tsx` (active quiz abandon action) | User JWT | Connected |
| GET /api/quiz/{quiz_id}/results | `client/src/lib/quizService.ts` used by `client/src/pages/QuizPage.tsx` (attempt review panel) | User JWT | Connected |
| DELETE /api/quiz/{quiz_id} | `client/src/lib/quizService.ts` used by `client/src/pages/QuizPage.tsx` (attempt delete action) | User JWT | Connected |

### Learn sessions

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| POST /api/learn/sessions | `client/src/pages/LearnPage.tsx` via `client/src/lib/learnSessionService.ts` | User JWT | Connected |
| GET /api/learn/sessions | `client/src/lib/learnSessionService.ts` used by `client/src/pages/LearnPage.tsx` + `client/src/pages/LearnSessionsPage.tsx` (filtered/paginated session list) | User JWT | Connected |
| GET /api/learn/sessions/{session_id} | `client/src/lib/learnSessionService.ts` used by `client/src/pages/LearnPage.tsx` (selected session metadata) | User JWT | Connected |
| PATCH /api/learn/sessions/{session_id}/end | `client/src/pages/LearnPage.tsx` via `client/src/lib/learnSessionService.ts` | User JWT | Connected |
| DELETE /api/learn/sessions/{session_id} | `client/src/lib/learnSessionService.ts` used by `client/src/pages/LearnPage.tsx` + `client/src/pages/LearnSessionsPage.tsx` | User JWT | Connected |
| POST /api/learn/sessions/{session_id}/messages | `client/src/pages/LearnPage.tsx` via `client/src/lib/learnSessionService.ts` | User JWT | Connected |
| GET /api/learn/sessions/{session_id}/messages | `client/src/lib/learnSessionService.ts` used by `client/src/pages/LearnPage.tsx` + `client/src/pages/LearnSessionsPage.tsx` (transcript preview) | User JWT | Connected |
| DELETE /api/learn/sessions/{session_id}/messages/{msg_id} | `client/src/lib/learnSessionService.ts` used by `client/src/pages/LearnPage.tsx` + `client/src/pages/LearnSessionsPage.tsx` | User JWT | Connected |
| DELETE /api/learn/sessions/{session_id}/messages | `client/src/lib/learnSessionService.ts` used by `client/src/pages/LearnPage.tsx` + `client/src/pages/LearnSessionsPage.tsx` | User JWT | Connected |

### Library

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| GET /api/library/bookmarks | `client/src/pages/LibraryPage.tsx` | User JWT | Connected |
| GET /api/library/bookmarks/{bookmark_id} | none | User JWT | Backend-only |
| POST /api/library/bookmarks | none | User JWT | Backend-only |
| PATCH /api/library/bookmarks/{bookmark_id} | none | User JWT | Backend-only |
| DELETE /api/library/bookmarks/{bookmark_id} | `client/src/pages/LibraryPage.tsx` | User JWT | Connected |
| DELETE /api/library/bookmarks | none | User JWT | Backend-only |
| GET /api/library/notes | `client/src/pages/LibraryPage.tsx` | User JWT | Connected |
| GET /api/library/notes/{note_id} | none | User JWT | Backend-only |
| POST /api/library/notes | `client/src/pages/LibraryPage.tsx` | User JWT | Connected |
| PUT /api/library/notes/{note_id} | none | User JWT | Backend-only |
| DELETE /api/library/notes/{note_id} | `client/src/pages/LibraryPage.tsx` | User JWT | Connected |
| DELETE /api/library/notes | none | User JWT | Backend-only |

### Achievements

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| GET /api/achievements | `client/src/pages/AchievementsPage.tsx` | User JWT | Connected |
| GET /api/achievements/earned | none | User JWT | Backend-only |
| GET /api/achievements/{badge_id} | none | User JWT | Backend-only |

### Profile preferences

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| GET /api/profile/subjects | none | User JWT | Backend-only |
| PUT /api/profile/subjects/{subject} | none | User JWT | Backend-only |
| DELETE /api/profile/subjects/{subject} | none | User JWT | Backend-only |

### Recommendations

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| GET /api/recommendations | `client/src/lib/recommendationsService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |
| PATCH /api/recommendations/{rec_id} | `client/src/lib/recommendationsService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |
| DELETE /api/recommendations/{rec_id} | `client/src/lib/recommendationsService.ts` used by `client/src/pages/StudyPlanPage.tsx` (recommendation delete action) | User JWT | Connected |

### Insights

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| GET /api/insights/mastery | `client/src/lib/plannerInsightsService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |
| GET /api/insights/mastery/{subject} | none | User JWT | Backend-only |
| GET /api/insights/risk-topics | `client/src/lib/plannerInsightsService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |
| GET /api/insights/calibration | `client/src/lib/plannerInsightsService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |
| GET /api/insights/weekly-report | `client/src/lib/plannerInsightsService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |
| GET /api/insights/readiness | `client/src/lib/plannerInsightsService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |
| GET /api/insights/habits | `client/src/lib/plannerInsightsService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |

### Notifications

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| GET /api/notifications | `client/src/lib/accountService.ts` used by `client/src/pages/NotificationsPage.tsx` | User JWT | Connected |
| GET /api/notifications/unread-count | `client/src/lib/accountService.ts` used by `client/src/pages/NotificationsPage.tsx` | User JWT | Connected |
| PATCH /api/notifications/{notification_id}/read | `client/src/lib/accountService.ts` used by `client/src/pages/NotificationsPage.tsx` | User JWT | Connected |
| POST /api/notifications/read-all | `client/src/lib/accountService.ts` used by `client/src/pages/NotificationsPage.tsx` | User JWT | Connected |
| DELETE /api/notifications/{notification_id} | `client/src/lib/accountService.ts` used by `client/src/pages/NotificationsPage.tsx` | User JWT | Connected |
| GET /api/notifications/preferences | `client/src/lib/accountService.ts` used by `client/src/pages/NotificationsPage.tsx` | User JWT | Connected |
| PUT /api/notifications/preferences | `client/src/lib/accountService.ts` used by `client/src/pages/NotificationsPage.tsx` | User JWT | Connected |
| POST /api/notifications/push-tokens | none | User JWT | Backend-only |
| DELETE /api/notifications/push-tokens/{token_id} | none | User JWT | Backend-only |

### Admin (Deprecated)

Admin frontend and router wiring are removed for the student-focused open-source release.
Admin ORM models are also removed from active runtime mapping.

### Support and Reports

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| GET /api/support/tickets | `client/src/lib/supportService.ts` used by `client/src/pages/SupportPage.tsx` | User JWT | Connected |
| POST /api/support/tickets | `client/src/lib/supportService.ts` used by `client/src/pages/SupportPage.tsx` | User JWT | Connected |
| GET /api/support/tickets/{ticket_id} | `client/src/lib/supportService.ts` used by `client/src/pages/SupportPage.tsx` | User JWT | Connected |
| POST /api/support/tickets/{ticket_id}/reply | `client/src/lib/supportService.ts` used by `client/src/pages/SupportPage.tsx` | User JWT | Connected |
| POST /api/support/reports | `client/src/lib/supportService.ts` used by `client/src/pages/SupportPage.tsx` (content report submission) | User JWT | Connected |
| POST /api/reports | `client/src/lib/supportService.ts` used by `client/src/pages/SupportPage.tsx` | User JWT | Connected |

### Retrieval and Error Notebook

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| POST /api/retrieval/lesson-recall | `client/src/lib/retrievalService.ts` used by `client/src/pages/LearnPage.tsx` | User JWT | Connected |
| GET /api/retrieval/spaced-queue | `client/src/lib/retrievalService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |
| POST /api/retrieval/spaced-queue/{review_id}/complete | `client/src/lib/retrievalService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |
| GET /api/errors/mistake-cards | `client/src/lib/errorNotebookService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |
| PATCH /api/errors/mistake-cards/{card_id} | `client/src/lib/errorNotebookService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |

### Planner

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| POST /api/planner/generate | `client/src/lib/plannerInsightsService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |
| POST /api/planner/strategist | `client/src/lib/plannerInsightsService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |
| GET /api/planner/daily | `client/src/lib/plannerInsightsService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |
| PATCH /api/planner/tasks/{task_id} | `client/src/lib/plannerInsightsService.ts` used by `client/src/pages/StudyPlanPage.tsx` | User JWT | Connected |

### Realtime transports

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| GET /api/events/stream (SSE) | none | User JWT | Backend-only |
| WS /ws/chat | none | Public | Backend-only |

### Disabled or Removed domains

#### Payments

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| GET /api/payments/plans | none (subscription page removed) | User JWT | Removed |
| GET /api/payments/subscriptions/current | none | User JWT | Removed |
| POST /api/payments/checkout | none | User JWT | Removed |
| POST /api/payments/verify | none | User JWT | Removed |
| POST /api/payments/subscriptions/{subscription_id}/cancel | none | User JWT | Removed |
| GET /api/payments/payments | none | User JWT | Removed |
| GET /api/payments/invoices | none | User JWT | Removed |
| POST /api/payments/promo/validate | none | User JWT | Removed |
| GET /api/payments/wallet | none | User JWT | Removed |
| GET /api/payments/wallet/transactions | none | User JWT | Removed |

#### Security

| Backend endpoint | UI entrypoint | Auth | Current status |
|---|---|---|---|
| POST /api/security/password-reset/request | none (security page removed) | Public | Disabled |
| POST /api/security/password-reset/confirm | none | Public | Disabled |
| GET /api/security/sessions | none | User JWT | Disabled |
| POST /api/security/sessions/{session_id}/revoke | none | User JWT | Disabled |
| POST /api/security/sessions/revoke-others | none | User JWT | Disabled |
| GET /api/security/login-history | none | User JWT | Disabled |
| GET /api/security/events | none | User JWT | Disabled |

## Rationalization Priorities (Low-Impact, Next Pass)

1. Keep disabled domains disabled until product scope explicitly reintroduces subscription/security UX.
2. Decide whether to deprecate legacy `/api/trainer` endpoints now that active quiz UX is fully on `/api/quiz` (start + history + result review).
3. Decide whether to expose backend-only endpoints in other domains that remain intentionally out of current student UX scope.
4. Add SSE/WebSocket client only if real-time UX is required; otherwise document as reserved interfaces.
5. Add cleanup/deprecation notes for endpoints intentionally backend-only so their state is explicit in release docs.