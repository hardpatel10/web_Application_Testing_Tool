# Starts the FastAPI backend (Uvicorn, auto-reload) for local development.
# Creates the venv and installs dependencies if missing, applies pending
# Alembic migrations (no-op if already up to date), then starts the server.

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "== Security Assessment Dashboard - Backend ==" -ForegroundColor Cyan
Write-Host "Project root: $root"
Write-Host ""

$venvPython = Join-Path $root ".venv\Scripts\python.exe"

try {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "python was not found on PATH. Install Python 3.13+ from https://python.org and retry."
    }

    if (-not (Test-Path $venvPython)) {
        Write-Host "No virtual environment found at .venv - creating one..." -ForegroundColor Yellow
        python -m venv .venv
        if (-not (Test-Path $venvPython)) { throw "Failed to create the virtual environment at .venv." }
    }

    Write-Host "Installing/verifying backend dependencies (backend\requirements.txt)..." -ForegroundColor Yellow
    & $venvPython -m pip install --quiet -r backend\requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "pip install failed. Check the output above for the missing/broken package." }

    if (-not (Test-Path ".env")) {
        Write-Host "No .env file found - copying .env.example (safe defaults for local dev)." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
    }

    Write-Host ""
    Write-Host "Applying database migrations (alembic upgrade head)..." -ForegroundColor Yellow
    & $venvPython -m alembic -c backend\alembic.ini upgrade head
    if ($LASTEXITCODE -ne 0) { throw "Alembic migration failed. Check backend\alembic.ini and DATABASE_URL in .env." }

    Write-Host ""
    Write-Host "Starting backend:" -ForegroundColor Green
    Write-Host "  API:      http://localhost:8000/api/v1"
    Write-Host "  Swagger:  http://localhost:8000/docs"
    Write-Host "  ReDoc:    http://localhost:8000/redoc"
    Write-Host "Press Ctrl+C to stop." -ForegroundColor DarkGray
    Write-Host ""

    & $venvPython -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
}
catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
