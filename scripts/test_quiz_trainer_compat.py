#!/usr/bin/env python3
"""Smoke test legacy trainer quiz answer compatibility.

Validates that when correct_answer is a letter (A-D), submitting the option text
is still evaluated correctly by /api/trainer/submit-answer.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


class HttpClient:
    def __init__(self, base_url: str, timeout: int = 20):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            url=url,
            method=method,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, (json.loads(body) if body else {})
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

    status, health = client.request("GET", "/health")
    all_ok &= check("Health", status == 200 and health.get("status") == "healthy", f"HTTP {status}")

    status, quiz_res = client.request(
        "POST",
        "/api/trainer/generate-quiz",
        payload={
            "subject": "biology",
            "difficulty": "easy",
            "question_count": 3,
            "topics": [],
        },
    )
    quiz = quiz_res.get("quiz", {}) if status == 200 else {}
    questions = quiz.get("questions", []) if isinstance(quiz, dict) else []
    all_ok &= check("Generate trainer quiz", status == 200 and len(questions) >= 1, f"HTTP {status}")
    if not questions:
        return 1

    q0 = questions[0]
    options = q0.get("options", [])
    correct_answer = q0.get("correct_answer", "")
    correct_letter = str(correct_answer).strip().upper()

    if len(correct_letter) == 1 and correct_letter in {"A", "B", "C", "D"} and options:
        selected_text = options[ord(correct_letter) - ord("A")]
    else:
        selected_text = str(correct_answer)

    status, eval_res = client.request(
        "POST",
        "/api/trainer/submit-answer",
        payload={
            "quiz_id": quiz.get("quiz_id", "compat-test"),
            "question_id": q0.get("id", 1),
            "user_answer": selected_text,
            "options": options,
            "correct_answer": correct_answer,
            "question_text": q0.get("question", ""),
        },
    )

    evaluation = eval_res.get("evaluation", {}) if status == 200 else {}
    is_correct = bool(evaluation.get("correct")) if isinstance(evaluation, dict) else False
    returned_correct = str(evaluation.get("correct_answer", "")) if isinstance(evaluation, dict) else ""

    all_ok &= check(
        "Submit trainer answer using option text",
        status == 200 and is_correct,
        f"HTTP {status}, returned_correct={returned_correct}",
    )

    if all_ok:
        print("\nTrainer quiz compatibility smoke test passed.")
        return 0

    print("\nTrainer quiz compatibility smoke test failed.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify trainer answer compatibility")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    args = parser.parse_args()
    return run(args.base_url)


if __name__ == "__main__":
    sys.exit(main())
