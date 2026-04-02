# APXMIND Learning API Contracts (BL-01 to BL-12)

Date: 2026-04-01

## Scope
Canonical request/response contracts for the learning backlog slice BL-01 through BL-12.
All routes require authenticated user context.

## BL-01 Lesson Recall Submission + Feedback
Endpoint: POST /api/retrieval/lesson-recall

Request:
```json
{
  "lesson_id": 12,
  "subject": "biology",
  "topic": "human physiology",
  "response_text": "student recall text",
  "self_score": 65,
  "time_taken_sec": 120
}
```

Response:
```json
{
  "success": true,
  "score_band": "partial",
  "next_review_due": "2026-04-03T08:30:00Z",
  "spaced_review_id": "uuid",
  "gaps": ["missing definitions"]
}
```

## BL-02 Daily Mixed Mini-Set
Endpoint: POST /api/quiz

Request:
```json
{
  "subject": "biology",
  "difficulty": "mixed",
  "question_count": 12,
  "topic": "mixed"
}
```

Response:
```json
{
  "quiz": {
    "id": "uuid",
    "subject": "biology",
    "difficulty": "mixed",
    "status": "active"
  },
  "questions": [
    {
      "id": 101,
      "question_no": 1,
      "question_text": "...",
      "options": ["A", "B", "C", "D"]
    }
  ]
}
```

Related:
- POST /api/quiz/{id}/answers
- POST /api/quiz/{id}/finish

## BL-03 Error Notebook Auto-Log
Endpoint: GET /api/errors/mistake-cards

Query:
- status: active|resolved
- subject: optional
- limit: integer

Response:
```json
{
  "success": true,
  "cards": [
    {
      "id": "uuid",
      "subject": "biology",
      "topic": "cell cycle",
      "error_reason_code": "concept_confusion",
      "status": "active"
    }
  ]
}
```

Update Endpoint: PATCH /api/errors/mistake-cards/{id}

Request:
```json
{
  "status": "resolved"
}
```

## BL-04 Confidence Capture + Calibration
Answer Endpoint: POST /api/quiz/{id}/answers

Request:
```json
{
  "question_id": 101,
  "user_answer": "B",
  "confidence_level": 4
}
```

Calibration Endpoint: GET /api/insights/calibration?days=30

Response:
```json
{
  "sample_count": 14,
  "mean_confidence": 3.7,
  "accuracy_percent": 64.3,
  "confidence_accuracy_gap": 9.2,
  "confident_wrong_rate": 18.5,
  "trend": []
}
```

## BL-05 Spaced Scheduler Core
Endpoint: GET /api/retrieval/spaced-queue

Query:
- limit
- due_before (ISO datetime)

Response:
```json
{
  "success": true,
  "due_items": [
    {
      "id": "uuid",
      "topic": "human physiology",
      "interval_step": 2,
      "due_at": "2026-04-02T07:00:00Z"
    }
  ]
}
```

## BL-06 Spaced Queue Completion API
Endpoint: POST /api/retrieval/spaced-queue/{id}/complete

Request:
```json
{
  "result": "correct",
  "confidence_level": 4
}
```

Response:
```json
{
  "success": true,
  "next_due_at": "2026-04-05T07:00:00Z",
  "interval_step": 3,
  "streak": 2
}
```

## BL-07 Mastery Labels + Risk Scoring
Endpoint: GET /api/insights/mastery?subject=biology

Response:
```json
{
  "success": true,
  "mastery": [
    {
      "subject": "biology",
      "topic": "genetics",
      "mastery_score": 61.2,
      "confidence": 58.0,
      "state_label": "fragile"
    }
  ]
}
```

Endpoint: GET /api/insights/risk-topics?subject=biology&limit=10

Response:
```json
{
  "success": true,
  "risk_topics": [
    {
      "subject": "biology",
      "topic": "genetics",
      "risk_score": 72.4,
      "state_label": "fragile"
    }
  ]
}
```

## BL-08 Weekly Report Export
Endpoint: GET /api/insights/weekly-report?days=7&export_format=json

Response:
```json
{
  "success": true,
  "summary": {
    "retention_score": 68.0,
    "accuracy_percent": 64.1,
    "speed_qph": 42.3,
    "consistency_score": 71.2
  },
  "risk_topics": []
}
```

Endpoint: GET /api/insights/weekly-report?days=7&export_format=markdown

Response:
```json
{
  "success": true,
  "export": {
    "format": "markdown",
    "filename": "apxmind-weekly-report-2026-04-01.md",
    "content": "# APXMIND Weekly Report..."
  }
}
```

## BL-09 Adaptive Planner Generation
Endpoint: POST /api/planner/generate

Request:
```json
{
  "available_minutes": 90,
  "date": "2026-04-01"
}
```

Response:
```json
{
  "success": true,
  "date": "2026-04-01",
  "generated_count": 4,
  "available_minutes": 90,
  "planned_minutes": 85,
  "tasks": []
}
```

Endpoint: POST /api/planner/strategist

Request:
```json
{
  "date": "2026-04-02"
}
```

## BL-10 Planner Task Execution Tracking
Endpoint: GET /api/planner/daily?date=2026-04-01

Response:
```json
{
  "success": true,
  "date": "2026-04-01",
  "total": 4,
  "completed_count": 2,
  "pending_count": 2,
  "tasks": []
}
```

Endpoint: PATCH /api/planner/tasks/{id}

Request:
```json
{
  "status": "completed"
}
```

Response:
```json
{
  "success": true,
  "task": {
    "id": "uuid",
    "status": "completed"
  },
  "rescheduled_task": null
}
```

## BL-11 Exam Stamina Timed Drills
Endpoint: POST /api/exam/stamina/sessions

Request:
```json
{
  "mode": "mixed",
  "duration_minutes": 30,
  "planned_questions": 30,
  "block_count": 3
}
```

Response:
```json
{
  "success": true,
  "session_id": "uuid",
  "mode": "mixed",
  "duration_minutes": 30,
  "planned_questions": 30,
  "block_plan": [
    {
      "block_no": 1,
      "planned_minutes": 10,
      "planned_questions": 10
    }
  ]
}
```

Endpoint: POST /api/exam/stamina/sessions/{id}/finish

Request:
```json
{
  "block_results": [
    {
      "block_no": 1,
      "attempted_questions": 10,
      "correct_answers": 7,
      "elapsed_sec": 600,
      "dominant_error": "time_pressure"
    }
  ],
  "notes": "lost focus in final block"
}
```

Response:
```json
{
  "success": true,
  "session_id": "uuid",
  "score_percent": 70,
  "pacing_qph": 60,
  "fatigue_accuracy_dip": 8.5,
  "fatigue_detected": true,
  "error_clusters": {
    "time_pressure": 3
  },
  "xp_awarded": 36
}
```

## BL-12 Sync Journal + Batch Sync API
Endpoint: POST /api/sync/batch

Request:
```json
{
  "operations": [
    {
      "operation_type": "event",
      "entity_type": "planner_task",
      "entity_id": "uuid",
      "payload": {
        "status": "completed"
      },
      "idempotency_key": "sync-1711962000-abcd1234"
    }
  ]
}
```

Response:
```json
{
  "success": true,
  "accepted_count": 1,
  "duplicate_count": 0,
  "failed_count": 0,
  "results": [
    {
      "idempotency_key": "sync-1711962000-abcd1234",
      "status": "accepted",
      "journal_id": "uuid",
      "attempt_count": 1,
      "retryable": false
    }
  ]
}
```

Endpoint: GET /api/sync/status

Response:
```json
{
  "success": true,
  "pending_count": 0,
  "synced_count": 12,
  "failed_count": 0,
  "total_count": 12,
  "backlog_count": 0,
  "latest_synced_at": "2026-04-01T11:12:13.456789"
}
```
