# APXMIND Learning Product Backlog (Execution Spec)

Date: 2026-03-29
Owner: Product + Engineering + Learning Science
Status: Ready for sprint planning

Related strategy document:
- [LEARNING_FEATURE_ROADMAP.md](LEARNING_FEATURE_ROADMAP.md)
- [LEARNING_TICKET_EXECUTION_STATUS.md](LEARNING_TICKET_EXECUTION_STATUS.md)

## 1. Objective
Translate APXMIND's offline-first learning strategy into build-ready execution items with:
- exact user stories
- data model fields
- API endpoints
- UI screens and flows
- release-wise effort estimates (S/M/L)

This spec is aligned with existing APXMIND tables and routes, especially:
- learning and chat: `learning_sessions`, `chat_messages`, `query_events`
- mastery and insights: `topic_mastery`, `exam_readiness_snapshots`, `habit_signals`
- event log: `learning_events`

---

## 2. Delivery Slices

### Release 1 (Weeks 1-3): Retrieval Foundation
Primary outcomes:
- every lesson ends with memory retrieval
- every mistake is captured and reused
- mixed daily mini-practice starts behavior change

### Release 2 (Weeks 4-7): Retention Engine
Primary outcomes:
- spaced queue operational (D+1, D+3, D+7, D+14)
- mastery map visible and trustworthy
- weekly offline report available

### Release 3 (Weeks 8-12): Personalization + Reliability
Primary outcomes:
- adaptive daily planner
- exam stamina mode
- low-bandwidth sync safety

---

## 3. Epics, User Stories, Acceptance Criteria, Estimates

## Epic E1: Retrieval and Memory Loop

### Story E1-S1: End-of-lesson 2-minute recall
As a student, I want a short recall task after each lesson so I can retain what I learned.

Acceptance criteria:
- lesson completion triggers recall prompt automatically
- prompt is memory-first (no immediate hint reveal)
- self-check appears after answer submission
- completion writes a `learning_event` with `event_type=recall_completed`
- works offline and queues sync events

Estimate: M
Dependencies: existing lesson completion flow

---

### Story E1-S2: Recall quality scoring
As a student, I want feedback on recall quality so I know if I should revise now.

Acceptance criteria:
- rubric score stored as 0-100 in recall payload
- score bands shown: Strong / Needs Review / Retry
- low score adds item to spaced queue for next day

Estimate: M
Dependencies: E1-S1

---

### Story E1-S3: Daily mixed mini-set
As a student, I want 5 mixed questions daily across Bio/Chem/Phy so I can improve transfer.

Acceptance criteria:
- at least 5 questions with mixed subjects
- no blocked pattern of same concept for all 5
- completion logs `event_type=interleaved_set_completed`
- score and response time captured

Estimate: M
Dependencies: question selection service

---

## Epic E2: Mistake Intelligence + Metacognition

### Story E2-S1: Auto error notebook
As a student, I want wrong answers converted into mistake cards so I can avoid repeated errors.

Acceptance criteria:
- every incorrect answer creates/updates a mistake card
- card includes concept tag, reason tag, correction note
- card appears in revision list within 24 hours
- deduplication by user + concept + error pattern

Estimate: M
Dependencies: quiz answer pipeline

---

### Story E2-S2: Confidence slider before submit
As a student, I want to mark confidence before answering so I can calibrate my judgment.

Acceptance criteria:
- confidence input required on eligible assessments (1-5)
- confidence and correctness stored together
- analytics view shows confident-wrong frequency

Estimate: S
Dependencies: assessment UI components

---

### Story E2-S3: Calibration dashboard card
As a student, I want weekly calibration insight so I know where I overestimate mastery.

Acceptance criteria:
- weekly card shows:
  - mean confidence
  - actual accuracy
  - confidence-accuracy gap
- trend visible for last 4 weeks

Estimate: S
Dependencies: E2-S2 data capture

---

## Epic E3: Spaced Revision Engine

### Story E3-S1: Spaced scheduler baseline
As a student, I want automatic spaced revision scheduling so I review before forgetting.

Acceptance criteria:
- schedule intervals: D+1, D+3, D+7, D+14
- missed review requeues with shorter gap
- completed review advances interval
- all scheduling logic works offline

Estimate: L
Dependencies: event log reliability

---

### Story E3-S2: Spaced queue API + UI
As a student, I want to see my due revision queue and complete it quickly.

Acceptance criteria:
- queue endpoint returns due items sorted by urgency
- one-tap "Start Revision" launches review flow
- completion updates `next_due_at`

Estimate: M
Dependencies: E3-S1

---

### Story E3-S3: Anti-cram alerts
As a student, I want reminders when I postpone too many due reviews.

Acceptance criteria:
- alert shown if overdue count exceeds threshold
- reminder message includes estimated catch-up effort
- optional local notification integration

Estimate: S
Dependencies: E3-S2

---

## Epic E4: Mastery and Insights

### Story E4-S1: Mastery state labels
As a student, I want each micro-topic labeled as Not Started, Shaky, or Strong.

Acceptance criteria:
- score thresholds map to 3 states
- labels visible by subject and chapter
- labels refresh after quiz/recall/review events

Estimate: M
Dependencies: existing `topic_mastery`

---

### Story E4-S2: Topic risk list
As a student, I want a risk-ranked topic list so I can prioritize study effectively.

Acceptance criteria:
- risk score combines low mastery + high error recurrence + time since last success
- top-10 risk topics visible on dashboard

Estimate: M
Dependencies: E4-S1, E2-S1

---

### Story E4-S3: Weekly offline report card
As a student, I want a weekly downloadable summary so I can review progress with mentor/parent.

Acceptance criteria:
- includes retention, accuracy, speed, risk topics
- generated fully offline
- export as PDF/image

Estimate: M
Dependencies: E4-S1, E4-S2

---

## Epic E5: Adaptive Planner

### Story E5-S1: Daily plan generation
As a student, I want a daily study plan based on my weak areas and available time.

Acceptance criteria:
- inputs: exam date, weak topics, spaced due queue, daily time budget
- plan allocates slots across revision + practice + new learning
- plan updates when user misses tasks

Estimate: L
Dependencies: E3 and E4 epics

---

### Story E5-S2: Planner adherence tracking
As a student, I want to see whether I followed my plan so I can improve consistency.

Acceptance criteria:
- each planned task has status: pending/completed/skipped
- weekly adherence % shown
- skipped tasks auto-rescheduled with priority

Estimate: M
Dependencies: E5-S1

---

### Story E5-S3: Mentor-style planner nudges
As a student, I want motivational nudges tied to my plan so I stay consistent.

Acceptance criteria:
- nudge templates vary by adherence and streak
- all nudges available offline

Estimate: S
Dependencies: notification framework

---

## Epic E6: Exam Readiness and Stamina

### Story E6-S1: Difficulty ladder mode
As a student, I want progression from easy to NEET-level so I build confidence and depth.

Acceptance criteria:
- question sessions support ladder stages
- stage advancement based on accuracy + confidence stability

Estimate: M
Dependencies: assessment service updates

---

### Story E6-S2: Timed stamina drills
As a student, I want timed section drills so I can improve endurance and pacing.

Acceptance criteria:
- configurable timed blocks
- fatigue markers captured (late-session accuracy dip)
- post-drill feedback shows pacing and error clusters

Estimate: M
Dependencies: timer and analytics event capture

---

### Story E6-S3: Monthly score projection trend
As a student, I want a projected NEET score trend so I can see if my plan is working.

Acceptance criteria:
- monthly projection with confidence band
- transparent note: "estimate, not guarantee"

Estimate: M
Dependencies: readiness scoring logic

---

## Epic E7: Offline-First Sync and School Scale

### Story E7-S1: Local-first sync journal
As a student, I want my progress safe offline so nothing is lost without internet.

Acceptance criteria:
- all key writes recorded in local sync journal
- retries on connectivity restore
- idempotent server writes supported

Estimate: L
Dependencies: API idempotency strategy

---

### Story E7-S2: Conflict-safe merge rules
As a platform maintainer, I want deterministic merge behavior so data remains consistent across devices.

Acceptance criteria:
- merge rules documented for sessions, mastery, planner tasks, mistake cards
- conflict audit events logged

Estimate: M
Dependencies: E7-S1

---

### Story E7-S3: School/Lab LAN mode (Phase 2 candidate)
As a teacher, I want local classroom visibility over LAN so I can support many students offline.

Acceptance criteria:
- one LAN host dashboard can read student progress snapshots
- no internet required for classroom session

Estimate: L
Dependencies: local network service and auth model

---

## 4. Data Model Specification

Design principle:
- reuse existing tables first (`learning_events`, `topic_mastery`, `habit_signals`, `exam_readiness_snapshots`, `learning_recommendations`)
- add only minimal new tables for retrieval-specific and planner-specific workflows

## 4.1 Reuse Existing Tables (No schema break)

### Table: `learning_events` (existing)
New `event_type` values:
- `recall_started`
- `recall_completed`
- `interleaved_set_completed`
- `confidence_recorded`
- `spaced_review_completed`
- `planner_task_completed`
- `stamina_drill_completed`

Payload fields (by event):
- `topic`, `chapter`, `difficulty`, `score_percent`, `confidence_level`, `time_taken_sec`, `error_reason`, `next_due_at`

---

### Table: `topic_mastery` (existing)
Additions:
- add nullable `state_label` (text) OR derive at read time from `mastery_score`
- optional `last_success_at` for risk scoring

Recommendation:
- derive labels in service first to avoid migration risk

---

### Table: `learning_recommendations` (existing)
Use for planner output items:
- `rec_type` values: `daily_plan_task`, `revision`, `mini_set`, `stamina_drill`
- `status`: `active`, `accepted`, `dismissed`, `completed`

---

## 4.2 New Tables (Proposed)

### Table: `mistake_cards`
Purpose:
- persistent structured error notebook

Fields:
- `id` (uuid pk)
- `user_id` (fk users)
- `subject` (text)
- `topic` (text)
- `source_type` (quiz/recall/drill)
- `source_id` (text)
- `error_reason_code` (formula_error/concept_confusion/misread/time_pressure/other)
- `prompt_snapshot` (text)
- `correct_explanation` (text)
- `times_seen` (int default 1)
- `times_repeated` (int default 0)
- `last_seen_at` (datetime)
- `next_due_at` (datetime)
- `status` (active/resolved)
- `created_at`, `updated_at`

Indexes:
- `(user_id, next_due_at)`
- `(user_id, subject, topic)`

---

### Table: `spaced_reviews`
Purpose:
- explicit queue state for spaced retrieval items

Fields:
- `id` (uuid pk)
- `user_id` (fk users)
- `topic` (text)
- `subject` (text)
- `source_type` (lesson/mistake_card/flashcard)
- `source_id` (text)
- `interval_step` (int; 1,3,7,14,...)
- `due_at` (datetime)
- `last_reviewed_at` (datetime)
- `last_result` (correct/incorrect/partial)
- `ease_factor` (numeric)
- `streak` (int)
- `created_at`, `updated_at`

Indexes:
- `(user_id, due_at)`
- unique `(user_id, source_type, source_id)`

---

### Table: `planner_tasks`
Purpose:
- track concrete daily plan execution

Fields:
- `id` (uuid pk)
- `user_id` (fk users)
- `task_date` (date)
- `task_type` (revision/new_learning/mini_set/stamina)
- `subject` (text)
- `topic` (text)
- `recommended_minutes` (int)
- `priority_score` (numeric)
- `status` (pending/completed/skipped)
- `completed_at` (datetime)
- `source_recommendation_id` (fk learning_recommendations nullable)
- `created_at`, `updated_at`

Indexes:
- `(user_id, task_date)`
- `(user_id, status, task_date)`

---

### Table: `sync_journal`
Purpose:
- local-first reliable sync replay (client and optional server mirror)

Fields:
- `id` (uuid pk)
- `user_id` (fk users)
- `operation_type` (create/update/delete/event)
- `entity_type` (mistake_card/planner_task/spaced_review/event)
- `entity_id` (text)
- `payload` (json)
- `idempotency_key` (text unique)
- `attempt_count` (int)
- `last_attempt_at` (datetime)
- `synced_at` (datetime nullable)
- `status` (pending/synced/failed)
- `created_at`

Indexes:
- `(user_id, status, created_at)`
- unique `(idempotency_key)`

---

## 5. API Endpoint Draft (v1)

Naming policy:
- follow existing style under `/api/*`
- keep reads and writes explicit
- require auth on all routes

## 5.1 Retrieval and Spaced

### POST `/api/retrieval/lesson-recall`
Purpose:
- submit 2-minute recall result

Request:
- `lesson_id`, `subject`, `topic`, `response_text`, `self_score`, `time_taken_sec`

Response:
- `score_band`, `gaps`, `next_review_due`

---

### GET `/api/retrieval/spaced-queue`
Purpose:
- fetch due spaced items

Query params:
- `limit`, `due_before`

Response:
- list of due review cards

---

### POST `/api/retrieval/spaced-queue/{id}/complete`
Purpose:
- mark a spaced item as completed and compute next interval

Request:
- `result` (correct/partial/incorrect), `confidence_level`

Response:
- `next_due_at`, `interval_step`, `updated_ease_factor`

---

## 5.2 Error Notebook + Calibration

### GET `/api/errors/mistake-cards`
Query:
- `status`, `subject`, `limit`

### PATCH `/api/errors/mistake-cards/{id}`
Purpose:
- resolve/reactivate/edit reason tags

### GET `/api/insights/calibration`
Purpose:
- confidence vs correctness metrics over time

Query:
- `days=7|30|90`

---

## 5.3 Planner

### GET `/api/planner/daily`
Purpose:
- return generated task list for a date

Query:
- `date=YYYY-MM-DD`

### POST `/api/planner/generate`
Purpose:
- generate/re-generate daily plan

Request:
- `date`, `available_minutes`

### PATCH `/api/planner/tasks/{id}`
Purpose:
- update task status

Request:
- `status` (completed/skipped)

---

## 5.4 Exam Stamina + Readiness

### POST `/api/exam/stamina/sessions`
Purpose:
- start timed drill

### POST `/api/exam/stamina/sessions/{id}/finish`
Purpose:
- submit performance summary

### GET `/api/insights/readiness` (existing, extend payload)
Enhancement:
- add `projection_confidence_band`

---

## 5.5 Sync

### POST `/api/sync/batch`
Purpose:
- upload pending local journal operations

Request:
- list of operations with idempotency keys

Response:
- per-item accepted/rejected/retry statuses

### GET `/api/sync/status`
Purpose:
- health and backlog count

---

## 6. UI Screens and Flow

## 6.1 New/Updated Screens

1. Lesson End Recall Modal
- appears on lesson completion
- includes timer, response box, self-check

2. Daily Practice Home Card
- shows due spaced count + mini-set CTA + planner progress

3. Error Notebook Screen
- filter by subject/topic/reason
- quick retry and mark resolved

4. Mastery Map Screen (updated)
- state labels and risk list

5. Planner Screen (new)
- daily tasks with status and drag re-order (optional)

6. Weekly Report Screen
- retention/accuracy/speed/risk with export button

7. Calibration Insight Card
- confidence vs correctness chart

8. Stamina Drill Screen
- timed sectional drill and post-analysis

## 6.2 Core UX Flow (student)
1. Learn lesson
2. Complete 2-minute recall
3. Daily mini-set
4. Review spaced queue
5. Resolve mistake cards
6. Follow planner tasks
7. Check weekly report and readiness trend

---

## 7. Backlog by Release With S/M/L Estimates

| ID | Item | Release | Estimate |
|---|---|---|---|
| BL-01 | Lesson recall submission + feedback | R1 | M |
| BL-02 | Daily mixed mini-set | R1 | M |
| BL-03 | Error notebook auto-log | R1 | M |
| BL-04 | Confidence capture and chart basics | R1 | S |
| BL-05 | Spaced scheduler core | R2 | L |
| BL-06 | Spaced queue API + UI | R2 | M |
| BL-07 | Mastery state labels + risk scoring | R2 | M |
| BL-08 | Weekly report export | R2 | M |
| BL-09 | Adaptive planner generation | R3 | L |
| BL-10 | Planner task execution tracking | R3 | M |
| BL-11 | Exam stamina timed drills | R3 | M |
| BL-12 | Sync journal + batch sync API | R3 | L |

Sizing reference:
- S = 1-3 dev days
- M = 4-8 dev days
- L = 9-15 dev days

---

## 8. Telemetry and Success Metric Mapping

| Metric | Definition | Source |
|---|---|---|
| D7 retention | correct on day-7 review / total day-7 reviews | `spaced_reviews`, `learning_events` |
| D30 retention | correct on day-30 review / total day-30 reviews | `spaced_reviews` |
| Repeated mistake rate | repeated wrongs per concept / attempts | `mistake_cards`, quiz answers |
| Weekly active study days | unique days with study activity | `habit_signals` |
| Interleaving transfer score | score on mixed mini-sets | `learning_events` |
| Confidence calibration gap | avg(confidence) - accuracy | confidence events + outcomes |
| Monthly projected score trend | readiness projection over months | `exam_readiness_snapshots` |

---

## 9. Engineering Notes and Risk Controls

1. Offline-first contract
- no blocking dependency on network for core loops
- sync must be retry-safe and idempotent

2. Performance contract
- recall submission response under 500ms (local path)
- spaced queue fetch under 300ms on local cache

3. Data integrity
- include idempotency keys for all event writes
- do not mutate append-only events

4. Pedagogy safety
- avoid punitive feedback language
- preserve student trust with transparent scoring and projections

---

## 10. Immediate Build Order (Start Tomorrow)

Sprint A (7-10 days):
- BL-01, BL-02, BL-03

Sprint B (7-10 days):
- BL-04, BL-05

Sprint C (7-10 days):
- BL-06, BL-07, BL-08

Sprint D (7-10 days):
- BL-09, BL-10

Sprint E (7-10 days):
- BL-11, BL-12

---

## 11. Definition of Done (Per Story)

A story is complete only when all are true:
- acceptance criteria pass
- API contract documented in OpenAPI route docs
- offline behavior verified with network disabled
- telemetry event emitted and validated
- unit/integration tests added or updated
- smoke path added to API smoke profile where applicable

---

## 12. Suggested Next Artifact
Create `LEARNING_API_CONTRACTS.md` with exact request/response schemas for BL-01 to BL-12 so backend and frontend can start parallel implementation immediately.

---

## 13. Verification Commands

Run learning backlog smoke tests:

```powershell
python scripts/test_learning_backlog.py --base-url http://127.0.0.1:8000
```

Run platform regression smoke tests:

```powershell
python scripts/verify_full_stack.py --base-url http://127.0.0.1:8000
```
