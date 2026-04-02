# API Smoke Runbook

## What this covers

The smoke suite validates APXMIND API behavior end-to-end:
- System + auth + profile
- Subjects + lessons + books
- Dashboard + progress
- Quiz v2 + learn sessions + library
- Achievements + recommendations + insights
- SSE stream health
- Optional: LLM-heavy query/trainer endpoints
- Optional: WebSocket protocol test

## Primary command

```powershell
python scripts/test_core_learning_flow.py --base-url http://127.0.0.1:8000
```

## Full coverage command

```powershell
python scripts/test_core_learning_flow.py --base-url http://127.0.0.1:8000 --include-llm
python scripts/test_sync_offline_replay.py --base-url http://127.0.0.1:8000
python scripts/test_learning_backlog.py --base-url http://127.0.0.1:8000
python scripts/verify_full_stack.py --base-url http://127.0.0.1:8000
python scripts/test_quiz_trainer_compat.py --base-url http://127.0.0.1:8000
```

## One-command local run (starts/stops server automatically)

```powershell
scripts\\run_api_smoke.cmd core
```

By default, this wrapper runs:
- `test_core_learning_flow.py`
- `test_sync_offline_replay.py`

Skip offline replay when needed:

```powershell
set APX_SKIP_SYNC_REPLAY=1
scripts\\run_api_smoke.cmd core
```

## Report output

Default JSON report path:
- `artifacts/api-smoke-report.json`

Override:

```powershell
python scripts/test_core_learning_flow.py --base-url http://127.0.0.1:8000 --report-json artifacts/my-report.json
```

Optional wrapper toggles (environment variables):

```powershell
set APX_INCLUDE_LLM=1
set APX_INCLUDE_WS=1
scripts\\run_api_smoke.cmd full
```

## Exit codes

- `0` => all checks passed (or only skipped checks when not strict)
- `1` => one or more failures
- `2` => API unavailable / health check failed
- `3` => strict mode enabled and one or more checks skipped

## Strict mode

Treat skipped checks as failure:

```powershell
python scripts/test_core_learning_flow.py --base-url http://127.0.0.1:8000
```

## CI workflow

GitHub Actions workflow:
- `.github/workflows/api-smoke.yml`

It runs a `core` profile smoke pass on push/PR and uploads:
- `artifacts/api-smoke-report.json`
- `api.log`

## Common troubleshooting

- `Subject not found`:
  - Run `python -m scripts.seed_data`
- Recommendation PATCH/DELETE skipped:
  - Enable fixture flag: `--ensure-recommendation`
- SSE timeout in custom clients:
  - Ensure you read at least first event line instead of waiting for stream completion
- WebSocket skipped:
  - Use `--include-ws` and ensure `websockets` dependency is available in environment
