@echo off
start "Aegis Backend" cmd /k "cd /d C:\Users\origi\ptah.site\ptah.site\aegis-credit\backend && uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload"
timeout /t 4 /nobreak >nul
start "Aegis Frontend" cmd /k "cd /d C:\Users\origi\ptah.site\ptah.site\aegis-credit\frontend && npm run dev -- --port 3001"
timeout /t 8 /nobreak >nul
start "" "http://localhost:3001"
