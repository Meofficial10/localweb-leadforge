// scripts/setup.mjs —— one-time environment setup (npm run setup)
// 1. create backend/.venv if missing  2. install backend deps  3. install dashboard deps
// 4. copy .env.example -> backend/.env if missing  5. alembic upgrade head
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, copyFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const isWin = process.platform === 'win32';
const fail = (msg) => { console.error('[setup] ' + msg); process.exit(1); };
const sh = (cmd, args, opts) => {
  console.log('[setup] $ ' + [cmd, ...args].join(' '));
  const r = spawnSync(cmd, args, { stdio: 'inherit', shell: false, windowsHide: true, ...opts });
  if (r.status !== 0) fail(cmd + ' failed (code ' + r.status + ')');
  return r;
};

// --- 1. backend venv ---
const backend = path.join(root, 'backend');
const py = isWin ? 'python.exe' : 'python3';
const venvDir = path.join(backend, '.venv');
const venvPy = path.join(venvDir, isWin ? 'Scripts' : 'bin', isWin ? 'python.exe' : 'python');
const venvPip = path.join(venvDir, isWin ? 'Scripts' : 'bin', isWin ? 'pip.exe' : 'pip');
if (!existsSync(venvPy)) {
  console.log('[setup] creating backend virtualenv …');
  mkdirSync(backend, { recursive: true });
  sh(py, ['-m', 'venv', '.venv'], { cwd: backend });
} else {
  console.log('[setup] backend virtualenv already present');
}

// --- 2. backend deps (editable install incl. dev extras) ---
if (!existsSync(venvPip)) fail('virtualenv pip missing at ' + venvPip);
sh(venvPy, ['-m', 'pip', 'install', '--upgrade', 'pip', '-q']);
sh(venvPy, ['-m', 'pip', 'install', '-e', '".[dev]"', '-q'], { cwd: backend });

// --- 3. dashboard deps ---
const dash = path.join(root, 'dashboard');
if (!existsSync(path.join(dash, 'node_modules'))) {
  console.log('[setup] installing dashboard dependencies …');
  // prefer pnpm (lockfile present), fall back to npm
  const usePnpm = existsSync(path.join(dash, 'pnpm-lock.yaml'));
  const pm = usePnpm ? 'pnpm' : 'npm';
  sh(pm, ['install'], { cwd: dash });
} else {
  console.log('[setup] dashboard node_modules already present');
}

// --- 4. copy .env.example -> backend/.env if missing ---
const envSrc = path.join(root, '.env.example');
const envDst = path.join(backend, '.env');
if (!existsSync(envDst) && existsSync(envSrc)) {
  copyFileSync(envSrc, envDst);
  console.log('[setup] created backend/.env from .env.example');
} else {
  console.log('[setup] backend/.env already present (or example missing)');
}

// --- 5. alembic upgrade head ---
console.log('[setup] running alembic upgrade head …');
sh(venvPy, ['-m', 'alembic', 'upgrade', 'head'], { cwd: backend });

console.log('[setup] all done — run "npm run dev" to start backend + dashboard.');
