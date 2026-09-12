#Requires -Version 5.1
<#
.SYNOPSIS
  Brings up the full VYOMA + KAVACH demo stack from one command.

.DESCRIPTION
  Kills any stale listeners on port 8000/3000 (a stale server on the frontend
  port silently shadowed the app in rehearsal and served outdated routes),
  ensures local Ollama is reachable on 11434, seeds the demo SAFETY_OFFICER
  account (idempotent), then starts the backend and frontend as background
  processes and polls both until they respond.

  Every status line prints reflects an actual health check. Safe to re-run.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$BACKEND_URL = "http://127.0.0.1:8000"
$FRONTEND_URL = "http://127.0.0.1:3000"
$OLLAMA_URL = "http://127.0.0.1:11434/api/tags"

function Write-Status($msg) { Write-Host "[demo] $msg" }

function Get-PortOwnerPids($port) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
}

function Test-Ollama {
    try {
        $r = Invoke-WebRequest -Uri $OLLAMA_URL -UseBasicParsing -TimeoutSec 2
        return $r.StatusCode -eq 200
    } catch { return $false }
}

## 1) Kill stale listeners so we always serve today's code, not a leftover.
foreach ($port in 8000, 3000) {
    $pids = Get-PortOwnerPids $port
    if ($pids) {
        foreach ($procId in $pids) {
            $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Status ("port {0}: killing stale listener PID {1} ({2})" -f $port, $procId, $proc.ProcessName)
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            } else {
                Write-Status ("port {0}: stale listener PID {1} no longer running" -f $port, $procId)
            }
        }
    } else {
        Write-Status ("port {0}: no listener to kill" -f $port)
    }
}
Start-Sleep -Milliseconds 600

## 2) Make sure local Ollama is reachable (start it best-effort if not).
if (Test-Ollama) {
    Write-Status "Ollama reachable on http://127.0.0.1:11434"
} else {
    Write-Status "Ollama not reachable on 11434; attempting to start it..."
    $candidates = @()
    $appOllama = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $appOllama) { $candidates = @($appOllama) }
    $cmdOllama = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmdOllama) { $candidates = @($candidates + $cmdOllama.Source) }

    if (-not $candidates) {
        Write-Host "[demo] ERROR: Ollama is not running and no ollama.exe was found to start it. Install/start Ollama and re-run." -ForegroundColor Red
        exit 1
    }

    $started = $false
    foreach ($bin in $candidates) {
        try {
            Start-Process -FilePath $bin -ArgumentList "serve" -WindowStyle Hidden | Out-Null
            Write-Status ("starting Ollama via: {0}" -f $bin)
            $started = $true
            break
        } catch {
            Write-Status ("could not start {0}: {1}" -f $bin, $_.Exception.Message)
        }
    }

    if (-not $started) {
        Write-Host "[demo] ERROR: could not start Ollama. Start it manually (e.g. `ollama serve`) and re-run." -ForegroundColor Red
        exit 1
    }

    $ok = $false
    for ($i = 0; $i -lt 20; $i++) {
        if (Test-Ollama) { $ok = $true; break }
        Start-Sleep -Milliseconds 1000
    }
    if (-not $ok) {
        Write-Host "[demo] ERROR: Ollama still not reachable on http://127.0.0.1:11434 after ~20s. Verify the Ollama app is installed and running, then re-run." -ForegroundColor Red
        exit 1
    }
    Write-Status "Ollama is now reachable on http://127.0.0.1:11434"
}

## 3) Seed the demo user (idempotent; no duplicates on re-run).
Write-Status "Seeding demo SAFETY_OFFICER user..."
& python scripts/seed_demo_user.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[demo] ERROR: seeding demo user failed (exit code $LASTEXITCODE)." -ForegroundColor Red
    exit 1
}

## 4) Start the backend as a background process.
Write-Status "Starting backend (uvicorn backend.main:app)..."
Start-Process python -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $Root -WindowStyle Hidden | Out-Null

## 5) Start the built frontend (`next start`; assumes a prior `pnpm build`).
Write-Status "Starting frontend (pnpm start)..."
Start-Process cmd.exe -ArgumentList "/c", "pnpm start" -WorkingDirectory (Join-Path $Root "frontend") -WindowStyle Hidden | Out-Null

## 6) Poll both services; every success/error line is a real check.
$apiOk = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        if ((Invoke-WebRequest -Uri "$BACKEND_URL/api/health" -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) { $apiOk = $true; break }
    } catch { }
    Start-Sleep -Milliseconds 1000
}
if (-not $apiOk) {
    Write-Host "[demo] ERROR: backend did not become healthy on $BACKEND_URL after ~30s. Verify Python/uvicorn are available and port 8000 is free." -ForegroundColor Red
    exit 1
}
Write-Status "backend healthy on $BACKEND_URL (checked /api/health)"

$webOk = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        if ((Invoke-WebRequest -Uri "$FRONTEND_URL/" -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) { $webOk = $true; break }
    } catch { }
    Start-Sleep -Milliseconds 1000
}
if (-not $webOk) {
    Write-Host "[demo] ERROR: frontend did not respond on $FRONTEND_URL after ~30s. Did you run `pnpm build` in frontend/ first? (pnpm start serves the last build.)" -ForegroundColor Red
    exit 1
}
Write-Status "frontend up on $FRONTEND_URL (checked HTTP 200)"

## 7) Success banner with URLs, credentials, and fixture paths.
$conflict = Join-Path $Root "ai_agent\fixtures\conflict_case.json"
$safe = Join-Path $Root "ai_agent\fixtures\safe_case.json"
Write-Host ""
Write-Host "[demo] Demo stack is UP." -ForegroundColor Green
Write-Host "  Backend:   $BACKEND_URL   (health: $BACKEND_URL/api/health)" -ForegroundColor Cyan
Write-Host "  Frontend:  $FRONTEND_URL" -ForegroundColor Cyan
Write-Host "  Demo login: officer / pass  (SAFETY_OFFICER; demo-only, not a security control)" -ForegroundColor Cyan
Write-Host "  Fixtures:" -ForegroundColor Cyan
Write-Host "    conflict scenario -> $conflict"
Write-Host "    safe scenario     -> $safe"