"""
Comprehensive API smoke test runner for APXMIND.

Usage examples:
  python scripts/test_full_api.py
  python scripts/test_full_api.py --profile full --include-llm --include-ws
  python scripts/test_full_api.py --base-url http://127.0.0.1:8000 --report-json artifacts/api-report.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class Result:
    method: str
    path: str
    status: Any
    reason: str = ""


class ApiSmokeRunner:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.base_url = args.base_url.rstrip("/")
        self.results: list[Result] = []
        self.token: str = ""
        self.user_name: str = f"smoke_{uuid.uuid4().hex[:8]}"
        self.password: str = "test1234"

    def add(self, method: str, path: str, status: Any, reason: str = "") -> None:
        self.results.append(Result(method=method, path=path, status=status, reason=reason))

    def request(
        self,
        method: str,
        path: str,
        data: Any = None,
        token: str | None = None,
        timeout: int | None = None,
        expect_json: bool = True,
    ) -> tuple[Any, Any, str, str | None]:
        headers: dict[str, str] = {}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(
            f"{self.base_url}{path}", data=body, headers=headers, method=method
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout or self.args.timeout) as response:
                content_type = response.headers.get("content-type", "")
                raw = response.read()
                payload = None
                if expect_json and "application/json" in content_type:
                    try:
                        payload = json.loads(raw.decode("utf-8")) if raw else None
                    except Exception:
                        payload = None
                return response.status, payload, content_type, None
        except urllib.error.HTTPError as exc:
            txt = exc.read().decode("utf-8")
            payload = None
            try:
                payload = json.loads(txt) if txt else None
            except Exception:
                payload = {"raw": txt}
            return exc.code, payload, "", None
        except Exception as exc:
            return "FAIL", None, "", str(exc)

    def do(
        self,
        method: str,
        path: str,
        data: Any = None,
        token: str | None = None,
        timeout: int | None = None,
        expect_json: bool = True,
    ) -> tuple[Any, Any, str, str | None]:
        status, payload, content_type, error = self.request(
            method=method,
            path=path,
            data=data,
            token=token,
            timeout=timeout,
            expect_json=expect_json,
        )
        self.add(method, path, status, error or "")
        return status, payload, content_type, error

    def wait_for_health(self) -> bool:
        for _ in range(self.args.health_retries):
            status, _, _, _ = self.request("GET", "/health", timeout=self.args.health_timeout)
            if status == 200:
                return True
            time.sleep(self.args.health_interval)
        return False

    def maybe_seed_subjects(self) -> None:
        if not self.args.seed_if_empty:
            return
        status, body, _, _ = self.request("GET", "/api/subjects")
        if status == 200 and isinstance(body, dict) and body.get("count", 0) > 0:
            return

        cmd = [sys.executable, "-m", "scripts.seed_data"]
        subprocess.run(cmd, check=True, cwd=str(PROJECT_ROOT))

    async def ensure_recommendation_for_user(self, user_id: int) -> int | None:
        from sqlalchemy import select
        from src.apxmind.core.config import Settings
        from src.apxmind.db.models import LearningRecommendation
        from src.apxmind.db import session as db_session

        settings = Settings()
        db_session.init_db_engine(settings)

        if db_session._async_session_factory is None:
            return None

        async with db_session._async_session_factory() as session:
            existing = await session.execute(
                select(LearningRecommendation)
                .where(LearningRecommendation.user_id == user_id)
                .order_by(LearningRecommendation.id.desc())
                .limit(1)
            )
            rec = existing.scalar_one_or_none()
            if rec is None:
                rec = LearningRecommendation(
                    user_id=user_id,
                    rec_type="revision",
                    subject="biology",
                    topic="cell_structure",
                    title="Revise Cell Structure",
                    reason="Created by smoke test fixture",
                    priority_score=0.900,
                    status="active",
                )
                session.add(rec)
                await session.commit()
                await session.refresh(rec)
            return rec.id

    def auth_bootstrap(self) -> int | None:
        register_payload = {
            "name": self.user_name,
            "username": self.user_name,
            "password": self.password,
            "preferred_language": "english",
            "current_class": "12th",
        }

        status, body, _, _ = self.do("POST", "/api/auth/register", register_payload)
        if isinstance(body, dict) and body.get("token"):
            self.token = body["token"]

        self.do("POST", "/api/auth/login", {"name": self.user_name, "password": self.password})

        if not self.token:
            status, body, _, _ = self.request(
                "POST", "/api/auth/login", {"name": self.user_name, "password": self.password}
            )
            if isinstance(body, dict):
                self.token = body.get("token", "")

        _, me, _, _ = self.do("GET", "/api/auth/me", token=self.token)
        return me.get("id") if isinstance(me, dict) else None

    def check_system(self) -> None:
        self.do("GET", "/health")
        self.do("GET", "/api")
        self.do("GET", "/openapi.json")
        self.do("GET", "/docs", expect_json=False)

    def check_subjects_books(self) -> None:
        status, subjects, _, _ = self.do("GET", "/api/subjects", token=self.token)
        subject_name = "biology"
        lesson_id = None

        if status == 200 and isinstance(subjects, dict) and subjects.get("data"):
            subject_name = (subjects["data"][0].get("name") or "biology").lower()

        _, lessons, _, _ = self.do("GET", f"/api/subjects/{subject_name}/lessons", token=self.token)
        if isinstance(lessons, dict) and lessons.get("lessons"):
            lesson_id = lessons["lessons"][0].get("id")

        if lesson_id is not None:
            self.do(
                "POST",
                f"/api/subjects/{subject_name}/lessons/{lesson_id}/complete",
                token=self.token,
            )
        else:
            self.add(
                "POST",
                "/api/subjects/{subject_name}/lessons/{lesson_id}/complete",
                "SKIP",
                "no lessons in DB",
            )

        pdf_rel = None
        books_root = PROJECT_ROOT / "data" / "raw" / "NCRTBooks"
        if books_root.exists():
            for root, _, files in os.walk(books_root):
                for file_name in files:
                    if file_name.lower().endswith(".pdf"):
                        full = Path(root) / file_name
                        pdf_rel = str(full.relative_to(books_root)).replace("\\", "/")
                        break
                if pdf_rel:
                    break

        if pdf_rel:
            self.do(
                "GET",
                "/api/books/" + urllib.parse.quote(pdf_rel, safe="/"),
                token=self.token,
                expect_json=False,
            )
        else:
            self.add("GET", "/api/books/{file_path}", "SKIP", "no pdf found")

    def check_dashboard_progress(self) -> None:
        self.do("GET", "/api/dashboard/summary", token=self.token)
        self.do("GET", "/api/progress/daily", token=self.token)
        self.do("GET", "/api/progress/gamification", token=self.token)
        self.do(
            "POST",
            "/api/progress/study-minutes",
            {"minutes": 10, "subject": "biology"},
            token=self.token,
        )

    def check_quiz_v2(self) -> None:
        _, quiz_start, _, _ = self.do(
            "POST",
            "/api/quiz",
            {"subject": "biology", "difficulty": "easy", "question_count": 3},
            token=self.token,
            timeout=120,
        )

        quiz_id = None
        question_id = None
        if isinstance(quiz_start, dict):
            quiz_id = (quiz_start.get("quiz") or {}).get("id")
            questions = quiz_start.get("questions") or []
            if questions:
                question_id = questions[0].get("id")

        self.do("GET", "/api/quiz", token=self.token)

        if not quiz_id:
            for method, path in [
                ("GET", "/api/quiz/{quiz_id}"),
                ("GET", "/api/quiz/{quiz_id}/questions"),
                ("POST", "/api/quiz/{quiz_id}/answers"),
                ("PUT", "/api/quiz/{quiz_id}/answers/{question_id}"),
                ("GET", "/api/quiz/{quiz_id}/results"),
                ("POST", "/api/quiz/{quiz_id}/finish"),
                ("DELETE", "/api/quiz/{quiz_id}"),
                ("PATCH", "/api/quiz/{quiz_id}/abandon"),
            ]:
                self.add(method, path, "SKIP", "quiz creation failed")
            return

        self.do("GET", f"/api/quiz/{quiz_id}", token=self.token)
        self.do("GET", f"/api/quiz/{quiz_id}/questions", token=self.token)

        if question_id is not None:
            self.do(
                "POST",
                f"/api/quiz/{quiz_id}/answers",
                {"question_id": question_id, "user_answer": "A"},
                token=self.token,
            )
            self.do(
                "PUT",
                f"/api/quiz/{quiz_id}/answers/{question_id}",
                {"user_answer": "B"},
                token=self.token,
            )
        else:
            self.add("POST", "/api/quiz/{quiz_id}/answers", "SKIP", "no question id")
            self.add(
                "PUT",
                "/api/quiz/{quiz_id}/answers/{question_id}",
                "SKIP",
                "no question id",
            )

        self.do("GET", f"/api/quiz/{quiz_id}/results", token=self.token)
        self.do("POST", f"/api/quiz/{quiz_id}/finish", token=self.token)
        self.do("DELETE", f"/api/quiz/{quiz_id}", token=self.token)

        _, second_quiz, _, _ = self.do(
            "POST",
            "/api/quiz",
            {"subject": "biology", "difficulty": "easy", "question_count": 2},
            token=self.token,
            timeout=120,
        )
        second_quiz_id = None
        if isinstance(second_quiz, dict):
            second_quiz_id = (second_quiz.get("quiz") or {}).get("id")

        if second_quiz_id:
            self.do("PATCH", f"/api/quiz/{second_quiz_id}/abandon", token=self.token)
            self.do("DELETE", f"/api/quiz/{second_quiz_id}", token=self.token)
        else:
            self.add("PATCH", "/api/quiz/{quiz_id}/abandon", "SKIP", "second quiz creation failed")

    def check_learn(self) -> None:
        _, session, _, _ = self.do(
            "POST", "/api/learn/sessions", {"subject": "biology"}, token=self.token
        )
        self.do("GET", "/api/learn/sessions", token=self.token)

        session_id = session.get("id") if isinstance(session, dict) else None
        if not session_id:
            for method, path in [
                ("POST", "/api/learn/sessions/{session_id}/messages"),
                ("GET", "/api/learn/sessions/{session_id}"),
                ("GET", "/api/learn/sessions/{session_id}/messages"),
                ("DELETE", "/api/learn/sessions/{session_id}/messages/{msg_id}"),
                ("DELETE", "/api/learn/sessions/{session_id}/messages"),
                ("PATCH", "/api/learn/sessions/{session_id}/end"),
                ("DELETE", "/api/learn/sessions/{session_id}"),
            ]:
                self.add(method, path, "SKIP", "session creation failed")
            return

        _, msg, _, _ = self.do(
            "POST",
            f"/api/learn/sessions/{session_id}/messages",
            {"content": "test message"},
            token=self.token,
            timeout=120,
        )
        msg_id = msg.get("id") if isinstance(msg, dict) else None

        self.do("GET", f"/api/learn/sessions/{session_id}", token=self.token)
        self.do("GET", f"/api/learn/sessions/{session_id}/messages", token=self.token)

        if msg_id is not None:
            self.do("DELETE", f"/api/learn/sessions/{session_id}/messages/{msg_id}", token=self.token)
        else:
            self.add(
                "DELETE",
                "/api/learn/sessions/{session_id}/messages/{msg_id}",
                "SKIP",
                "no message id",
            )

        self.do("DELETE", f"/api/learn/sessions/{session_id}/messages", token=self.token)
        self.do("PATCH", f"/api/learn/sessions/{session_id}/end", token=self.token)
        self.do("DELETE", f"/api/learn/sessions/{session_id}", token=self.token)

    def check_library(self) -> None:
        _, bookmark, _, _ = self.do(
            "POST",
            "/api/library/bookmarks",
            {"title": "bookmark test", "subject": "biology", "path": "/tmp"},
            token=self.token,
        )
        self.do("GET", "/api/library/bookmarks", token=self.token)

        bookmark_id = bookmark.get("id") if isinstance(bookmark, dict) else None
        if bookmark_id:
            self.do("GET", f"/api/library/bookmarks/{bookmark_id}", token=self.token)
            self.do(
                "PATCH",
                f"/api/library/bookmarks/{bookmark_id}",
                {"title": "bookmark test 2"},
                token=self.token,
            )
            self.do("DELETE", f"/api/library/bookmarks/{bookmark_id}", token=self.token)
        else:
            for method, path in [
                ("GET", "/api/library/bookmarks/{bookmark_id}"),
                ("PATCH", "/api/library/bookmarks/{bookmark_id}"),
                ("DELETE", "/api/library/bookmarks/{bookmark_id}"),
            ]:
                self.add(method, path, "SKIP", "bookmark creation failed")

        self.do("DELETE", "/api/library/bookmarks", token=self.token)

        _, note, _, _ = self.do(
            "POST",
            "/api/library/notes",
            {"title": "note test", "content": "abc", "subject": "biology"},
            token=self.token,
        )
        self.do("GET", "/api/library/notes", token=self.token)

        note_id = note.get("id") if isinstance(note, dict) else None
        if note_id:
            self.do("GET", f"/api/library/notes/{note_id}", token=self.token)
            self.do(
                "PUT",
                f"/api/library/notes/{note_id}",
                {"title": "note test updated", "content": "xyz"},
                token=self.token,
            )
            self.do("DELETE", "/api/library/notes", [note_id], token=self.token)
        else:
            for method, path in [
                ("GET", "/api/library/notes/{note_id}"),
                ("PUT", "/api/library/notes/{note_id}"),
                ("DELETE", "/api/library/notes"),
            ]:
                self.add(method, path, "SKIP", "note creation failed")

    def check_profile_and_achievements(self) -> None:
        self.do("GET", "/api/achievements", token=self.token)
        status, achievements, _, _ = self.request("GET", "/api/achievements", token=self.token)
        self.do("GET", "/api/achievements/earned", token=self.token)

        badge_id = None
        if status == 200 and isinstance(achievements, dict) and achievements.get("badges"):
            badge_id = achievements["badges"][0].get("id")

        if badge_id:
            self.do("GET", f"/api/achievements/{badge_id}", token=self.token)
        else:
            self.add("GET", "/api/achievements/{badge_id}", "SKIP", "no badges available")

        self.do("GET", "/api/profile/subjects", token=self.token)
        self.do(
            "PUT",
            "/api/profile/subjects/biology",
            {"strength": "weak", "priority_rank": 1},
            token=self.token,
        )
        self.do("DELETE", "/api/profile/subjects/biology", token=self.token)

    def check_recommendations_and_insights(self, user_id: int | None) -> None:
        rec_id = None
        if self.args.ensure_recommendation and user_id is not None:
            try:
                rec_id = asyncio.run(self.ensure_recommendation_for_user(user_id))
            except Exception as exc:
                self.add("FIXTURE", "/api/recommendations", "SKIP", f"fixture failed: {exc}")

        _, recs, _, _ = self.do("GET", "/api/recommendations", token=self.token)
        if rec_id is None and isinstance(recs, dict) and recs.get("recommendations"):
            rec_id = recs["recommendations"][0].get("id")

        if rec_id is not None:
            self.do(
                "PATCH",
                f"/api/recommendations/{rec_id}",
                {"status": "accepted"},
                token=self.token,
            )
            self.do("DELETE", f"/api/recommendations/{rec_id}", token=self.token)
        else:
            self.add("PATCH", "/api/recommendations/{rec_id}", "SKIP", "no recommendation rows")
            self.add("DELETE", "/api/recommendations/{rec_id}", "SKIP", "no recommendation rows")

        self.do("GET", "/api/insights/mastery", token=self.token)
        self.do("GET", "/api/insights/mastery/biology", token=self.token)
        self.do("GET", "/api/insights/readiness", token=self.token)
        self.do("GET", "/api/insights/habits", token=self.token)

    def check_llm_endpoints(self) -> None:
        self.do(
            "POST",
            "/api/query",
            {"query": "What is mitochondria?", "subject": "biology"},
            token=self.token,
            timeout=120,
        )

        _, trainer_quiz, _, _ = self.do(
            "POST",
            "/api/trainer/generate-quiz",
            {"subject": "biology", "difficulty": "easy", "question_count": 2, "topics": []},
            token=self.token,
            timeout=120,
        )

        if isinstance(trainer_quiz, dict) and trainer_quiz.get("quiz") and trainer_quiz["quiz"].get("questions"):
            question = trainer_quiz["quiz"]["questions"][0]
            self.do(
                "POST",
                "/api/trainer/submit-answer",
                {
                    "quiz_id": trainer_quiz["quiz"].get("quiz_id", "x"),
                    "question_id": question.get("id", 1),
                    "user_answer": question.get("correct_answer", "A"),
                    "question_text": question.get("question", ""),
                    "correct_answer": question.get("correct_answer", "A"),
                },
                token=self.token,
                timeout=120,
            )
        else:
            self.add("POST", "/api/trainer/submit-answer", "SKIP", "trainer quiz not generated")

    def check_sse(self) -> None:
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/events/stream",
                headers={"Authorization": f"Bearer {self.token}"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=self.args.timeout) as response:
                first_line = response.readline().decode("utf-8").strip()
                self.add("GET", "/api/events/stream", response.status, first_line)
        except Exception as exc:
            self.add("GET", "/api/events/stream", "FAIL", str(exc))

    def check_websocket(self) -> None:
        if not self.args.include_ws:
            self.add("WS", "/ws/chat", "SKIP", "disabled")
            return

        try:
            import websockets  # type: ignore
        except Exception:
            self.add("WS", "/ws/chat", "SKIP", "websockets package unavailable")
            return

        async def _run_ws() -> tuple[bool, str]:
            ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws/chat"
            try:
                async with websockets.connect(ws_url, open_timeout=self.args.timeout) as ws:
                    await ws.send(json.dumps({"question": "What is photosynthesis?", "subject": "biology"}))
                    _ = await asyncio.wait_for(ws.recv(), timeout=self.args.timeout)
                    return True, "received first websocket message"
            except Exception as exc:
                return False, str(exc)

        ok, reason = asyncio.run(_run_ws())
        self.add("WS", "/ws/chat", 200 if ok else "FAIL", reason)

    def summary(self) -> dict[str, Any]:
        passed = 0
        failed = 0
        skipped = 0

        for row in self.results:
            if row.status == "SKIP":
                skipped += 1
            elif isinstance(row.status, int) and 200 <= row.status < 300:
                passed += 1
            else:
                failed += 1

        return {
            "baseUrl": self.base_url,
            "profile": self.args.profile,
            "includeLlm": self.args.include_llm,
            "includeWs": self.args.include_ws,
            "strictSkips": self.args.strict_skips,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "testUser": self.user_name,
            "counts": {
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "total": len(self.results),
            },
            "results": [r.__dict__ for r in self.results],
        }

    def run(self) -> int:
        if not self.wait_for_health():
            print("[ERROR] API is not healthy/reachable.")
            return 2

        self.check_system()
        self.maybe_seed_subjects()

        user_id = self.auth_bootstrap()
        self.do(
            "POST",
            "/api/auth/profile",
            {
                "name": self.user_name,
                "username": self.user_name,
                "password": self.password,
                "preferred_language": "english",
                "current_class": "12th",
            },
            token=self.token,
        )
        self.do("PUT", "/api/auth/profile", {"daily_study_target": 5}, token=self.token)
        self.do("GET", "/api/auth/users", token=self.token)

        self.check_subjects_books()
        self.check_dashboard_progress()
        self.check_quiz_v2()
        self.check_learn()
        self.check_library()
        self.check_profile_and_achievements()
        self.check_recommendations_and_insights(user_id)

        if self.args.profile == "full" or self.args.include_llm:
            self.check_llm_endpoints()

        self.check_sse()
        self.check_websocket()

        data = self.summary()

        report_path = Path(self.args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        counts = data["counts"]
        print(
            f"SUMMARY PASS={counts['passed']} FAIL={counts['failed']} SKIP={counts['skipped']} TOTAL={counts['total']}"
        )

        if counts["failed"]:
            print("--- FAILURES ---")
            for row in data["results"]:
                st = row["status"]
                if st != "SKIP" and not (isinstance(st, int) and 200 <= st < 300):
                    print(f"{row['method']} {row['path']} -> {st} {row['reason']}")

        if counts["skipped"]:
            print("--- SKIPPED ---")
            for row in data["results"]:
                if row["status"] == "SKIP":
                    print(f"{row['method']} {row['path']} -> SKIP {row['reason']}")

        if counts["failed"] > 0:
            return 1
        if self.args.strict_skips and counts["skipped"] > 0:
            return 3
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="APXMIND full API smoke checks")
    parser.add_argument(
        "--base-url",
        default=os.getenv("APX_BASE_URL", "http://127.0.0.1:8000"),
        help="API base URL",
    )
    parser.add_argument(
        "--profile",
        choices=["core", "full"],
        default=os.getenv("APX_TEST_PROFILE", "core"),
        help="core excludes LLM-heavy endpoints; full includes them",
    )
    parser.add_argument("--include-llm", action="store_true", help="Force include /api/query and trainer endpoints")
    parser.add_argument("--include-ws", action="store_true", help="Enable websocket protocol test")
    parser.add_argument("--seed-if-empty", action="store_true", help="Seed subjects/lessons if subjects table is empty")
    parser.add_argument(
        "--ensure-recommendation",
        action="store_true",
        help="Create recommendation fixture row for patch/delete coverage",
    )
    parser.add_argument("--strict-skips", action="store_true", help="Treat skipped checks as failure")
    parser.add_argument(
        "--report-json",
        default=os.getenv("APX_REPORT_JSON", "artifacts/api-smoke-report.json"),
        help="JSON report output path",
    )
    parser.add_argument("--timeout", type=int, default=int(os.getenv("APX_TIMEOUT", "30")), help="Request timeout seconds")
    parser.add_argument("--health-timeout", type=int, default=5, help="Health-check request timeout seconds")
    parser.add_argument("--health-retries", type=int, default=40, help="Health-check retry count")
    parser.add_argument("--health-interval", type=float, default=0.5, help="Seconds between health retries")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runner = ApiSmokeRunner(args)
    return runner.run()


if __name__ == "__main__":
    raise SystemExit(main())
