# scripts/dev.ps1 - start backend + dashboard together (no manual venv activation).
# Equivalent to: npm run dev
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'node not found on PATH - install Node.js 18+' }
  if (-not (Test-Path (Join-Path $root 'backend\.venv'))) { Write-Host 'Backend virtualenv missing - running npm run setup first...' -ForegroundColor Yellow; npm run setup }
  if (-not (Test-Path (Join-Path $root 'node_modules\.bin\concurrently.cmd'))) { Write-Host 'Installing root dev deps (concurrently)...' -ForegroundColor Yellow; npm install --no-audit --no-fund }
  if (-not (Test-Path (Join-Path $root 'dashboard\node_modules'))) { Write-Host 'Dashboard deps missing - running npm run setup...' -ForegroundColor Yellow; npm run setup }
  npm run dev
} finally { Pop-Location }
