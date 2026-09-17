@echo off
title WinEvent Analyzer - OS Crash ^& Hang Telemetry Monitor
echo ======================================================================
echo   WinEvent Analyzer - Windows Application Crash ^& Hang Monitor
echo ======================================================================
echo.
echo [*] Starting FastAPI Backend Server on http://127.0.0.1:8000 ...
echo [*] Opening default web browser...
echo [*] Press Ctrl+C in this window to stop the server.
echo.

start "" "http://127.0.0.1:8000"
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000

pause
