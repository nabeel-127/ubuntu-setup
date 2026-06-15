#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from pathlib import Path

paths = [Path("bootstrap.py"), Path("main.py")]
paths.extend(Path("runtime").glob("*.py"))
paths.extend(Path("system").glob("*.py"))
paths.extend(Path("system/packages").glob("*.py"))
paths.extend(Path("system/packages/apt").glob("*.py"))

for path in paths:
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY

PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --help >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --source apt.ubuntu >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --category programming >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --only git >/dev/null

PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --dry-run --only git >/dev/null

echo "Smoke tests passed."
