@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  Security Assessment Dashboard - Frontend
echo ============================================
echo Project root: %CD%
echo.

where npm >nul 2>nul
if errorlevel 1 (
    echo ERROR: npm was not found on PATH. Install Node.js 20+ from https://nodejs.org and retry.
    exit /b 1
)

if not exist "node_modules" (
    echo Installing frontend dependencies ^(npm install^)...
    call npm install
    if errorlevel 1 (
        echo ERROR: npm install failed. Check the npm output above.
        exit /b 1
    )
)

echo.
echo Starting frontend:
echo   App:  http://localhost:5173
echo   ^(proxies /api requests to http://localhost:8000 - the backend must be running^)
echo Press Ctrl+C to stop.
echo.

call npm run dev

endlocal
