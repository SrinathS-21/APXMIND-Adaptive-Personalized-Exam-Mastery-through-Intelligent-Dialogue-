@echo off
setlocal

set BASE_URL=%APX_BASE_URL%
if "%BASE_URL%"=="" set BASE_URL=http://127.0.0.1:8000

set MODE=%1
if "%MODE%"=="" set MODE=core

set REPORT_JSON=%APX_REPORT_JSON%
if "%REPORT_JSON%"=="" set REPORT_JSON=artifacts/api-smoke-report.json

echo Starting API server for smoke checks...
start "apx-api-smoke-server" /min cmd /c "cd /d %~dp0.. && python main.py --host 127.0.0.1 --port 8000"

timeout /t 5 /nobreak >nul

set CMD=python scripts/test_full_api.py --base-url %BASE_URL% --profile %MODE% --report-json %REPORT_JSON%
if not "%APX_INCLUDE_LLM%"=="1" goto :skip_llm
set CMD=%CMD% --include-llm
:skip_llm
if not "%APX_INCLUDE_WS%"=="1" goto :skip_ws
set CMD=%CMD% --include-ws
:skip_ws
if "%APX_NO_SEED%"=="1" goto :skip_seed
set CMD=%CMD% --seed-if-empty
:skip_seed
if "%APX_NO_RECOMMENDATION%"=="1" goto :skip_rec
set CMD=%CMD% --ensure-recommendation
:skip_rec
if "%APX_STRICT_SKIPS%"=="1" set CMD=%CMD% --strict-skips

echo Running smoke checks: %CMD%
%CMD%
set EXIT_CODE=%ERRORLEVEL%

echo Stopping API server...
taskkill /FI "WINDOWTITLE eq apx-api-smoke-server*" /F >nul 2>nul

echo Done. Exit code: %EXIT_CODE%
exit /b %EXIT_CODE%
