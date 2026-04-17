# APXMIND Lesson Cockpit Action Plan

Date: 2026-04-12
Owner: Product + Frontend + Backend + Learning Science
Status: Ready to execute

## 1. Problem Statement
Current flow:
1. User opens a subject page.
2. User clicks any lesson.
3. User lands on a mostly generic tutor screen.

Gap:
- Lesson context is weak after navigation.
- The page does not adapt deeply by lesson, subject, or current learner state.
- Recall block exists, but guidance and progression are not yet mission-driven.

## 2. Outcome Goals
Primary outcomes:
- Make each lesson screen feel lesson-specific and adaptive.
- Increase active learning (retrieval, checks, reflection) without increasing friction.
- Improve completion quality, not only completion count.

Success metrics:
- +20% lesson completion with recall submitted.
- +15% D+1 recall performance on covered topics.
- -20% repeated mistakes for concepts covered in the lesson.
- +10% average session depth (messages per lesson session).

## 3. Product Scope (Phased)

### Phase 1: Contextual Lesson Shell (MVP)
Deliverables:
- Lesson Mission Card at top of Learn screen.
- Smart Start Modes: Guided Learn, Rapid Revision, Exam Drill.
- Lesson-specific welcome prompt and suggested first actions.
- Improved Recall panel structure with explicit fields.

In-scope behavior:
- Mission Card uses current lesson metadata (title, difficulty, estimated time, topics).
- Mode selection influences first system prompt and UI hints.
- No heavy schema migrations required for first release.

### Phase 2: Adaptive Learning Loop
Deliverables:
- Auto Checkpoint Pulse every 3-4 user turns.
- Confidence check + quick concept check scoring.
- Mistake DNA tags (concept, formula, careless, time pressure, misread).
- Session summary card at lesson end.

In-scope behavior:
- Checkpoint results update local session state and backend analytics.
- Mistake tags are generated from user answer patterns and response text.

### Phase 3: Subject-Aware Workspace
Deliverables:
- Physics helpers: formula lane and variable reminder panel.
- Chemistry helpers: reaction pathway and exception cues.
- Biology helpers: process map and sequence memory cards.
- Finish Strong screen with mastery delta and next review schedule.

In-scope behavior:
- Keep one shared layout shell.
- Inject subject-specific side tools as pluggable widgets.

## 4. Technical Design

### 4.1 Frontend Changes
Primary files:
- client/src/pages/LearnPage.tsx
- client/src/lib/learnSessionService.ts
- client/src/lib/retrievalService.ts
- client/src/lib/uiI18n.ts

New components to add:
- client/src/components/learn/LessonMissionCard.tsx
- client/src/components/learn/TutorModeSelector.tsx
- client/src/components/learn/CheckpointPulseCard.tsx
- client/src/components/learn/SubjectToolPanel.tsx
- client/src/components/learn/FinishStrongCard.tsx

State model additions in Learn page:
- selectedTutorMode: guided | revision | drill
- checkpointState: nextTriggerTurn, pendingQuestion, recentScores
- lessonMission: objective list, expectedDuration, focusTopics
- subjectToolState: formulaList / pathwayNodes / processSteps

### 4.2 Backend Changes
Primary files:
- src/apxmind/server/routes/learn.py
- src/apxmind/server/routes/subjects.py
- src/apxmind/api/schemas.py
- src/apxmind/db/models.py

New or extended endpoints:
- GET /api/learn/lessons/{lesson_id}/context
  - returns mission summary, focus topics, prerequisite hints
- POST /api/learn/sessions/{session_id}/checkpoint
  - stores checkpoint response and score
- POST /api/learn/sessions/{session_id}/mode
  - stores active tutor mode for analytics and prompts
- GET /api/learn/sessions/{session_id}/summary
  - returns recap, mistake tags, and suggested next actions

Prompt behavior updates:
- Use selected tutor mode as instruction style control.
- Inject lesson mission context into assistant responses.
- Trigger short checkpoint prompts at configured turn intervals.

### 4.3 Data Model Additions (Phase 2+)
Candidate tables:
- lesson_checkpoints
  - id, session_id, lesson_id, concept_key, prompt, user_answer, score, created_at
- lesson_session_state
  - session_id, tutor_mode, checkpoint_interval, last_checkpoint_turn
- lesson_summary_snapshots
  - session_id, mastery_delta, confidence_gap, recommended_review_at

If migration risk must stay low, use existing JSON payload fields first and normalize later.

## 5. Delivery Plan by Sprint

### Sprint 1 (5 days): Phase 1 MVP
Build:
- Mission Card UI + data wire from lesson metadata.
- Tutor mode selector + request payload propagation.
- Lesson-specific welcome and CTA hints.
- Recall panel copy and field structure improvements.

Acceptance criteria:
- Mode selection persists for active session.
- Mission card always matches selected lesson.
- No regressions in send message, reopen session, recall submit.

### Sprint 2 (5 days): Phase 2 Core
Build:
- Checkpoint pulse trigger logic.
- Checkpoint API endpoint and persistence.
- Mistake DNA tagging (rule-based first, model-assisted later).
- Session summary API and UI card.

Acceptance criteria:
- Checkpoint appears at expected cadence.
- Checkpoint results persist and load in session summary.
- Mistake tags are visible and actionable.

### Sprint 3 (7 days): Phase 3 Differentiation
Build:
- Subject-specific tool panel widgets.
- Finish Strong screen with adaptive next steps.
- Links from summary to spaced revision or quiz.

Acceptance criteria:
- Physics/Chemistry/Biology each render different tool panel content.
- Finish card includes next review time and task CTA.

## 6. QA and Validation Plan
Functional tests:
- Lesson navigation from each subject to mission-aware Learn page.
- Mode switch updates assistant behavior and backend records.
- Checkpoint submission and summary retrieval.
- Recall save + lesson complete flow still works.

Behavioral tests:
- Compare completion quality metrics pre/post release.
- Track checkpoint correctness and confidence trends.

Performance tests:
- Ensure no noticeable UI lag from new panels.
- Keep lesson screen first render under current baseline + 15%.

## 7. Rollout Strategy
- Stage 1: Internal feature flags for all new widgets.
- Stage 2: 20% user rollout for Phase 1.
- Stage 3: 100% rollout for Phase 1, then progressive release of Phase 2 and 3.

Feature flags suggested:
- lesson_mission_card_enabled
- tutor_mode_selector_enabled
- checkpoint_pulse_enabled
- subject_tool_panels_enabled
- finish_strong_card_enabled

## 8. Immediate Next Tasks (Start Now)
1. Create frontend scaffolding for Mission Card and Tutor Mode selector.
2. Extend send message payload to include tutor mode.
3. Add backend schema field for tutor mode in message/session requests.
4. Add first lesson context endpoint using current Lesson table data.
5. Wire mission card to new endpoint with graceful fallback.

## 9. Risks and Mitigations
Risk: Scope expansion from creative ideas.
Mitigation: Ship Phase 1 fully before Phase 2 starts.

Risk: Prompt instability with too many controls.
Mitigation: Use strict prompt template sections and A/B prompt variants.

Risk: Analytics noise from mixed legacy and new sessions.
Mitigation: Include feature version tags in session metadata.

## 10. Definition of Done
- Feature flags and rollout plan merged.
- Phase-specific acceptance criteria passed.
- No breakage in existing learn, quiz, and recall flows.
- Documentation and runbook updated.
