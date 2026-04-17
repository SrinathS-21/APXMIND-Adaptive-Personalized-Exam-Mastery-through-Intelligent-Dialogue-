@echo off
setlocal

for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"

set PY_CMD=python
if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" set "PY_CMD=%PROJECT_ROOT%\.venv\Scripts\python.exe"

set BASE_URL=%APX_BASE_URL%
if "%BASE_URL%"=="" set BASE_URL=http://127.0.0.1:8000

set MODE=%1
if "%MODE%"=="" set MODE=core

set REPORT_JSON=%APX_REPORT_JSON%
if "%REPORT_JSON%"=="" set REPORT_JSON=artifacts/api-smoke-report.json

set "STARTED_SERVER=0"
powershell -NoProfile -Command "$u='%BASE_URL%/health'; try { $r=Invoke-WebRequest -UseBasicParsing -Uri $u -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul

if "%ERRORLEVEL%"=="0" (
	echo Reusing existing API server for smoke checks...
) else (
	echo Starting API server for smoke checks...
	start "apx-api-smoke-server" /min cmd /c "cd /d %PROJECT_ROOT% && %PY_CMD% main.py --host 127.0.0.1 --port 8000"
	set "STARTED_SERVER=1"
)

timeout /t 5 /nobreak >nul

set CORE_CMD=%PY_CMD% scripts/test_core_learning_flow.py --base-url %BASE_URL% --profile %MODE% --report-json %REPORT_JSON%
if not "%APX_INCLUDE_LLM%"=="1" goto :skip_llm
set CORE_CMD=%CORE_CMD% --include-llm
:skip_llm

echo Running core smoke checks: %CORE_CMD%
%CORE_CMD%
set CORE_EXIT_CODE=%ERRORLEVEL%

set SYNC_EXIT_CODE=0
if not "%CORE_EXIT_CODE%"=="0" goto :after_sync

if "%APX_SKIP_SYNC_REPLAY%"=="1" (
	echo Skipping offline replay smoke because APX_SKIP_SYNC_REPLAY=1
	goto :after_sync
)

set SYNC_CMD=%PY_CMD% scripts/test_sync_offline_replay.py --base-url %BASE_URL%
echo Running offline replay sync smoke: %SYNC_CMD%
%SYNC_CMD%
set SYNC_EXIT_CODE=%ERRORLEVEL%

:after_sync
set EXIT_CODE=%CORE_EXIT_CODE%
if "%EXIT_CODE%"=="0" set EXIT_CODE=%SYNC_EXIT_CODE%

if "%STARTED_SERVER%"=="1" (
	echo Stopping API server...
	taskkill /FI "WINDOWTITLE eq apx-api-smoke-server*" /F >nul 2>nul
)

echo Done. Exit code: %EXIT_CODE%
exit /b %EXIT_CODE%
