#!/usr/bin/env bash
# Starts the FastAPI backend (Uvicorn, auto-reload) for local development on Linux.
# Creates the venv and installs dependencies if missing, applies pending
# Alembic migrations (no-op if already up to date), then starts the server.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== Security Assessment Dashboard - Backend =="
echo "Project root: $ROOT"
echo

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 was not found on PATH. Install Python 3.13+ (e.g. 'sudo apt install python3 python3-venv') and retry." >&2
    exit 1
fi

VENV_PY=".venv/bin/python"

if [ ! -x "$VENV_PY" ]; then
    echo "No virtual environment found at .venv - creating one..."
    python3 -m venv .venv
    if [ ! -x "$VENV_PY" ]; then
        echo "ERROR: Failed to create the virtual environment at .venv." >&2
        exit 1
    fi
fi

echo "Installing/verifying backend dependencies (backend/requirements.txt)..."
"$VENV_PY" -m pip install --quiet -r backend/requirements.txt

if [ ! -f ".env" ]; then
    echo "No .env file found - copying .env.example (safe defaults for local dev)."
    cp ".env.example" ".env"
fi

echo
echo "Applying database migrations (alembic upgrade head)..."
"$VENV_PY" -m alembic -c backend/alembic.ini upgrade head

echo
echo "Starting backend:"
echo "  API:      http://localhost:8000/api/v1"
echo "  Swagger:  http://localhost:8000/docs"
echo "  ReDoc:    http://localhost:8000/redoc"
echo "Press Ctrl+C to stop."
echo

exec "$VENV_PY" -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
