// scripts/run.mjs —— start one service ("api" or "web") in dev or prod mode.
// Used by the root npm scripts (concurrently gives [api]/[web] colored prefixes).
// Resolves the backend virtualenv and the dashboard Next.js local binary so no
// manual activation is needed.
import { spawn, spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const which = process.argv[2];
const mode = process.argv[3] ?? 'dev';

const isWin = process.platform === 'win32';

function backendPython() {
  const candidates = [
    path.join(root, 'backend', '.venv', isWin ? 'Scripts' : 'bin', isWin ? 'python.exe' : 'python'),
  ];
  for (const c of candidates) if (existsSync(c)) return c;
  return isWin ? 'python.exe' : 'python3'; // fall back to PATH python
}

function dashboardNext() {
  const n = path.join(root, 'dashboard', 'node_modules', 'next', 'dist', 'bin', 'next');
  if (existsSync(n + '.js')) return { node: process.execPath, nextBin: n + '.js' };
  if (existsSync(n)) return { node: process.execPath, nextBin: n };
  throw new Error('dashboard node_modules/next not found — run "npm run setup" first');
}

function runChild(cmd, args, cwd) {
  const child = spawn(cmd, args, { cwd, stdio: 'inherit', shell: false, windowsHide: true });
  const forward = (sig) => { if (!child.killed) child.kill(sig); };
  process.on('SIGINT', () => forward('SIGINT'));
  process.on('SIGTERM', () => forward('SIGTERM'));
  child.on('exit', (code, sig) => { process.exit(code ?? (sig ? 1 : 0)); });
  return child;
}

function runSync(cmd, args, cwd) {
  const r = spawnSync(cmd, args, { cwd, stdio: 'inherit', shell: false, windowsHide: true });
  return r.status ?? 1;
}

const PORT_API = String(process.env.LF_API_PORT || '8000');
const PORT_WEB = String(process.env.LF_WEB_PORT || '3006');

if (which === 'api') {
  const py = backendPython();
  const args = ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', PORT_API];
  if (mode === 'dev') args.push('--reload');
  runChild(py, args, path.join(root, 'backend'));
} else if (which === 'web') {
  const { node, nextBin } = dashboardNext();
  if (mode === 'dev') {
    runChild(node, [nextBin, 'dev', '-p', PORT_WEB, '-H', '127.0.0.1'], path.join(root, 'dashboard'));
  } else {
    // prod: build then start (matches "next build && next start")
    const build = runSync(node, [nextBin, 'build'], path.join(root, 'dashboard'));
    if (build !== 0) process.exit(build);
    runChild(node, [nextBin, 'start', '-p', PORT_WEB, '-H', '127.0.0.1'], path.join(root, 'dashboard'));
  }
} else {
  console.error('usage: node scripts/run.mjs <api|web> <dev|prod>');
  process.exit(2);
}
