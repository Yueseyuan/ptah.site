@echo off
:: Site Clone Tool — Windows launcher
:: Double-click this file to run.

setlocal
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════╗
echo  ║       SITE CLONE TOOL            ║
echo  ╚══════════════════════════════════╝
echo.

:: check node is installed
where node >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Node.js is not installed.
    echo  Download from https://nodejs.org
    pause
    exit /b 1
)

set /p URL="  Enter URL to clone: "
if "%URL%"=="" goto :end

echo.
echo  Mode:
echo    1  Standard  (HTML, CSS, JS, images, fonts, colors)
echo    2  Deep      (+ API capture, rendered DOM, mock server)
echo.
set /p MODE="  Choose [1/2]: "

if "%MODE%"=="2" (
    echo.
    echo  Running deep clone of %URL% ...
    echo.
    node clone.js %URL% --deep
) else (
    echo.
    echo  Cloning %URL% ...
    echo.
    node clone.js %URL%
)

if errorlevel 0 (
    echo.
    echo  Done! Opening output folder...
    :: open the most recently created cloned folder
    for /f "delims=" %%d in ('dir /b /ad /od "cloned\" 2^>nul') do set LATEST=%%d
    if defined LATEST (
        explorer "cloned\%LATEST%"
    )
)

:end
echo.
pause
