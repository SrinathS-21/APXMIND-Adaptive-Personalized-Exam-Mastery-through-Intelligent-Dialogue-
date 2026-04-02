#!/usr/bin/env python3
"""Offline-to-online sync replay smoke test.

Simulates local queue behavior by:
1) failing sync while "offline" (unreachable endpoint),
2) replaying queued operations after reconnect,
3) verifying idempotent duplicate replay and zero backlog.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


class HttpClient:
    def __init__(self, base_url: str, timeout: int = 20):
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
        except urllib.error.URLError as err:
            return 0, {"error": "network_unreachable", "reason": str(err.reason)}


def get_token(payload: Dict[str, Any]) -> Optional[str]:
    return payload.get("token") or payload.get("access_token")


def add_result(results: list[CheckResult], name: str, passed: bool, detail: str) -> None:
    results.append(CheckResult(name=name, passed=passed, detail=detail))
    marker = "PASS" if passed else "FAIL"
    print(f"[{marker}] {name}: {detail}")


def run(base_url: str) -> int:
    client = HttpClient(base_url)
    results: list[CheckResult] = []

    status, health = client.request("GET", "/health")
    add_result(results, "Health", status == 200 and health.get("status") == "healthy", f"HTTP {status}")

    suffix = str(int(time.time()))
    register_payload = {
        "name": f"Sync Replay User {suffix}",
        "username": f"sync_replay_{suffix}",
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
        return 1

    status, initial_sync_status = client.request("GET", "/api/sync/status", token=token)
    initial_backlog = int(initial_sync_status.get("backlog_count", -1)) if status == 200 else -1
    add_result(
        results,
        "Initial sync status",
        status == 200 and initial_backlog == 0,
        f"HTTP {status}, backlog={initial_backlog}",
    )

    local_queue = [
        {
            "operation_type": "event",
            "entity_type": "planner_task",
            "entity_id": "offline-task-1",
            "payload": {"status": "completed", "source": "offline-replay-smoke"},
            "idempotency_key": f"offline-{suffix}-1",
        },
        {
            "operation_type": "event",
            "entity_type": "spaced_review",
            "entity_id": "offline-review-1",
            "payload": {"result": "correct", "source": "offline-replay-smoke"},
            "idempotency_key": f"offline-{suffix}-2",
        },
        {
            "operation_type": "event",
            "entity_type": "stamina_session",
            "entity_id": "offline-stamina-1",
            "payload": {"score_percent": 72.5, "source": "offline-replay-smoke"},
            "idempotency_key": f"offline-{suffix}-3",
        },
    ]

    offline_client = HttpClient("http://127.0.0.1:1", timeout=1)
    status, offline_attempt = offline_client.request(
        "POST",
        "/api/sync/batch",
        token=token,
        payload={"operations": local_queue},
    )
    add_result(
        results,
        "Offline sync attempt fails",
        status == 0 and offline_attempt.get("error") == "network_unreachable",
        f"HTTP {status}",
    )

    status, replay_batch = client.request(
        "POST",
        "/api/sync/batch",
        token=token,
        payload={"operations": local_queue},
    )
    accepted = int(replay_batch.get("accepted_count", 0)) if status == 200 else 0
    failed = int(replay_batch.get("failed_count", 0)) if status == 200 else -1
    add_result(
        results,
        "Reconnect replay accepted",
        status == 200 and accepted == len(local_queue) and failed == 0,
        f"HTTP {status}, accepted={accepted}, failed={failed}",
    )

    status, replay_duplicate = client.request(
        "POST",
        "/api/sync/batch",
        token=token,
        payload={"operations": local_queue},
    )
    duplicate = int(replay_duplicate.get("duplicate_count", 0)) if status == 200 else 0
    add_result(
        results,
        "Replay idempotency",
        status == 200 and duplicate == len(local_queue),
        f"HTTP {status}, duplicate={duplicate}",
    )

    status, final_sync_status = client.request("GET", "/api/sync/status", token=token)
    synced = int(final_sync_status.get("synced_count", 0)) if status == 200 else 0
    backlog = int(final_sync_status.get("backlog_count", -1)) if status == 200 else -1
    latest_synced_at = final_sync_status.get("latest_synced_at") if status == 200 else None
    add_result(
        results,
        "Final sync status",
        status == 200 and synced >= len(local_queue) and backlog == 0 and isinstance(latest_synced_at, str),
        f"HTTP {status}, synced={synced}, backlog={backlog}",
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
        return 1

    print("\nOffline replay sync smoke test passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify offline-to-online sync replay behavior")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    args = parser.parse_args()
    return run(args.base_url)


if __name__ == "__main__":
    sys.exit(main())
