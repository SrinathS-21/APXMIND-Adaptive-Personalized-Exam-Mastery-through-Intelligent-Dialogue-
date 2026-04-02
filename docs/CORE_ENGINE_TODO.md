# APXMIND: Core Learning Engine - Master Implementation Plan (Single Source of Truth)

## Memory Snapshot (Do Not Forget)
This section captures all critical context so we do not lose details between sessions.

- Scope: Student-first only. Admin models and legacy admin DB schema were removed and cleaned.
- Local DB: Primary local DB is APXMIND.db (confirm actual path via config).
- Data sources: data/raw contains NCERT books and question bank inputs; data/vectorstore is the embedded store.
- Models available locally: models/Llama-3.2-3B-Instruct-Q4_K_M.gguf and models/qwen2.5-3b-instruct-q4_k_m.gguf.
- Frontend: client/ (Vite + React). Backend: src/apxmind (FastAPI + SQLAlchemy).
- Core product metrics to surface daily: Daily Goal percent, Lessons Today, Quizzes Today, XP Today.
- The learning loop must be fully closed: plan -> learn -> quiz -> mastery -> next plan. No gaps.
- Phase 3 extensions must be gated behind a stable Phase 2 loop.

## Architecture Philosophy
**Zero Disconnected Branches.** Every feature implemented in this document follows a strict End-to-End (E2E) protocol. Nothing is built in isolation. A feature is only considered "Complete" when it spans across all layers interchangeably:
`Database (SQLAlchemy) -> Backend (FastAPI) -> AI Agent (Qwen/Llama) -> Frontend (React Dashboard) -> Verification`

Non-negotiables:
- Single source of truth is the database. UI is display-only for computed values.
- Each feature must have: schema, API, agent contract, UI, automated verification, manual verification.
- Each step must update the next step in the loop without manual stitching.

## Definitions and Metric Formulas (Use These Everywhere)
- Daily Plan Unit: One planned task in the day (lesson, quiz, review, mock, revision).
- Planned Units: Sum of all plan items for the day.
- Completed Units: Count of plan items completed with status=done.
- Daily Goal Percent: `floor((completed_units / planned_units) * 100)`.
  - If planned_units=0, show 0 percent and a "No plan yet" state.
- Lessons Today: Count of lesson_completed events for the local date.
- Quizzes Today: Count of quiz_completed events for the local date.
- XP Today: Sum of xp_delta for the local date.
- Mastery Score: Float 0.0 to 1.0. Updated by quiz performance and decays over time.

## End-to-End Event Flow (Source of Truth)
1. Strategist generates DailyPlan for date D and writes StudyPlan + DailyProgress(planned_units).
2. User starts lesson -> StudySession created.
3. Lesson completed -> LessonCompletion + XPEvent -> DailyProgress increments lessons_completed and completed_units.
4. Quiz started -> QuizAttempt created.
5. Quiz completed -> QuestionAttempt rows -> XPEvent -> TopicMastery updated.
6. DailyProgress aggregates: quizzes_completed, xp_earned, goal_percent.
7. Strategist reads TopicMastery + DailyProgress and generates plan for date D+1.

## Data Model Contract (Detailed)
All models below must be created in src/apxmind/db/models.py. Field names are the contract; verify actual User table name before finalizing.

1. DailyProgress
- id (PK)
- user_id (FK -> users.id; confirm actual User model)
- date (Date)
- planned_units (Integer)
- completed_units (Integer)
- lessons_completed (Integer)
- quizzes_completed (Integer)
- xp_earned (Integer)
- goal_percent (Integer, stored for fast reads)
- streak_days (Integer, optional)
- created_at, updated_at (DateTime)
- unique constraint: (user_id, date)

2. TopicMastery
- id (PK)
- user_id (FK)
- subject (String, e.g., Physics, Chemistry, Botany, Zoology)
- topic (String, e.g., Kinematics)
- subtopic (String, optional)
- mastery_score (Float 0-1)
- last_assessed_at (DateTime)
- correct_count, incorrect_count, attempts (Integer)
- confidence (Float 0-1, optional)
- decay_at (DateTime, optional)
- created_at, updated_at (DateTime)
- index: (user_id, subject, topic, subtopic)

3. StudySession
- id (PK)
- user_id (FK)
- mode (String: lesson|quiz|review|mock)
- topic_ref (String, optional)
- lesson_id (String, optional)
- quiz_id (String, optional)
- started_at, ended_at (DateTime)
- duration_sec (Integer)
- interruptions_count (Integer, optional)
- device (String, optional)

4. StudyPlan
- id (PK)
- user_id (FK)
- plan_date (Date)
- plan_json (JSON: ordered list of tasks)
- planned_units (Integer)
- created_at (DateTime)
- generated_by (String: strategist|manual)
- status (String: active|expired|replaced)

5. LessonCompletion
- id (PK)
- user_id (FK)
- lesson_id (String)
- topic_ref (String)
- started_at, completed_at (DateTime)
- duration_sec (Integer)
- comprehension_rating (Integer 1-5, optional)

6. QuizAttempt
- id (PK)
- user_id (FK)
- quiz_id (String)
- topic_ref (String)
- total_questions, correct_count (Integer)
- score_percent (Integer)
- started_at, completed_at (DateTime)
- duration_sec (Integer)

7. QuestionAttempt
- id (PK)
- quiz_attempt_id (FK)
- question_id (String)
- selected_option (String)
- is_correct (Boolean)
- time_spent_sec (Integer)

8. XPEvent
- id (PK)
- user_id (FK)
- source (String: lesson|quiz|streak|bonus|review)
- xp_delta (Integer)
- reason (String)
- created_at (DateTime)

Phase 3 (gated)
- SpacedRepetitionSchedule, BurnoutSignal, MockExamAttempt

## API Contract (Detailed)
All endpoints are authenticated using the existing auth dependency.

GET /api/v1/student/progress/today
- Response: {"date":"YYYY-MM-DD","lessons_completed":0,"quizzes_completed":0,"xp_today":0,"goal_percent":0,"planned_units":0,"completed_units":0}

GET /api/v1/student/plan/today
- Response: {"date":"YYYY-MM-DD","items":[{"type":"lesson","topic_ref":"Physics/Kinematics","estimated_min":30}],"planned_units":2}

POST /api/v1/student/session/start
- Body: {"mode":"lesson","topic_ref":"Physics/Kinematics","lesson_id":"L001"}
- Response: {"session_id":"...","started_at":"..."}

POST /api/v1/student/session/end
- Body: {"session_id":"...","ended_at":"...","duration_sec":1800}

POST /api/v1/student/lesson/complete
- Body: {"lesson_id":"L001","topic_ref":"Physics/Kinematics","duration_sec":1800,"comprehension_rating":4}

POST /api/v1/student/quiz/complete
- Body: {"quiz_id":"Q001","topic_ref":"Physics/Kinematics","total_questions":5,"correct_count":4,"duration_sec":600}

GET /api/v1/student/mastery
- Response: [{"subject":"Physics","topic":"Kinematics","mastery_score":0.62,"last_assessed_at":"..."}]

POST /api/v1/student/plan/regenerate
- Body: {"reason":"daily_refresh"}

POST /api/planner/strategist
- Body: {"date":"YYYY-MM-DD"}
- Response: Same as GenerateDailyPlanResponse (uses user daily study target)

## Frontend Contract (Detailed)
Core components (client/src):
- DailyGoalRing (percent display with 0, 25, 50, 75, 100 states)
- MetricsRow (Lessons Today, Quizzes Today, XP Today)
- StartMissionButton (fetches plan, navigates into lesson flow)
- TodayPlanList (renders ordered plan tasks)
- SessionTimer (tracks study time)

State rules:
- Loading: show skeletons, do not show 0 until API returns.
- Empty plan: show "No plan yet" CTA with regenerate button.
- Error: show retry and log error to console.

User flow:
Dashboard -> Start Mission -> Lesson UI -> Tutor -> Quiz -> Results -> Back to Dashboard (auto refresh).

## AI Agent Contract (Detailed)
Tutor Agent input (JSON): {"topic_ref":"Physics/Kinematics","context_chunks":[...],"student_level":"intermediate","time_budget_min":30}
Tutor output (JSON): {"summary":"...","key_points":[...],"check_questions":[...],"next_quiz_seed":"..."}

Quizzer Agent input (JSON): {"topic_ref":"Physics/Kinematics","difficulty":"medium","count":5}
Quizzer output (JSON): {"quiz_id":"...","questions":[{"question":"...","options":["A","B","C","D"],"correct_option":"B","explanation":"...","topic_ref":"Physics/Kinematics"}]}

Strategist Agent input (JSON): {"mastery_snapshot":[...],"progress_today":{...},"plan_history":[...]}
Strategist output (JSON): {"plan_date":"YYYY-MM-DD","items":[...],"planned_units":3}

Guardrails:
- All agent outputs must be valid JSON and schema-validated before persisting.
- If context is missing, the agent must request clarification instead of hallucinating.


---

## MILESTONE 1: The Tracking Foundation (Database Layer)
*Before the AI can adapt, it needs memory. We build the schemas to track XP, goal progress, and mastery.*

### 1.1 Implementation: Progress & Mastery Models
* **What we are doing:** Creating SQLAlchemy models in `models.py` to store `DailyProgress`, `TopicMastery` (per topic), and `StudySession` (time tracking).
* **Interconnected Subsystems:** Forms the base for the Student Dashboard UI and Strategist AI Agent.
* **Outcome:** The database can securely store a student's daily XP, quiz scores, and subject strengths.
* **Detailed Tasks:**
  - Define tables exactly as described in Data Model Contract.
  - Add indices and unique constraints to prevent duplicate daily rows.
  - Create seed script to insert a dummy DailyProgress row for testing.
* **Automated Verification:** 
  * Run `verify_models.py` to ensure schema integrity.
  * Run `pytest` on CRUD operations for the new models.
* **Manual Verification:** Use an SQLite viewer or DB browser to artificially insert a dummy row into `DailyProgress` and verify it persists without corrupting other user tables.
* **Acceptance Criteria:**
  - DailyProgress row can be created, updated, and queried by date.
  - TopicMastery row updates on quiz completion.
  - StudySession rows record durations without null end time.

---

## MILESTONE 2: Core Data Exchange (Backend APIs)
*Connecting the database to the outside world.*

### 2.1 Implementation: Progress Endpoints
* **What we are doing:** Building FastAPI routes (`GET /api/v1/student/progress/today`, `POST /api/v1/student/session/end`, etc.).
* **Interconnected Subsystems:** Connects the Database Layer to the Frontend React components.
* **Outcome:** The frontend has a secure, authenticated pipeline to fetch "Lessons Today, Quizzes Today, XP Today, 0% Goal" strings.
* **Detailed Tasks:**
  - Implement request validation (Pydantic) for all POST bodies.
  - Implement idempotency for lesson/quiz completion requests.
  - Add server-side aggregation for xp_today and goal_percent.
* **Automated Verification:** 
  * API Smoke Tests (`run_api_smoke.cmd`) to verify 200 OK responses and proper JSON formatting.
* **Manual Verification:** Execute standard `curl` commands or use Postman to fetch a user's daily progress and visually inspect the JSON payload.
* **Acceptance Criteria:**
  - Endpoints return correct values for the dummy test user.
  - Goal percent updates after lesson/quiz completion calls.

---

## MILESTONE 3: The Student Dashboard (Frontend UI)
*Making the metrics visible and interactive for the user.*

### 3.1 Implementation: Daily Goal & XP Widget
* **What we are doing:** Creating React components in the client workspace (`ProgressWidget`, `DailyGoalRing`, `XpCounter`).
* **Interconnected Subsystems:** Fetches data purely from Milestone 2 endpoints. Triggers Milestone 4 (Learning materials) when a user clicks "Start Today's Mission".
* **Outcome:** The user logs in and sees a beautiful, LiveKit-style premium UI displaying their real-time stats.
* **Detailed Tasks:**
  - Build API hooks for fetching today progress and plan.
  - Add empty and error states for "no plan" and failed API requests.
  - Connect Start Mission button to the lesson flow route.
* **Automated Verification:** 
  * React Testing Library tests to ensure components render without crashing given mock JSON data.
* **Manual Verification:** Run `npm run dev` and log in via the browser. The dashboard should accurately reflect the dummy DB row inserted during Milestone 1.
* **Acceptance Criteria:**
  - Daily Goal, Lessons Today, Quizzes Today, XP Today match the API payload.
  - Refresh after quiz completion updates values without hard reload.

---

## MILESTONE 4: The Acquisition and Active Recall Engine (AI Agents)
*Where learning actually happens.*

### 4.1 Implementation: AI Tutor & Quizzer Agents
* **What we are doing:** Orchestrating the local LLM (`Qwen2.5`) to act interactively. 
  * *Tutor:* Reads Vectors from the DB and explains concepts conversationally via Socratic methods.
  * *Quizzer:* Generates 3-5 multi-choice questions after the Tutor module ends.
* **Interconnected Subsystems:** Reads context from Pinecone/Vectorstore. Writes results (XP, score) via Milestone 2 API -> updates Milestone 1 DB models.
* **Outcome:** A student reads a module, takes a dynamic quiz, and their XP automatically increments by +50 on the frontend.
* **Detailed Tasks:**
  - Implement RAG pipeline for tutor context.
  - Enforce quiz JSON schema validation.
  - Map quiz results to TopicMastery updates.
* **Automated Verification:** 
  * AI output validation scripts: Assert that the Quizzer actually returns 4 options and 1 correct answer in a strict JSON format.
* **Manual Verification:** Open the UI, complete a dummy lesson, answer 3 quiz questions. Watch the "Quizzes Today" counter increment from 0 to 1 and the "Daily Goal" bar move to 50%.
* **Acceptance Criteria:**
  - Tutor and Quizzer produce valid JSON every time.
  - XPEvent row created after quiz completion.

---

## MILESTONE 5: The Loop Closer (Strategist Agent and Knowledge Graph)
*The system gets smart and adapts to the student.*

### 5.1 Implementation: The Overnight Recalibration
* **What we are doing:** Creating a background worker/cron job. It evaluates the `TopicMastery` DB tracking. If a student failed the Quiz (from Milestone 4), it schedules a remedial session for tomorrow.
* **Interconnected Subsystems:** Reads `TopicMastery` -> Updates `DailyProgress` target for the *next* day.
* **Outcome:** The Adaptive Loop is officially a loop. High scores lead to advanced topics; low scores lead to fundamental review. The student's path is 100% personalized.
* **Detailed Tasks:**
  - Build strategist job entry point and scheduling.
  - Define scoring rules for remedial vs advanced insertion.
  - Save plan JSON and mark previous plan as replaced.
* **Automated Verification:** 
  * Unit test: Feed the Strategist Agent a "failed quiz" payload and assert that its generated next-day plan includes a "remedial" tag.
* **Manual Verification:** Log in, maliciously fail all quizzes in a module. Fast-forward the system clock (or manually trigger the cron job). Log in again and verify the Dashboard now says "Let's review yesterday's weak points" instead of pushing new content.
* **Acceptance Criteria:**
  - Plan regeneration runs without manual edits.
  - Next day plan is different after poor performance.

---

## PHASE 3 EXTENSIONS (Exam Conditioning)
*To be implemented ONLY after Milestone 1-5 loop is fully airtight.*

1. **Spaced Repetition System (SRS):** Hooking into the Strategist algorithm to bring back topics 7/21/60 days later.
2. **Mock Exam Simulator:** Generating 200 question full-length bounds with UI countdown timers.
3. **Multimodal Doubt Solver:** UI upload button -> processing using vision models -> saving to `TopicMastery`.
4. **Burnout Detection:** Analyzing `StudySession` time gaps to trigger low-pressure rest days.

---
## Verification Matrix (End-to-End, No Gaps)
Automated:
- `verify_models.py` passes after new models are added.
- API smoke tests pass for all new endpoints.
- Frontend tests render all widgets with mock data.

Manual:
- Create dummy DailyProgress row, verify UI reflects it.
- Complete lesson -> verify Lessons Today incremented.
- Complete quiz -> verify Quizzes Today and XP Today incremented.
- Trigger strategist -> verify tomorrow plan changes.

## Flow Testing Harness (Core Loop)
Automated:
- scripts/test_core_learning_flow.py
  - Auth register/login
  - Dashboard summary
  - Lesson completion -> XP and progress updates
  - Learn session (optional LLM message)
  - Quiz start/answer/finish -> mastery updated
  - Planner generate/daily/update
  - Progress and gamification snapshots

Manual:
- Run the same path in the UI and confirm the same counters update.
- Validate that no step requires manual DB edits.

## Open Questions (Resolve Before Implementation)
- Confirm User model/table name for FK usage.
- Confirm authentication dependency for student endpoints.
- Confirm where plan JSON should be stored (DB vs file).
- Confirm whether daily goal percent should be computed or stored.

## Document Status
Status: ACTIVE
Currently Executing: MILESTONE 1 (Database Foundation)
Last Updated: 2026-03-31