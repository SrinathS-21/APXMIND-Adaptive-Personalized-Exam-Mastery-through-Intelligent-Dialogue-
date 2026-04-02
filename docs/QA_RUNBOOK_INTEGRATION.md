# APXMIND Integration QA Runbook

Date: 2026-03-29

## Purpose
Quick, repeatable validation for current integration state across frontend, backend, and key API flows.

## Preconditions
- Python dependencies installed.
- Frontend dependencies installed in `client`.
- API and frontend run on local machine.
- Test with one or two student users.

## Step 0: Start Services

### 0.1 API
```powershell
python main.py --host 127.0.0.1 --port 8000
```

If port 8000 is in use:
```powershell
$conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue; if ($conn) { Stop-Process -Id $conn.OwningProcess -Force }
```

### 0.2 Frontend
```powershell
cd client
npm run dev
```

### 0.3 Model Backend Preflight (Quality Prerequisite)
```powershell
Invoke-RestMethod -Uri http://localhost:11434/api/tags -Method Get
```

Pass criteria:
- Command returns installed model tags.

If this check fails:
- Chat remains functional with graceful fallback, but answer quality will be limited.

## Step 1: Build Sanity

```powershell
cd client
npm run build
```

Pass criteria:
- Build completes successfully.

## Step 2: Core Manual Flow (Student)

1. Login from `/login`.
2. Open dashboard and confirm metrics load.
3. Open subject page and ensure lessons load.
4. Open learn page and send at least 2 messages.
5. Leave learn page and return to verify session path remains stable.
6. Open study plan and click Generate Plan.
7. Mark one task Done and one task Skip.
8. In Active Recommendations, Accept or Dismiss at least one item.
9. In Spaced Revision Queue, submit at least one review result (Correct/Partial/Incorrect) when items are present.
10. In Error Notebook, mark one mistake card resolved when cards are present.
11. Confirm risk topics, calibration, and weekly summary load.
12. Open support page and create one support ticket.
13. Open created ticket and send one reply.
14. Submit one content report from support page.
15. Open library and create then delete a note.
16. Open notifications and mark one item read/unread.

Pass criteria:
- No blocking UI errors in the above flow.
- Planner and insights values update after task changes.
- Support ticket create/reply and content report complete without blocking errors.
- Study plan retrieval/error notebook actions complete without blocking errors when data is available.

## Step 3: Chat Degradation Check (Model Dependency)

The best response quality requires healthy local model services. Validate graceful fallback:

1. Keep API up.
2. Ask a question in Learn chat.
3. If local model backend is unavailable, verify app still returns a non-crashing fallback response.

Pass criteria:
- No 500 crash visible in UI flow.
- Response indicates graceful fallback behavior rather than hard failure.

## Step 4: Student Experience Focus

1. Login as normal user.
2. Confirm no admin navigation or `/admin` workflow is exposed in UI.

Pass criteria:
- UI remains student-focused with no admin portal entry points.

## Step 5: Automated Smoke Suite

Run from workspace root:

```powershell
python scripts/test_core_learning_flow.py --base-url http://127.0.0.1:8000
python scripts/test_learning_backlog.py --base-url http://127.0.0.1:8000
python scripts/verify_full_stack.py --base-url http://127.0.0.1:8000
python scripts/test_quiz_trainer_compat.py --base-url http://127.0.0.1:8000
```

Pass criteria:
- All scripts exit with code 0.

## Step 6: Disabled Domain Guardrails

Payments and security routes are intentionally disabled in the current release scope.
This step exists to prevent accidental re-enable regressions.

Verify removed domains remain inaccessible:

```powershell
python scripts/verify_full_stack.py --base-url http://127.0.0.1:8000
```

Pass criteria (included in script):
- `/api/payments/*` returns 404.
- `/api/security/*` returns 404.

### 6.1 One-time DB schema cleanup (legacy environments)

If your environment was created before payment removal, run the one-time schema cleanup:

```powershell
python scripts/cleanup_legacy_payments_schema.py --dry-run
python scripts/cleanup_legacy_payments_schema.py --apply
```

Expected result:
- Script creates a timestamped DB backup at repo root.
- Legacy payment tables are removed.
- Legacy users columns are removed:
	- `subscription_status`
	- `subscription_expires_at`
	- `lifetime_value_inr`
	- `referral_code`

### 6.2 One-time admin schema cleanup (legacy environments)

If your environment was created before admin deprecation, run:

```powershell
python scripts/cleanup_legacy_admin_schema.py --dry-run
python scripts/cleanup_legacy_admin_schema.py --apply
```

Expected result:
- Script creates a timestamped DB backup at repo root.
- Legacy admin tables are removed:
	- `admin_sessions`
	- `admin_actions`
	- `admin_users`
	- `admin_roles`
- Support/moderation tables are rewritten to remove `admin_users` foreign keys while preserving data.

## Failure Triage Shortcuts

1. API not reachable:
- Recheck `python main.py` logs and port binding.

2. Chat low quality:
- Validate local LLM/embedding backend process is running and reachable.

3. Student login blocked unexpectedly:
- Re-register a local user from the welcome flow and retry.

4. Frontend stale behavior:
- Restart `npm run dev` and hard-refresh browser.

## Release Signoff Checklist

- Build passed.
- Student core manual flow passed.
- Support page ticket and report flow passed.
- Study plan retrieval and error-notebook interactions passed (or no-due-data state handled gracefully).
- Chat fallback behavior confirmed.
- Student-only UX checks passed.
- Automated smoke suite passed.
- Disabled domain checks passed.