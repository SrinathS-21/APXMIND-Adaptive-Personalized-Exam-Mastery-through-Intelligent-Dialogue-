#!/usr/bin/env python3
"""End-to-end flow test for the core learning loop."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

UTC = timezone.utc


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


class HttpClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        *,
        token: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, Dict[str, Any]]:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        req = urllib.request.Request(url=url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                parsed = json.loads(body) if body else {}
                return resp.status, parsed
        except urllib.error.HTTPError as err:
            body = err.read().decode("utf-8")
            try:
                parsed = json.loads(body) if body else {}
            except json.JSONDecodeError:
                parsed = {"raw": body}
            return err.code, parsed


def get_token(payload: Dict[str, Any]) -> Optional[str]:
    return payload.get("token") or payload.get("access_token")


def add_result(results: list[CheckResult], name: str, passed: bool, detail: str) -> None:
    results.append(CheckResult(name=name, passed=passed, detail=detail))
    marker = "PASS" if passed else "FAIL"
    print(f"[{marker}] {name}: {detail}")


def write_report(report_path: Optional[str], results: list[CheckResult]) -> None:
    if not report_path:
        return
    failed = [r for r in results if not r.passed]
    payload = {
        "summary": {
            "total": len(results),
            "passed": len(results) - len(failed),
            "failed": len(failed),
        },
        "checks": [
            {"name": r.name, "passed": r.passed, "detail": r.detail}
            for r in results
        ],
    }
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)


def validate_next_actions_payload(payload: Dict[str, Any]) -> tuple[bool, str]:
    actions = payload.get("actions")
    generated_at = payload.get("generated_at")

    if not isinstance(generated_at, str) or not generated_at.strip():
        return False, "missing generated_at"

    if not isinstance(actions, list) or len(actions) < 1:
        return False, "actions must be a non-empty list"

    required_fields = ["key", "title", "description", "cta_label", "cta_route"]
    route_patterns = [
        re.compile(r"^/books$"),
        re.compile(r"^/study-plan$"),
        re.compile(r"^/learn-sessions$"),
        re.compile(r"^/mini-set$"),
        re.compile(r"^/exam/stamina$"),
        re.compile(r"^/subject/[^/]+$"),
        re.compile(r"^/subject/[^/]+/quiz$"),
        re.compile(r"^/subject/[^/]+/lesson/[^/]+/learn$"),
        re.compile(r"^/subject/[^/]+/lesson/[^/]+/quiz$"),
    ]

    for idx, action in enumerate(actions[:3]):
        if not isinstance(action, dict):
            return False, f"action[{idx}] must be an object"
        for field in required_fields:
            value = action.get(field)
            if not isinstance(value, str) or not value.strip():
                return False, f"action[{idx}] missing field: {field}"

        route = action.get("cta_route", "")
        if not any(pattern.match(route) for pattern in route_patterns):
            return False, f"action[{idx}] has unroutable cta_route: {route}"

    return True, f"actions={len(actions)}"


def run(base_url: str, include_llm: bool, report_path: Optional[str]) -> int:
    client = HttpClient(base_url)
    results: list[CheckResult] = []

    # 1) Health
    status, health = client.request("GET", "/health")
    add_result(results, "Health", status == 200 and health.get("status") == "healthy", f"HTTP {status}")

    # 2) Register user
    suffix = str(int(time.time()))
    username = f"flow_user_{suffix}"
    register_payload = {
        "name": f"Flow User {suffix}",
        "username": username,
        "password": "Test@12345",
        "current_class": "12th",
        "attempt_number": 1,
        "target_year": "2027",
        "target_score": 620,
        "daily_study_target": 4,
        "preferred_language": "english",
    }
    status, register_data = client.request("POST", "/api/auth/register", payload=register_payload)
    token = get_token(register_data) if status in (200, 201) else None
    add_result(results, "Register", status in (200, 201) and bool(token), f"HTTP {status}")
    if not token:
        write_report(report_path, results)
        return 1

    status, me_data = client.request("GET", "/api/auth/me", token=token)
    me_ok = status == 200 and me_data.get("username") == username
    add_result(results, "Auth me", me_ok, f"HTTP {status}")

    # 3) Baseline dashboard
    status, summary = client.request("GET", "/api/dashboard/summary", token=token)
    today = summary.get("today", {}) if status == 200 else {}
    base_lessons = int(today.get("lessons_completed", 0))
    base_quizzes = int(today.get("quizzes_taken", 0))
    base_xp = int(today.get("xp_earned", 0))
    add_result(results, "Dashboard summary", status == 200, f"HTTP {status}")

    status, next_actions_payload = client.request("GET", "/api/dashboard/next-actions", token=token)
    next_actions_ok, next_actions_detail = validate_next_actions_payload(next_actions_payload)
    add_result(
        results,
        "Dashboard next actions",
        status == 200 and next_actions_ok,
        f"HTTP {status}, {next_actions_detail}",
    )

    # 4) Subjects + lessons
    status, subjects_data = client.request("GET", "/api/subjects", token=token)
    subjects = subjects_data.get("data", []) if status == 200 else []
    subject_name = subjects[0]["name"] if subjects else None
    add_result(results, "Subjects list", status == 200 and bool(subject_name), f"HTTP {status}")
    if not subject_name:
        write_report(report_path, results)
        return 1

    status, lessons_data = client.request("GET", f"/api/subjects/{subject_name}/lessons", token=token)
    lessons = lessons_data.get("lessons", []) if status == 200 else []
    lesson_id = lessons[0]["id"] if lessons else None
    add_result(results, "Lessons list", status == 200 and bool(lesson_id), f"HTTP {status}")
    if not lesson_id:
        write_report(report_path, results)
        return 1

    # 5) Complete lesson
    status, lesson_complete = client.request(
        "POST",
        f"/api/subjects/{subject_name}/lessons/{lesson_id}/complete",
        token=token,
    )
    add_result(results, "Lesson complete", status == 200, f"HTTP {status}")

    status, summary_after_lesson = client.request("GET", "/api/dashboard/summary", token=token)
    today_after_lesson = summary_after_lesson.get("today", {}) if status == 200 else {}
    lessons_after = int(today_after_lesson.get("lessons_completed", 0))
    xp_after = int(today_after_lesson.get("xp_earned", 0))
    add_result(
        results,
        "Lesson increments progress",
        status == 200 and lessons_after >= base_lessons + 1 and xp_after >= base_xp + 50,
        f"lessons={lessons_after}, xp={xp_after}",
    )

    # 5b) Lesson recall -> spaced review loop
    status, recall_data = client.request(
        "POST",
        "/api/retrieval/lesson-recall",
        token=token,
        payload={
            "lesson_id": lesson_id,
            "subject": subject_name,
            "topic": f"{subject_name} lesson {lesson_id}",
            "response_text": "Reviewed key points and common mistakes from this lesson.",
            "self_score": 65,
            "time_taken_sec": 120,
        },
    )
    review_id = recall_data.get("spaced_review_id") if status == 200 else None
    add_result(results, "Lesson recall", status == 200 and bool(review_id), f"HTTP {status}")

    due_before = urllib.parse.quote((datetime.now(UTC) + timedelta(days=2)).isoformat(), safe="")
    status, queue_data = client.request(
        "GET",
        f"/api/retrieval/spaced-queue?limit=20&due_before={due_before}",
        token=token,
    )
    queue_items = queue_data.get("due_items", []) if status == 200 else []
    has_review = bool(review_id) and any(item.get("id") == review_id for item in queue_items)
    add_result(
        results,
        "Lesson recall queued",
        status == 200 and has_review,
        f"HTTP {status}, count={len(queue_items)}",
    )

    # 6) Learn session
    status, session = client.request(
        "POST",
        "/api/learn/sessions",
        token=token,
        payload={"subject": subject_name, "lesson_id": lesson_id},
    )
    session_id = session.get("id") if status == 201 else None
    add_result(results, "Start learn session", status == 201 and bool(session_id), f"HTTP {status}")

    if session_id and include_llm:
        status, msg = client.request(
            "POST",
            f"/api/learn/sessions/{session_id}/messages",
            token=token,
            payload={"content": "Explain the key idea in two sentences."},
        )
        msg_ok = status == 200 and isinstance(msg.get("content"), str)
        add_result(results, "Learn message", msg_ok, f"HTTP {status}")

    if session_id:
        status, ended = client.request(
            "PATCH",
            f"/api/learn/sessions/{session_id}/end",
            token=token,
        )
        add_result(results, "End learn session", status == 200 and bool(ended.get("ended_at")), f"HTTP {status}")

    # 7) Quiz
    status, quiz_data = client.request(
        "POST",
        "/api/quiz",
        token=token,
        payload={"subject": subject_name, "difficulty": "easy", "question_count": 3},
    )
    quiz = quiz_data.get("quiz", {}) if status == 201 else {}
    questions = quiz_data.get("questions", []) if status == 201 else []
    quiz_id = quiz.get("id")
    question_id = questions[0]["id"] if questions else None
    add_result(results, "Start quiz", status == 201 and bool(quiz_id) and bool(question_id), f"HTTP {status}")

    if quiz_id and question_id:
        options = questions[0].get("options", []) if questions else []
        user_answer = options[0] if options else "A"
        status, _ = client.request(
            "POST",
            f"/api/quiz/{quiz_id}/answers",
            token=token,
            payload={"question_id": question_id, "user_answer": user_answer, "confidence_level": 3},
        )
        add_result(results, "Submit quiz answer", status == 200, f"HTTP {status}")

        status, finish = client.request(
            "POST",
            f"/api/quiz/{quiz_id}/finish",
            token=token,
        )
        summary = finish.get("summary", {}) if status == 200 else {}
        add_result(results, "Finish quiz", status == 200 and bool(summary), f"HTTP {status}")

    # 8) Progress after quiz
    status, summary_after_quiz = client.request("GET", "/api/dashboard/summary", token=token)
    today_after_quiz = summary_after_quiz.get("today", {}) if status == 200 else {}
    quizzes_after = int(today_after_quiz.get("quizzes_taken", 0))
    add_result(
        results,
        "Quiz increments progress",
        status == 200 and quizzes_after >= base_quizzes + 1,
        f"quizzes={quizzes_after}",
    )

    # 9) Mastery
    status, mastery_data = client.request(
        "GET",
        f"/api/insights/mastery?subject={subject_name}",
        token=token,
    )
    mastery_rows = mastery_data.get("mastery", []) if status == 200 else []
    add_result(results, "Mastery updated", status == 200 and len(mastery_rows) >= 1, f"HTTP {status}")

    # 10) Planner
    status, plan_data = client.request(
        "POST",
        "/api/planner/generate",
        token=token,
        payload={"available_minutes": 60},
    )
    plan_date = plan_data.get("date") if status == 200 else None
    plan_tasks = plan_data.get("tasks", []) if status == 200 else []
    add_result(results, "Planner generate", status == 200 and bool(plan_tasks), f"HTTP {status}")

    if plan_date:
        status, daily_data = client.request(
            "GET",
            f"/api/planner/daily?date={plan_date}",
            token=token,
        )
        daily_tasks = daily_data.get("tasks", []) if status == 200 else []
        add_result(results, "Planner daily", status == 200 and len(daily_tasks) >= 1, f"HTTP {status}")

    if plan_tasks:
        first_task_id = plan_tasks[0]["id"]
        status, update_data = client.request(
            "PATCH",
            f"/api/planner/tasks/{first_task_id}",
            token=token,
            payload={"status": "completed"},
        )
        updated_status = ((update_data.get("task") or {}).get("status")) if status == 200 else None
        add_result(
            results,
            "Planner task complete",
            status == 200 and updated_status == "completed",
            f"HTTP {status}",
        )

    # 10d) Exam stamina drill
    status, stamina_start = client.request(
        "POST",
        "/api/exam/stamina/sessions",
        token=token,
        payload={
            "mode": "mixed",
            "duration_minutes": 12,
            "planned_questions": 12,
            "block_count": 2,
        },
    )
    stamina_session_id = stamina_start.get("session_id") if status == 200 else None
    add_result(
        results,
        "Stamina start",
        status == 200 and bool(stamina_session_id),
        f"HTTP {status}",
    )

    if stamina_session_id:
        status, stamina_finish = client.request(
            "POST",
            f"/api/exam/stamina/sessions/{stamina_session_id}/finish",
            token=token,
            payload={
                "block_results": [
                    {
                        "block_no": 1,
                        "attempted_questions": 6,
                        "correct_answers": 5,
                        "elapsed_sec": 360,
                        "dominant_error": "misread",
                    },
                    {
                        "block_no": 2,
                        "attempted_questions": 6,
                        "correct_answers": 3,
                        "elapsed_sec": 360,
                        "dominant_error": "time_pressure",
                    },
                ]
            },
        )
        fatigue_value = stamina_finish.get("fatigue_accuracy_dip") if status == 200 else None
        add_result(
            results,
            "Stamina finish",
            status == 200 and isinstance(fatigue_value, (int, float)),
            f"HTTP {status}",
        )

    # 10e) Sync journal batch + idempotency + status
    sync_ops = [
        {
            "operation_type": "event",
            "entity_type": "planner_task",
            "entity_id": str(plan_tasks[0]["id"]) if plan_tasks else None,
            "payload": {"status": "completed"},
            "idempotency_key": f"sync-{suffix}-1",
        },
        {
            "operation_type": "event",
            "entity_type": "spaced_review",
            "entity_id": str(review_id) if review_id else None,
            "payload": {"result": "queued"},
            "idempotency_key": f"sync-{suffix}-2",
        },
    ]
    status, sync_batch = client.request(
        "POST",
        "/api/sync/batch",
        token=token,
        payload={"operations": sync_ops},
    )
    accepted_count = int(sync_batch.get("accepted_count", 0)) if status == 200 else 0
    failed_count = int(sync_batch.get("failed_count", 0)) if status == 200 else 0
    add_result(
        results,
        "Sync batch",
        status == 200 and accepted_count >= 2 and failed_count == 0,
        f"HTTP {status}, accepted={accepted_count}, failed={failed_count}",
    )

    status, sync_duplicate = client.request(
        "POST",
        "/api/sync/batch",
        token=token,
        payload={"operations": [sync_ops[0]]},
    )
    duplicate_count = int(sync_duplicate.get("duplicate_count", 0)) if status == 200 else 0
    add_result(
        results,
        "Sync idempotency",
        status == 200 and duplicate_count >= 1,
        f"HTTP {status}, duplicate={duplicate_count}",
    )

    status, sync_status = client.request("GET", "/api/sync/status", token=token)
    synced_count = int(sync_status.get("synced_count", 0)) if status == 200 else 0
    backlog_count = int(sync_status.get("backlog_count", 0)) if status == 200 else -1
    add_result(
        results,
        "Sync status",
        status == 200 and synced_count >= 2 and backlog_count == 0,
        f"HTTP {status}, synced={synced_count}, backlog={backlog_count}",
    )

    # 10b) Strategist for tomorrow
    tomorrow = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
    status, strategist_data = client.request(
        "POST",
        "/api/planner/strategist",
        token=token,
        payload={"date": tomorrow},
    )
    strategist_tasks = strategist_data.get("tasks", []) if status == 200 else []
    add_result(
        results,
        "Strategist generate",
        status == 200 and len(strategist_tasks) >= 1,
        f"HTTP {status}",
    )

    status, strategist_daily = client.request(
        "GET",
        f"/api/planner/daily?date={tomorrow}",
        token=token,
    )
    strategist_daily_tasks = strategist_daily.get("tasks", []) if status == 200 else []
    add_result(
        results,
        "Strategist daily",
        status == 200 and len(strategist_daily_tasks) >= 1,
        f"HTTP {status}",
    )

    # 10c) Auto-generation on daily fetch for day after tomorrow
    day_after = (datetime.now(UTC).date() + timedelta(days=2)).isoformat()
    status, auto_daily = client.request(
        "GET",
        f"/api/planner/daily?date={day_after}",
        token=token,
    )
    auto_daily_tasks = auto_daily.get("tasks", []) if status == 200 else []
    add_result(
        results,
        "Planner daily autogenerate",
        status == 200 and len(auto_daily_tasks) >= 1,
        f"HTTP {status}",
    )

    # 11) Progress and gamification snapshots
    status, daily_progress = client.request("GET", "/api/progress/daily?days=1", token=token)
    day_rows = daily_progress.get("days", []) if status == 200 else []
    add_result(results, "Daily progress", status == 200 and len(day_rows) == 1, f"HTTP {status}")

    status, gamification = client.request("GET", "/api/progress/gamification", token=token)
    total_xp = gamification.get("total_xp") if status == 200 else None
    add_result(
        results,
        "Gamification snapshot",
        status == 200 and isinstance(total_xp, int),
        f"HTTP {status}",
    )

    failures = [r for r in results if not r.passed]
    print("\nSummary:")
    print(f"  Total checks: {len(results)}")
    print(f"  Passed: {len(results) - len(failures)}")
    print(f"  Failed: {len(failures)}")

    if failures:
        print("\nFailed checks:")
        for result in failures:
            print(f"  - {result.name}: {result.detail}")
        write_report(report_path, results)
        return 1

    print("\nCore learning flow test passed.")
    write_report(report_path, results)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify core learning loop end-to-end flow")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--profile", default="core", help="Reserved for compatibility")
    parser.add_argument("--report-json", default=None, help="Optional JSON report output path")
    parser.add_argument("--include-llm", action="store_true", help="Include LLM message step")
    args = parser.parse_args()

    return run(args.base_url, args.include_llm, args.report_json)


if __name__ == "__main__":
    sys.exit(main())
