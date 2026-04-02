#!/usr/bin/env python3
"""Smoke test for retrieval, mistake-card, and planner backlog implementation."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any


class HttpClient:
    def __init__(self, base_url: str, timeout: int = 20):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
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


def check(name: str, ok: bool, detail: str) -> bool:
    marker = "PASS" if ok else "FAIL"
    print(f"[{marker}] {name}: {detail}")
    return ok


def run(base_url: str) -> int:
    client = HttpClient(base_url)
    all_ok = True

    # health
    status, _ = client.request("GET", "/health")
    all_ok &= check("Health", status == 200, f"HTTP {status}")

    # register unique user
    suffix = str(int(time.time()))
    username = f"learn_{suffix}"
    register_payload = {
        "name": f"Learning User {suffix}",
        "username": username,
        "password": "Test@12345",
        "current_class": "12th",
        "attempt_number": 1,
        "target_year": "2027",
        "target_score": 620,
        "daily_study_target": 4,
        "preferred_language": "english",
    }
    status, reg_data = client.request("POST", "/api/auth/register", payload=register_payload)
    token = reg_data.get("token") if status in (200, 201) else None
    all_ok &= check("Register", status in (200, 201) and bool(token), f"HTTP {status}")
    if not token:
        return 1

    # start quiz
    status, quiz_data = client.request(
        "POST",
        "/api/quiz",
        token=token,
        payload={"subject": "biology", "difficulty": "easy", "question_count": 3},
    )
    questions = quiz_data.get("questions", []) if status == 201 else []
    quiz_id = (quiz_data.get("quiz") or {}).get("id") if status == 201 else None
    first_qid = questions[0]["id"] if questions else None
    all_ok &= check("Start quiz", status == 201 and bool(quiz_id) and bool(first_qid), f"HTTP {status}")
    if not quiz_id or not first_qid:
        return 1

    # submit wrong answer to generate mistake card
    status, answer_data = client.request(
        "POST",
        f"/api/quiz/{quiz_id}/answers",
        token=token,
        payload={"question_id": first_qid, "user_answer": "not_an_option", "confidence_level": 5},
    )
    is_correct = ((answer_data.get("result") or {}).get("is_correct")) if status == 200 else True
    all_ok &= check("Submit answer", status == 200 and is_correct is False, f"HTTP {status}")

    # validate mistake cards
    status, cards_data = client.request("GET", "/api/errors/mistake-cards?status=active&limit=20", token=token)
    cards = cards_data.get("cards", []) if status == 200 else []
    all_ok &= check("Mistake cards listed", status == 200 and len(cards) >= 1, f"HTTP {status}, count={len(cards)}")
    card_id = cards[0]["id"] if cards else None

    # submit lesson recall
    status, recall_data = client.request(
        "POST",
        "/api/retrieval/lesson-recall",
        token=token,
        payload={
            "lesson_id": 1,
            "subject": "biology",
            "topic": "cell biology basics",
            "response_text": "Cell has nucleus, mitochondria, membrane.",
            "self_score": 62,
            "time_taken_sec": 95,
        },
    )
    review_id = recall_data.get("spaced_review_id") if status == 200 else None
    all_ok &= check("Lesson recall", status == 200 and bool(review_id), f"HTTP {status}")

    # fetch spaced queue with future cutoff
    cutoff = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    encoded_cutoff = urllib.parse.quote(cutoff, safe="")
    status, queue_data = client.request(
        "GET",
        f"/api/retrieval/spaced-queue?limit=20&due_before={encoded_cutoff}",
        token=token,
    )
    due_items = queue_data.get("due_items", []) if status == 200 else []
    all_ok &= check("Spaced queue", status == 200 and len(due_items) >= 1, f"HTTP {status}, count={len(due_items)}")

    queue_id = due_items[0]["id"] if due_items else None
    if queue_id:
        status, complete_data = client.request(
            "POST",
            f"/api/retrieval/spaced-queue/{queue_id}/complete",
            token=token,
            payload={"result": "correct", "confidence_level": 4},
        )
        all_ok &= check("Complete spaced review", status == 200 and bool(complete_data.get("next_due_at")), f"HTTP {status}")

    # generate planner tasks (BL-09)
    status, plan_data = client.request(
        "POST",
        "/api/planner/generate",
        token=token,
        payload={"available_minutes": 90},
    )
    planner_tasks = plan_data.get("tasks", []) if status == 200 else []
    planner_date = plan_data.get("date") if status == 200 else None
    all_ok &= check(
        "Generate planner",
        status == 200 and len(planner_tasks) >= 2 and bool(planner_date),
        f"HTTP {status}, count={len(planner_tasks)}",
    )

    # fetch planner daily view (BL-10 read path)
    if planner_date:
        status, daily_plan = client.request(
            "GET",
            f"/api/planner/daily?date={planner_date}",
            token=token,
        )
        daily_tasks = daily_plan.get("tasks", []) if status == 200 else []
        all_ok &= check(
            "Planner daily",
            status == 200 and len(daily_tasks) >= 1,
            f"HTTP {status}, count={len(daily_tasks)}",
        )

    # update planner task status: completed
    first_task_id = planner_tasks[0]["id"] if planner_tasks else None
    if first_task_id:
        status, task_update = client.request(
            "PATCH",
            f"/api/planner/tasks/{first_task_id}",
            token=token,
            payload={"status": "completed"},
        )
        updated_status = ((task_update.get("task") or {}).get("status")) if status == 200 else None
        all_ok &= check(
            "Planner task complete",
            status == 200 and updated_status == "completed",
            f"HTTP {status}",
        )

    # update planner task status: skipped and auto-reschedule
    second_task_id = planner_tasks[1]["id"] if len(planner_tasks) > 1 else None
    if second_task_id:
        status, skipped_update = client.request(
            "PATCH",
            f"/api/planner/tasks/{second_task_id}",
            token=token,
            payload={"status": "skipped"},
        )
        skipped_status = ((skipped_update.get("task") or {}).get("status")) if status == 200 else None
        has_rescheduled = bool(skipped_update.get("rescheduled_task")) if status == 200 else False
        all_ok &= check(
            "Planner task skip/reschedule",
            status == 200 and skipped_status == "skipped" and has_rescheduled,
            f"HTTP {status}",
        )

    # BL-07: mastery labels should be present and risk topics should be ranked
    status, mastery_data = client.request("GET", "/api/insights/mastery?subject=biology", token=token)
    mastery_rows = mastery_data.get("mastery", []) if status == 200 else []
    has_state_label = bool(mastery_rows) and isinstance(mastery_rows[0].get("state_label"), str)
    all_ok &= check(
        "Mastery with state labels",
        status == 200 and has_state_label,
        f"HTTP {status}, count={len(mastery_rows)}",
    )

    status, risk_data = client.request("GET", "/api/insights/risk-topics?subject=biology&limit=10", token=token)
    risk_rows = risk_data.get("risk_topics", []) if status == 200 else []
    has_risk_score = bool(risk_rows) and isinstance(risk_rows[0].get("risk_score"), (int, float))
    all_ok &= check(
        "Risk topics",
        status == 200 and has_risk_score,
        f"HTTP {status}, count={len(risk_rows)}",
    )

    # BL-04: confidence calibration insights
    status, calibration_data = client.request(
        "GET",
        "/api/insights/calibration?days=30",
        token=token,
    )
    sample_count = calibration_data.get("sample_count") if status == 200 else 0
    mean_confidence = calibration_data.get("mean_confidence") if status == 200 else None
    confidence_gap = calibration_data.get("confidence_accuracy_gap") if status == 200 else None
    has_calibration_metrics = (
        isinstance(sample_count, int)
        and sample_count >= 1
        and isinstance(mean_confidence, (int, float))
        and isinstance(confidence_gap, (int, float))
    )
    all_ok &= check(
        "Calibration insights",
        status == 200 and has_calibration_metrics,
        f"HTTP {status}, samples={sample_count}",
    )

    # BL-08: weekly report JSON + markdown export
    status, weekly_report_json = client.request(
        "GET",
        "/api/insights/weekly-report?days=7&export_format=json",
        token=token,
    )
    weekly_summary = weekly_report_json.get("summary", {}) if status == 200 else {}
    has_weekly_metrics = (
        isinstance(weekly_summary.get("retention_score"), (int, float))
        and isinstance(weekly_summary.get("accuracy_percent"), (int, float))
        and isinstance(weekly_summary.get("speed_qph"), (int, float))
        and isinstance(weekly_summary.get("consistency_score"), (int, float))
    )
    all_ok &= check(
        "Weekly report json",
        status == 200 and has_weekly_metrics,
        f"HTTP {status}",
    )

    status, weekly_report_md = client.request(
        "GET",
        "/api/insights/weekly-report?days=7&export_format=markdown",
        token=token,
    )
    export_obj = weekly_report_md.get("export", {}) if status == 200 else {}
    markdown_content = export_obj.get("content") if isinstance(export_obj, dict) else ""
    has_markdown_header = isinstance(markdown_content, str) and markdown_content.startswith("# APXMIND Weekly Report")
    all_ok &= check(
        "Weekly report markdown",
        status == 200 and has_markdown_header,
        f"HTTP {status}",
    )

    # patch mistake card
    if card_id:
        status, patch_data = client.request(
            "PATCH",
            f"/api/errors/mistake-cards/{card_id}",
            token=token,
            payload={"status": "resolved"},
        )
        patched_status = ((patch_data.get("card") or {}).get("status")) if status == 200 else None
        all_ok &= check("Update mistake card", status == 200 and patched_status == "resolved", f"HTTP {status}")

    if all_ok:
        print("\nLearning backlog smoke test passed.")
        return 0

    print("\nLearning backlog smoke test failed.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify learning backlog API slice")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    args = parser.parse_args()
    return run(args.base_url)


if __name__ == "__main__":
    sys.exit(main())
