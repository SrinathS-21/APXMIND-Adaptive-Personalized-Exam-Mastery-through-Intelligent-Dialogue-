# APXMIND Learning Ticket Execution Status

Date: 2026-04-01

## Scope
Status snapshot for BL-01 to BL-12 using code and smoke test evidence.

Legend:
- Complete: Implemented and verified by smoke flow.
- Partial: Core backend exists, but missing full UI/automation/DoD coverage.
- Pending: Not implemented yet.

## Ticket Status

| Ticket | Status | Why |
|---|---|---|
| BL-01 Lesson recall submission + feedback | Complete | Lesson recall is now enforced in lesson flow UI (`LearnPage`) via required recall submission before quiz progression, and completion is persisted through `/api/retrieval/lesson-recall` + lesson complete API. |
| BL-02 Daily mixed mini-set | Complete | Dedicated mini-set page and route (`/mini-set`) are implemented, planner mini_set tasks launch directly into the flow, and dashboard next-action routing is validated. |
| BL-03 Error notebook auto-log | Complete | Wrong quiz answers create/update mistake cards; API + UI integration + smoke pass. |
| BL-04 Confidence capture and calibration basics | Complete | Confidence captured in quiz submission and calibration insights endpoint is passing in smoke tests. |
| BL-05 Spaced scheduler core | Complete | Spaced review items are created, listed, and completed with interval updates. |
| BL-06 Spaced queue API and UI | Complete | Queue endpoints integrated and used in Study Plan UI; smoke pass confirmed. |
| BL-07 Mastery state labels and risk scoring | Complete | Mastery labels and risk topics endpoints available and validated in smoke tests. |
| BL-08 Weekly report export | Complete | Weekly report JSON + markdown export validated by smoke tests. |
| BL-09 Adaptive planner generation | Complete | Planner generation + strategist endpoint + automatic daily autogeneration on fetch implemented and verified. |
| BL-10 Planner task execution tracking | Complete | Task status updates, adherence metrics, and skip reschedule behavior verified. |
| BL-11 Exam stamina timed drills | Complete | Stamina start/finish APIs, persistence model, dashboard/planner routing, and dedicated UI (`/exam/stamina`) are implemented and smoke-validated. |
| BL-12 Sync journal and batch sync API | Complete | Sync journal model and `/api/sync/batch` + `/api/sync/status` APIs are implemented with idempotency handling, plus frontend sync queue auto-flush integration. |

## Delta Completed in this pass
1. Completed BL-02 dedicated daily mixed mini-set experience with route wiring and planner CTA integration.
2. Completed BL-11 exam stamina drill APIs + UI with fatigue analytics and planner CTA integration.
3. Completed BL-12 backend sync journal with idempotent `/api/sync/batch` and `/api/sync/status` endpoints.
4. Added frontend sync queue module (`syncService`) with local persistence, retry-safe flush, and online auto-flush bootstrap.
5. Wired sync enqueue across write-heavy frontend flows: planner generation/task updates, retrieval recall/complete, mistake-card update, lesson completion, quiz finish, study minutes, and stamina finish.
6. Extended core smoke coverage to include sync batch ingest, idempotency replay behavior, and sync status backlog checks.

## Verification Evidence
- `python scripts/test_core_learning_flow.py --base-url http://127.0.0.1:8000` => PASS (31/31)
- `python scripts/test_learning_backlog.py --base-url http://127.0.0.1:8000` => PASS
- `cd client && npm run build` => PASS

## Highest Priority Remaining
1. Backlog BL-01 to BL-12 is complete based on current smoke evidence.
2. Next increment should focus on hardening: offline simulation checks, additional idempotency conflict tests, and alerting/telemetry dashboards.
