@echo off
setlocal
title WinEvent Analyzer - Local SRE Mission Control
cd /d "%~dp0"

set "NPM_CMD="
where npm >nul 2>nul && set "NPM_CMD=npm"
if not exist "frontend\dist\index.html" (
  if not defined NPM_CMD (
    echo [ERROR] React frontend is not built and npm was not found.
    echo Run: cd frontend ^&^& npm install ^&^& npm run build
    pause
    exit /b 1
  )
  if not exist "frontend\node_modules" (
    echo [ERROR] Frontend dependencies are missing.
    echo Run: cd frontend ^&^& npm install ^&^& npm run build
    pause
    exit /b 1
  )
  echo [*] Production frontend build not found. Building React app...
  call %NPM_CMD% --prefix frontend run build
  if errorlevel 1 (
    echo [ERROR] Frontend build failed. Fix the npm output above, then retry.
    pause
    exit /b 1
  )
)

set "PYTHON_CMD="
if exist ".venv\Scripts\python.exe" set "PYTHON_CMD=.venv\Scripts\python.exe"
if not defined PYTHON_CMD where py >nul 2>nul && set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"

if not defined PYTHON_CMD (
  echo [ERROR] Python 3.11+ was not found.
  echo Install Python, then run: python -m pip install -r requirements.txt
  pause
  exit /b 1
)

echo ================================================================
echo   WinEvent Analyzer - Local SRE Mission Control
echo ================================================================
echo [*] Runtime: %PYTHON_CMD%
echo [*] URL: http://127.0.0.1:8000
echo [*] AI: GEMINI_API_KEY optional; Offline mode works without it.
echo [*] Press Ctrl+C in this window to stop the server.
echo.

start "WinEvent Analyzer Server" /b %PYTHON_CMD% -m uvicorn backend.app:app --host 127.0.0.1 --port 8000

set /a ATTEMPTS=0
:wait_for_server
%PYTHON_CMD% -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=1)" >nul 2>nul
if not errorlevel 1 goto server_ready
set /a ATTEMPTS+=1
if %ATTEMPTS% GEQ 20 goto server_unavailable
timeout /t 1 /nobreak >nul
goto wait_for_server

:server_ready
start "" "http://127.0.0.1:8000"
echo [*] Server is ready. Browser opened.
pause
exit /b 0

:server_unavailable
echo [ERROR] Server did not become ready within 20 seconds.
echo Check the Python/Uvicorn output and press Ctrl+C to stop the server.

pause
