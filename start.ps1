#!/usr/bin/env pwsh
# APXMIND Project Startup Script

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "      Starting APXMIND Project..." -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Start Backend
Write-Host "Starting Backend (http://localhost:8000)..." -ForegroundColor Green
$backend = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python main.py" -PassThru

Start-Sleep -Seconds 3

# Start Frontend
Write-Host "Starting Frontend (http://localhost:5173)..." -ForegroundColor Green
$frontend = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\client'; npm run dev" -PassThru

Write-Host ""
Write-Host "APXMIND is running!" -ForegroundColor Green
Write-Host "   Backend:  http://localhost:8000" -ForegroundColor Yellow
Write-Host "   Frontend: http://localhost:5173" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C in each terminal window to stop." -ForegroundColor Gray
