#!/usr/bin/env bash
# Starts the Vite frontend dev server for local development on Linux.
# Installs node_modules if missing, then starts the dev server.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "== Security Assessment Dashboard - Frontend =="
echo "Project root: $ROOT"
echo

if ! command -v npm >/dev/null 2>&1; then
    echo "ERROR: npm was not found on PATH. Install Node.js 20+ (e.g. via nodesource or nvm) and retry." >&2
    exit 1
fi

if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies (npm install)..."
    npm install
fi

echo
echo "Starting frontend:"
echo "  App:  http://localhost:5173"
echo "  (proxies /api requests to http://localhost:8000 - the backend must be running)"
echo "Press Ctrl+C to stop."
echo

exec npm run dev
