@echo off
title CA Engine Launcher
color 1F

echo.
echo  ================================================
echo   Cruel ^& Associates -- CA Engine
echo  ================================================
echo.

echo  [1/3] Starting backend on port 8001...
start "CA Engine -- Backend" cmd /k "cd /d C:\Users\origi\Desktop\ptah.site\ca-engine\backend && py -3.11 -m uvicorn app.main:app --reload --port 8001"

echo  [2/3] Waiting for backend to initialize...
timeout /t 6 /nobreak > nul

echo  [3/3] Starting frontend on port 3002...
start "CA Engine -- Frontend" cmd /k "cd /d C:\Users\origi\Desktop\ptah.site\ca-engine\frontend && npm start -- -p 3002"

echo.
echo  Waiting for frontend to come up...
timeout /t 10 /nobreak > nul

echo  Opening browser...
start http://localhost:3002

echo.
echo  CA Engine is running.
echo  Backend:  http://localhost:8001/api/docs
echo  Frontend: http://localhost:3002
echo.
echo  Close the two terminal windows to shut down.
pause
