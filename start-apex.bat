@echo off
echo Starting APEX AI...

:: Start backend
start "APEX Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && uvicorn app.main:app --port 8083"

:: Wait for backend to be ready
timeout /t 4 /nobreak >nul

:: Start frontend
start "APEX Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

:: Wait for frontend to be ready
timeout /t 6 /nobreak >nul

:: Open browser
start http://localhost:3003

echo APEX AI is starting. Check the two terminal windows for status.
