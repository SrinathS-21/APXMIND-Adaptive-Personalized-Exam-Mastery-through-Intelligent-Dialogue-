#!/usr/bin/env python3
"""End-to-end verification for student auth plus removed/disabled legacy endpoints."""

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
        data = None
        headers = {"Content-Type": "application/json"}

        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        if token:
            headers["Authorization"] = f"Bearer {token}"

        request = urllib.request.Request(url=url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                parsed = json.loads(body) if body else {}
                return response.status, parsed
        except urllib.error.HTTPError as err:
            body = err.read().decode("utf-8")
            try:
                parsed = json.loads(body) if body else {}
            except json.JSONDecodeError:
                parsed = {"raw": body}
            return err.code, parsed


def get_token(payload: Dict[str, Any]) -> Optional[str]:
    return payload.get("access_token") or payload.get("token")


def add_result(results: list[CheckResult], name: str, passed: bool, detail: str) -> None:
    results.append(CheckResult(name=name, passed=passed, detail=detail))
    marker = "PASS" if passed else "FAIL"
    print(f"[{marker}] {name}: {detail}")


def verify(base_url: str) -> int:
    client = HttpClient(base_url)
    results: list[CheckResult] = []

    # 1) Health
    status, health = client.request("GET", "/health")
    add_result(results, "Health endpoint", status == 200, f"HTTP {status}")

    # 2) Register student user and authenticate
    suffix = str(int(time.time()))
    username = f"verify_user_{suffix}"
    register_payload = {
        "name": f"Verify User {suffix}",
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
    user_token = get_token(register_data) if status in (200, 201) else None
    add_result(results, "Register student user", status in (200, 201) and bool(user_token), f"HTTP {status}")

    status, me_data = client.request("GET", "/api/auth/me", token=user_token)
    me_ok = status == 200 and (me_data.get("username") == username or me_data.get("name") == register_payload["name"])
    add_result(results, "Student /api/auth/me", me_ok, f"HTTP {status}")

    # 3) Confirm removed/disabled endpoints are inaccessible
    status, _ = client.request("GET", "/api/payments/plans", token=user_token)
    add_result(results, "Payments endpoint removed", status == 404, f"HTTP {status}")

    status, _ = client.request("GET", "/api/security/sessions", token=user_token)
    add_result(results, "Security endpoint disabled", status == 404, f"HTTP {status}")

    # Summary
    failures = [result for result in results if not result.passed]
    print("\nSummary:")
    print(f"  Total checks: {len(results)}")
    print(f"  Passed: {len(results) - len(failures)}")
    print(f"  Failed: {len(failures)}")

    if failures:
        print("\nFailed checks:")
        for result in failures:
            print(f"  - {result.name}: {result.detail}")
        return 1

    print("\nAll verification checks passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify APXMIND student stack and removed legacy endpoints")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    args = parser.parse_args()

    return verify(args.base_url)


if __name__ == "__main__":
    sys.exit(main())
