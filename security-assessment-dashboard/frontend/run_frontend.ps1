# Starts the Vite frontend dev server for local development.
# Installs node_modules if missing, then starts the dev server.

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
Set-Location $root

Write-Host "== Security Assessment Dashboard - Frontend ==" -ForegroundColor Cyan
Write-Host "Project root: $root"
Write-Host ""

try {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "npm was not found on PATH. Install Node.js 20+ from https://nodejs.org and retry."
    }

    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing frontend dependencies (npm install)..." -ForegroundColor Yellow
        npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install failed. Check the npm output above." }
    }

    Write-Host ""
    Write-Host "Starting frontend:" -ForegroundColor Green
    Write-Host "  App:  http://localhost:5173"
    Write-Host "  (proxies /api requests to http://localhost:8000 - the backend must be running)"
    Write-Host "Press Ctrl+C to stop." -ForegroundColor DarkGray
    Write-Host ""

    npm run dev
}
catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
