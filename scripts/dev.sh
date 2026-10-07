
#!/usr/bin/env bash
# scripts/dev.sh - start backend + dashboard together (no manual venv activation).
# Equivalent to: npm run dev
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v node >/dev/null 2>&1 || { echo "node not found on PATH - install Node.js 18+" >&2; exit 1; }
if [ ! -d "$ROOT/backend/.venv" ]; then
  echo "Backend virtualenv missing - running npm run setup first..." >&2
  npm run setup
fi
if [ ! -x "$ROOT/node_modules/.bin/concurrently" ]; then
  echo "Installing root dev deps (concurrently)..." >&2
  npm install --no-audit --no-fund
fi
if [ ! -d "$ROOT/dashboard/node_modules" ]; then
  echo "Dashboard deps missing - running npm run setup..." >&2
  npm run setup
fi
exec npm run dev
