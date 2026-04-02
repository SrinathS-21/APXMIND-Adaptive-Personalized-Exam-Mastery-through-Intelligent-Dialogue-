# APXMIND Learning Gap Analysis and Product Ideation

Date: 2026-04-01

## 1) Executive summary
This document maps what is already working, what is still missing, and how to close the gaps so APXMIND becomes a truly adaptive NEET learning system.

Core conclusion:
- The backend foundation is strong (events, mastery, spaced review, planner, strategist endpoint, test harness).
- The biggest product risk is integration drift: key adaptive capabilities exist in backend but are not fully consumed in frontend or automation.
- Highest priority is not adding more features first; it is closing loop integrity and observability so each learner action reliably changes tomorrow's plan.

---

## 2) What is already strong

### 2.1 Learning architecture is well defined
- Strategy and pedagogy principles are strong in [docs/LEARNING_FEATURE_ROADMAP.md](docs/LEARNING_FEATURE_ROADMAP.md).
- Delivery epics and acceptance criteria are well defined in [docs/LEARNING_PRODUCT_BACKLOG.md](docs/LEARNING_PRODUCT_BACKLOG.md).
- End-to-end system contract exists in [docs/CORE_ENGINE_TODO.md](docs/CORE_ENGINE_TODO.md).

### 2.2 Backend capability is advanced
- Retrieval queue and mistake notebook routes exist and are operational.
- Planner generation and execution tracking are implemented.
- Strategist endpoint now exists for adaptive next-day planning.
- Core loop smoke harness exists and is passing.

### 2.3 Data model supports adaptive learning
- Tables for spaced reviews, mistake cards, planner tasks, mastery, events are present.
- Event-first design and idempotency pattern exist for many critical writes.

---

## 3) Missing pieces and systemic gaps

## Gap A: Product loop integrity is still partial at UX level
Problem:
- Route matrix shows many backend endpoints are still backend-only or partially wired.
- This means adaptation can exist in code but not in user experience.

Evidence:
- [docs/ROUTE_UI_MATRIX_SECOND_PASS.md](docs/ROUTE_UI_MATRIX_SECOND_PASS.md)
- [docs/FOUR_TRACK_EXECUTION_STATUS.md](docs/FOUR_TRACK_EXECUTION_STATUS.md)

Impact:
- Student does not consistently experience the full loop: plan -> learn -> quiz -> mastery -> recalibrated plan.

What to add:
- Migrate quiz experience fully to stateful quiz routes and deprecate trainer-only flow.
- Wire strategist action into Study Plan UI as default daily plan source.
- Add lesson-recall UI (currently backend exists but no clear UI path in matrix).

---

## Gap B: Adaptive planning is not yet autonomous
Problem:
- Strategist exists as callable API but no automatic schedule runner.

Evidence:
- Planner and strategist code exists, but no recurring scheduler in app lifecycle.

Impact:
- Adaptation depends on manual trigger; students may receive stale plans.

What to add:
- Daily strategist job runner (local scheduled task):
  - Trigger time per user timezone.
  - Generate D+1 plan from mastery + spaced + mistake data.
  - Mark old pending plans as replaced.
- Add idempotency key per user-date for strategist generation.

---

## Gap C: Metric contract mismatch between docs and implementation
Problem:
- Core metrics in ideation docs (planned_units, completed_units, goal_percent) are not consistently represented in current read models and UI payloads.

Evidence:
- Contracts in [docs/CORE_ENGINE_TODO.md](docs/CORE_ENGINE_TODO.md) vs current dashboard/progress payload patterns.

Impact:
- Dashboard may look complete while hidden metric semantics differ.

What to add:
- Canonical metric service module:
  - Single function to compute lessons today, quizzes today, xp today, daily goal percent.
  - Shared by dashboard, planner, weekly reports, and tests.
- Versioned metric schema for frontend to prevent silent drift.

---

## Gap D: Smoke runbook drift from executable reality
Problem:
- Smoke runbook drift existed and can reoccur if test harness names change.

Evidence:
- Runbook-command drift was identified against the current harness.
- Runbook has now been updated to the active scripts.

Impact:
- QA onboarding confusion and false confidence.

What to add:
- Update runbook to current smoke entrypoint and profiles.
- Add generated report examples and expected pass signature.

---

## Gap E: No closed-loop learning policy layer
Problem:
- Data and endpoints exist, but policy logic for adaptation is still basic.

Impact:
- System adapts, but not deeply enough for exam outcomes.

What to add:
- Policy engine with explicit rules:
  - If confidence high and wrong twice in same topic -> force remedial concept task.
  - If accuracy high and low latency across 3 sessions -> promote difficulty.
  - If missed queue above threshold -> compress plan to revision-heavy mode.
  - If streak break + low minutes 3 days -> burnout-safe plan mode.

---

## Gap F: Frontend adaptive transparency is limited
Problem:
- Student may not understand why tasks changed.

Impact:
- Lower trust, lower adherence.

What to add:
- Why-this-task explainer on every plan item:
  - Example: "Added because your last kinematics quiz accuracy was 40%."
- Daily adaptation summary card:
  - What changed from yesterday and why.

---

## Gap G: Experimentation and learning science validation is missing
Problem:
- Features are added but not scientifically measured per cohort.

Impact:
- Hard to prove efficacy improvements.

What to add:
- Experiment framework:
  - A/B test retrieval prompt variants.
  - Track D7 and D30 retention deltas.
  - Track confidence-error gap trend by cohort.

---

## Gap H: Offline-first sync architecture is still incomplete
Problem:
- Backlog includes sync journal and batch sync, but implementation status is not fully closed in docs.

Evidence:
- Sync APIs and journal are in planning docs but not fully surfaced as complete in status docs.

Impact:
- Multi-device continuity and resilience remain fragile.

What to add:
- Implement sync journal fully with per-operation idempotency key.
- Add conflict rules by entity type (planner_task, mistake_card, spaced_review).
- Add sync health widgets in app settings.

---

## 4) Detailed ideation: next-level product capabilities

## 4.1 Adaptation stack model
Layer 1: Sensing
- Capture performance, confidence, time, interruptions, adherence.

Layer 2: Diagnosis
- Compute weak-topic risk, forgetting risk, overconfidence risk, burnout risk.

Layer 3: Intervention
- Update tomorrow plan with a constrained optimizer:
  - Required revision quota.
  - Weak-topic remediation quota.
  - New-learning quota.
  - Time budget and cognitive load cap.

Layer 4: Reflection
- Show learner-facing explanation and weekly report.

Layer 5: Learning-to-learn
- Tune planner policy based on what interventions improved outcomes.

---

## 4.2 Proposed high-value interventions

1. Retrieval-first lesson closure
- No lesson can be marked complete without short recall attempt.
- Immediate spaced enqueue on weak recall.

2. Confidence-gated progression
- Promote difficulty only when both accuracy and calibration are stable.

3. Dynamic plan compression
- On low adherence days, reduce scope and protect streak.

4. Exam-mode transitions
- As exam date approaches, increase timed mixed sets and stamina blocks.

5. Parent/mentor explainability layer
- Weekly digest with risk topics, consistency, and intervention suggestions.

---

## 5) Priority roadmap to close real gaps

## P0 (now, 1-2 weeks)
1. Align runbooks and smoke docs with actual scripts.
2. Wire strategist endpoint in Study Plan UI.
3. Wire lesson-recall in Learn flow.
4. Decide and execute quiz migration path:
   - stateful quiz route as primary.
   - trainer route as fallback or deprecate.
5. Add adaptation explanation strings to plan items.

Success criteria:
- A student can complete one day loop and see next-day adaptive changes without manual API calls.

## P1 (2-4 weeks)
1. Add automated strategist scheduler.
2. Introduce policy engine rules and versioning.
3. Add metric contract service and dashboard schema stabilization.
4. Add cohort analytics for retention and calibration.

Success criteria:
- Plan updates occur automatically and deterministically.
- Daily Goal and adherence metrics are consistent across pages.

## P2 (4-8 weeks)
1. Full offline sync journal and batch sync.
2. Stamina mode and readiness projection hardening.
3. Mentor and parent reporting packs.

Success criteria:
- Offline continuity and exam conditioning become production-grade.

---

## 6) System design upgrades recommended

1. Event contract registry
- Define every event type and payload schema in one source file.
- Validate payload at write time.

2. Planner policy versioning
- Store policy_version on each generated task.
- Enables rollback and A/B comparisons.

3. Data quality guards
- Nightly audit checks:
  - quizzes completed but no mastery update
  - lesson completed but no recall event
  - planner task completed but no adherence aggregation

4. Adaptation observability
- Add admin-safe internal dashboard for product team:
  - adaptation latency
  - stale plan rate
  - intervention success rate

5. Safe fallback hierarchy
- If model unavailable:
  - deterministic retrieval prompts
  - rule-based quiz generation from local bank
  - planner still generated from known mastery and due queue

---

## 7) KPI tree for decision making

Primary outcome KPIs:
- D7 retention per topic
- D30 retention per topic
- mixed-set transfer score
- confidence-error gap
- weekly adherence percent
- projected score trend

System health KPIs:
- stale plan rate (no regen in 24h)
- event-drop rate
- sync failure rate
- strategist job success rate

Behavior KPIs:
- lesson-to-recall completion ratio
- recall-to-spaced completion ratio
- repeated-mistake rate per concept

---

## 8) Risks and mitigations

Risk: Feature sprawl before loop closure.
Mitigation: Gate all new features behind loop integrity checklist.

Risk: Metric inconsistency across components.
Mitigation: Central metric computation service and contract tests.

Risk: Low trust in adaptation.
Mitigation: Explainability text for every adaptive decision.

Risk: Offline data conflicts.
Mitigation: Idempotent journal with deterministic merge precedence.

---

## 9) Recommended immediate next actions

1. Update route matrix and runbooks to include strategist and current smoke script reality.
2. Add UI action for strategist generation and display adaptation explanations.
3. Add automated daily strategist trigger with test coverage.
4. Add backlog status tracker mapping BL-01 to BL-12 to actual implementation state.
5. Add one integrated dashboard card: "What changed today and why".

---

## 10) Final assessment
APXMIND is close to becoming a strong adaptive learning product. The biggest missing part is not core capability; it is operational glue:
- UI wiring completeness,
- autonomous scheduling,
- metric consistency,
- and documentation-to-runtime alignment.

Once these are closed, the platform can move from "feature rich" to "outcome reliable" for NEET learners.
