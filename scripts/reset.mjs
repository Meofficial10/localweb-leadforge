// scripts/reset.mjs —— npm run reset -> python -m scripts.reset_db [--seed]
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const isWin = process.platform === 'win32';
const backend = path.join(root, 'backend');
const py = path.join(backend, '.venv', isWin ? 'Scripts' : 'bin', isWin ? 'python.exe' : 'python');
if (!existsSync(py)) { console.error('backend venv missing — run "npm run setup" first'); process.exit(1); }
const args = process.argv.slice(2);
const r = spawnSync(py, ['-m', 'scripts.reset_db', ...args], { cwd: backend, stdio: 'inherit', windowsHide: true });
process.exit(r.status ?? 1);
