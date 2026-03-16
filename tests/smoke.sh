#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

FILES=(
  "$ROOT_DIR/ubuntu-install.sh"
  "$ROOT_DIR/scripts/lib/common.sh"
  "$ROOT_DIR/scripts/core.sh"
  "$ROOT_DIR/scripts/dev.sh"
)

for file in "${FILES[@]}"; do
  bash -n "$file"
done

"$ROOT_DIR/ubuntu-install.sh" --help >/dev/null

if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
  if [[ "${ID:-}" == "ubuntu" ]]; then
    "$ROOT_DIR/ubuntu-install.sh" --dry-run --core >/dev/null
    "$ROOT_DIR/ubuntu-install.sh" --dry-run --dev >/dev/null
    "$ROOT_DIR/ubuntu-install.sh" --dry-run --all >/dev/null
  else
    echo "Skipping dry-run execution checks: non-Ubuntu host."
  fi
else
  echo "Skipping dry-run execution checks: /etc/os-release not found."
fi

echo "Smoke tests passed."
