@echo off
title CA Engine Launcher
color 1F

echo.
echo  ================================================
echo   Cruel ^& Associates -- CA Engine
echo  ================================================
echo.

echo  [1/4] Writing API config...
echo NEXT_PUBLIC_API_URL=http://localhost:8001> "C:\Users\origi\Desktop\ptah.site\ca-engine\frontend\.env.local"

echo  [2/4] Starting backend on port 8001...
start "CA Engine -- Backend" cmd /k "cd /d C:\Users\origi\Desktop\ptah.site\ca-engine\backend && py -3.11 -m uvicorn app.main:app --reload --port 8001"

echo  [3/4] Waiting for backend to initialize...
timeout /t 8 /nobreak > nul

echo  [4/4] Building ^& starting frontend on port 3002...
start "CA Engine -- Frontend" cmd /k "cd /d C:\Users\origi\Desktop\ptah.site\ca-engine\frontend && npm run build && npm start -- -p 3002"

echo.
echo  Frontend is building -- this takes about 60 seconds.
echo  Browser will open automatically when ready...
timeout /t 75 /nobreak > nul

start http://localhost:3002

echo.
echo  CA Engine is running.
echo  Backend:  http://localhost:8001/api/docs
echo  Frontend: http://localhost:3002
echo.
echo  Close the two terminal windows to shut down.
pause
