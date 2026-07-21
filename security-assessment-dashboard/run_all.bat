@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  Security Assessment Dashboard - Run All
echo ============================================
echo Project root: %CD%
echo.

if not exist "backend\run_backend.bat" (
    echo ERROR: Missing backend\run_backend.bat
    exit /b 1
)
if not exist "frontend\run_frontend.bat" (
    echo ERROR: Missing frontend\run_frontend.bat
    exit /b 1
)

echo Launching backend in a new window...
start "Security Dashboard - Backend" cmd /k "backend\run_backend.bat"

echo Waiting for the backend to come up...
timeout /t 5 /nobreak >nul

echo Launching frontend in a new window...
start "Security Dashboard - Frontend" cmd /k "frontend\run_frontend.bat"

echo.
echo Both servers are starting, each in its own window:
echo   Frontend:     http://localhost:5173
echo   Backend API:  http://localhost:8000/api/v1
echo   Swagger UI:   http://localhost:8000/docs
echo   ReDoc:        http://localhost:8000/redoc
echo.
echo Close those windows (or press Ctrl+C inside them) to stop the servers.

endlocal
