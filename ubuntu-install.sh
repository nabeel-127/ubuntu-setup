#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN=0
INSTALL_CORE=1
INSTALL_DEV=1

usage() {
  cat <<'USAGE'
Usage: ./ubuntu-install.sh [options]

Options:
  --core       Install only core applications
  --dev        Install only developer applications
  --all        Install both core and developer applications (default)
  --dry-run    Print what would run without making changes
  -h, --help   Show this help text
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --core)
      INSTALL_CORE=1
      INSTALL_DEV=0
      shift
      ;;
    --dev)
      INSTALL_CORE=0
      INSTALL_DEV=1
      shift
      ;;
    --all)
      INSTALL_CORE=1
      INSTALL_DEV=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf '[ERROR] Unknown option: %s\n' "$1" >&2
      usage
      exit 1
      ;;
  esac
done

export DRY_RUN

# shellcheck source=scripts/lib/common.sh
source "$SCRIPT_DIR/scripts/lib/common.sh"
# shellcheck source=scripts/install-core.sh
source "$SCRIPT_DIR/scripts/install-core.sh"
# shellcheck source=scripts/install-dev.sh
source "$SCRIPT_DIR/scripts/install-dev.sh"

main() {
  if [[ $EUID -eq 0 && -z "${SUDO_USER:-}" ]]; then
    warn "Running directly as root is supported, but Rust will install into root's home."
    warn "For a normal desktop setup, run this script as your regular user with sudo access."
  fi

  prepare_system

  if [[ "$INSTALL_CORE" == "1" ]]; then
    log "Installing core application suite..."
    install_core_suite
  fi

  if [[ "$INSTALL_DEV" == "1" ]]; then
    log "Installing developer application suite..."
    install_dev_suite
  fi

  log "Done."
}

main "$@"
