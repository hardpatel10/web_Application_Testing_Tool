# Starts both the backend and frontend dev servers, each in its own window.
# Convenience wrapper around backend\run_backend.ps1 + frontend\run_frontend.ps1.

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
Set-Location $root

Write-Host "== Security Assessment Dashboard - Run All ==" -ForegroundColor Cyan
Write-Host "Project root: $root"
Write-Host ""

try {
    $backendScript = Join-Path $root "backend\run_backend.ps1"
    $frontendScript = Join-Path $root "frontend\run_frontend.ps1"

    if (-not (Test-Path $backendScript)) { throw "Missing $backendScript" }
    if (-not (Test-Path $frontendScript)) { throw "Missing $frontendScript" }

    Write-Host "Launching backend in a new window..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$backendScript`""

    Write-Host "Waiting for the backend to come up..." -ForegroundColor DarkGray
    Start-Sleep -Seconds 5

    Write-Host "Launching frontend in a new window..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$frontendScript`""

    Write-Host ""
    Write-Host "Both servers are starting, each in its own window:" -ForegroundColor Green
    Write-Host "  Frontend:     http://localhost:5173"
    Write-Host "  Backend API:  http://localhost:8000/api/v1"
    Write-Host "  Swagger UI:   http://localhost:8000/docs"
    Write-Host "  ReDoc:        http://localhost:8000/redoc"
    Write-Host ""
    Write-Host "Close those windows (or press Ctrl+C inside them) to stop the servers." -ForegroundColor DarkGray
}
catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
