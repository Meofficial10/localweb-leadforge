"""Pre-commit contact-data gate (staged files). Reads the staged blobs so it scans
exactly what will be committed. Exits 1 when any staged text blob contains a
real-looking email/phone (see app/core/data_hygiene.py) or staged image is evidence.
"""
import subprocess, sys, os
from pathlib import Path

DEF_HINT = "allowlist-only (example.com/example.org/test) or +65 0000 fake numbers"


def staged_files():
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "-z"], capture_output=True, text=True)
    names = [n for n in out.stdout.split("\0") if n]
    return names


def blob(path):
    r = subprocess.run(["git", "show", ":0:" + path], capture_output=True)
    return r.stdout  # bytes


IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif"}


def main():
    from app.core.data_hygiene import find_violations, staged_image_is_evidence
    files = staged_files()
    problems = []
    for name in files:
        ext = Path(name).suffix.lower()
        if ext in IMAGE_EXT:
            if staged_image_is_evidence(name):
                problems.append(f"{name}: staged image is under /evidence or named p6-* (keep evidence local)")
            continue
        data = blob(name)
        # only treat text-y blobs (skip binary heuristics: no null bytes in first chunk)
        if not data or b"\x00" in data[:4096]:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for v in find_violations(text):
            problems.append(f"{name}: {v['kind']} '{v['value']}' (use {DEF_HINT})")
    if problems:
        print("BLOCKED: staged text contains real-looking contact data or evidence images:", file=sys.stderr)
        for p in problems:
            print("  - " + p, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
    sys.exit(main())

