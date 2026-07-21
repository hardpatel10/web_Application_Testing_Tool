#!/usr/bin/env bash
# Starts both the backend and frontend dev servers as background processes.
# Convenience wrapper around backend/run_backend.sh + frontend/run_frontend.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "== Security Assessment Dashboard - Run All =="
echo "Project root: $ROOT"
echo

BACKEND_SCRIPT="$ROOT/backend/run_backend.sh"
FRONTEND_SCRIPT="$ROOT/frontend/run_frontend.sh"

[ -f "$BACKEND_SCRIPT" ] || { echo "ERROR: Missing $BACKEND_SCRIPT" >&2; exit 1; }
[ -f "$FRONTEND_SCRIPT" ] || { echo "ERROR: Missing $FRONTEND_SCRIPT" >&2; exit 1; }

mkdir -p "$ROOT/logs"

echo "Launching backend in the background (logs/backend.out)..."
nohup bash "$BACKEND_SCRIPT" > "$ROOT/logs/backend.out" 2>&1 &
BACKEND_PID=$!

echo "Waiting for the backend to come up..."
sleep 5

echo "Launching frontend in the background (logs/frontend.out)..."
nohup bash "$FRONTEND_SCRIPT" > "$ROOT/logs/frontend.out" 2>&1 &
FRONTEND_PID=$!

echo
echo "Both servers are starting:"
echo "  Frontend:     http://localhost:5173  (pid $FRONTEND_PID, logs/frontend.out)"
echo "  Backend API:  http://localhost:8000/api/v1  (pid $BACKEND_PID, logs/backend.out)"
echo "  Swagger UI:   http://localhost:8000/docs"
echo "  ReDoc:        http://localhost:8000/redoc"
echo
echo "Stop with: kill $BACKEND_PID $FRONTEND_PID"
