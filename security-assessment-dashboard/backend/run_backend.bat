@echo off
setlocal

set "ROOT=%~dp0.."
pushd "%ROOT%" || (
    echo ERROR: Could not locate the project root relative to this script.
    exit /b 1
)

echo ============================================
echo  Security Assessment Dashboard - Backend
echo ============================================
echo Project root: %CD%
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: python was not found on PATH. Install Python 3.13+ from https://python.org and retry.
    popd
    exit /b 1
)

set "VENV_PY=.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo No virtual environment found at .venv - creating one...
    python -m venv .venv
    if not exist "%VENV_PY%" (
        echo ERROR: Failed to create the virtual environment at .venv.
        popd
        exit /b 1
    )
)

echo Installing/verifying backend dependencies ^(backend\requirements.txt^)...
"%VENV_PY%" -m pip install --quiet -r backend\requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed. Check the output above for the missing/broken package.
    popd
    exit /b 1
)

if not exist ".env" (
    echo No .env file found - copying .env.example ^(safe defaults for local dev^).
    copy /y ".env.example" ".env" >nul
)

echo.
echo Applying database migrations ^(alembic upgrade head^)...
"%VENV_PY%" -m alembic -c backend\alembic.ini upgrade head
if errorlevel 1 (
    echo ERROR: Alembic migration failed. Check backend\alembic.ini and DATABASE_URL in .env.
    popd
    exit /b 1
)

echo.
echo Starting backend:
echo   API:      http://localhost:8000/api/v1
echo   Swagger:  http://localhost:8000/docs
echo   ReDoc:    http://localhost:8000/redoc
echo Press Ctrl+C to stop.
echo.

"%VENV_PY%" -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

popd
endlocal
