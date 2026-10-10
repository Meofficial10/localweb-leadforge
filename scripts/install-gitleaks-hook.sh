#!/usr/bin/env sh
# Installs the gitleaks pre-commit hook into .git/hooks.
# Run from repo root:  sh scripts/install-gitleaks-hook.sh
set -e
# no -u (LOCALAPPDATA may be unset)

HOOK_DIR="$(git rev-parse --git-dir)/hooks"
TMP="$HOOK_DIR/.pre-commit.gitleaks"

# Locate gitleaks (PATH first, then known WinGet install locations)
find_bin() {
  # 1) explicit override
  if [ -n "$GITLEAKS_BIN" ] && [ -e "$GITLEAKS_BIN" ]; then printf '%s' "$GITLEAKS_BIN"; return; fi
  # 2) on PATH
  if command -v gitleaks >/dev/null 2>&1; then command -v gitleaks; return; fi
  # 3) known installation roots
  for base in "$LOCALAPPDATA" "$HOME/AppData/Local"; do
    for p in "$base/Microsoft/WinGet/Links/gitleaks.exe" \
             "$base/Microsoft/WinGet/Packages/Gitleaks.Gitleaks_Microsoft.Winget.Source"*/gitleaks.exe; do
      if [ -e "$p" ]; then printf '%s' "$p"; return; fi
    done
  done
}
BIN="$(find_bin)"
if [ -z "$BIN" ]; then
  echo "gitleaks not found. Install: winget install gitleaks  (or set GITLEAKS_BIN)" >&2
  exit 2
fi
printf 'located gitleaks: %s\n' "$BIN"

# Locate python for the contact-data scanner (PATH first, then the backend venv)
find_py() {
  if command -v python >/dev/null 2>&1; then command -v python; return; fi
  if command -v py >/dev/null 2>&1; then printf '%s' "py -3"; return; fi
  for p in "backend/.venv/Scripts/python.exe" "backend/.venv/bin/python"; do
    if [ -e "$p" ]; then printf '%s' "$p"; return; fi
  done
}
PY="$(find_py)"
if [ -z "$PY" ]; then
  echo "python not found — contact-data pre-commit gate will be skipped (gitleaks still runs)" >&2
fi
printf 'located python:    %s\n' "$PY"

mkdir -p "$HOOK_DIR"
cat > "$TMP" <<'HOOK'
#!/usr/bin/env sh
# pre-commit: gitleaks secret scan on staged changes
set -eu
BIN="__GITLEAKS_BIN__"
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT" || exit 2
CFG="--config .gitleaks.toml"
if ! "$BIN" git --pre-commit --staged --verbose $CFG; then
  echo "---------------------------------------------------------------" >&2
  echo "BLOCKED: gitleaks found potential secrets in staged changes." >&2
  echo "Review the report above. False positive? Extend .gitleaks.toml" >&2
  echo "allowlist, then re-run the commit." >&2
  echo "---------------------------------------------------------------" >&2
  exit 1
fi

if [ -n "__PYTHON_BIN__" ]; then
  if ! __PYTHON_BIN__ scripts/check_contact_data.py; then
    echo "----------------------------------------------------------------" >&2
    echo "BLOCKED: staged changes contain real-looking contact data or" >&2
    echo "staged evidence images. See the scanner report above; replace with" >&2
    echo "allowlisted placeholders (example.com/example.org/*.test, +65 0000)." >&2
    echo "----------------------------------------------------------------" >&2
    exit 1
  fi
fi
HOOK

# Escaping: sed replacement string with | delimiter; escape & and |
BIN_ESC="$(printf '%s' "$BIN" | sed 's/[&|]/\\&/g')"
sed "s|__GITLEAKS_BIN__|$BIN_ESC|g" "$TMP" > "$HOOK_DIR/pre-commit"
if [ -n "$PY" ]; then
  PY_ESC="$(printf '%s' "$PY" | sed 's/[&|]/\\&/g')"
  sed -i "s|__PYTHON_BIN__|$PY_ESC|g" "$HOOK_DIR/pre-commit"
else
  sed -i "s|__PYTHON_BIN__||g" "$HOOK_DIR/pre-commit"
fi
rm -f "$TMP"
chmod +x "$HOOK_DIR/pre-commit" 2>/dev/null || true

printf 'Installed gitleaks pre-commit hook:\n  binary: %s\n  hook:   %s\n' "$BIN" "$HOOK_DIR/pre-commit"
