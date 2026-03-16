#!/usr/bin/env bash

log() {
  printf '[INFO] %s\n' "$*"
}

warn() {
  printf '[WARN] %s\n' "$*" >&2
}

err() {
  printf '[ERROR] %s\n' "$*" >&2
}

die() {
  err "$*"
  exit 1
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

run_cmd() {
  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    printf '[DRY-RUN]'
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    printf '\n'
  else
    "$@"
  fi
}

run_shell() {
  local cmd="$1"
  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    printf '[DRY-RUN] %s\n' "$cmd"
  else
    bash -lc "$cmd"
  fi
}

require_sudo() {
  if ! command_exists sudo; then
    die "sudo is required."
  fi

  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    return 0
  fi

  sudo -v >/dev/null 2>&1 || die "This script requires a user with sudo access."
}

detect_platform() {
  if [[ ! -f /etc/os-release ]]; then
    die "Cannot detect operating system. /etc/os-release is missing."
  fi

  # shellcheck disable=SC1091
  source /etc/os-release

  if [[ "${ID:-}" != "ubuntu" ]]; then
    die "This setup currently supports Ubuntu only. Detected: ${ID:-unknown}"
  fi

  UBUNTU_VERSION="${VERSION_ID}"
  CODENAME="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
  ARCH="$(dpkg --print-architecture)"

  if [[ -n "${SUDO_USER:-}" ]]; then
    REAL_USER="${SUDO_USER}"
  else
    REAL_USER="${USER}"
  fi

  REAL_HOME="$(getent passwd "$REAL_USER" | cut -d: -f6)"

  export UBUNTU_VERSION CODENAME ARCH REAL_USER REAL_HOME

  log "Detected Ubuntu ${UBUNTU_VERSION} (${CODENAME}), architecture ${ARCH}, target user ${REAL_USER}."
}

version_ge() {
  dpkg --compare-versions "$1" ge "$2"
}

is_apt_installed() {
  dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q '^install ok installed$'
}

is_snap_installed() {
  snap list "$1" >/dev/null 2>&1
}

is_flatpak_installed() {
  flatpak info --system "$1" >/dev/null 2>&1
}

apt_update() {
  run_cmd sudo apt-get update
}

apt_install() {
  run_cmd sudo apt-get install -y "$@"
}

ensure_universe() {
  run_cmd sudo add-apt-repository -y universe
}

ensure_multiverse() {
  run_cmd sudo add-apt-repository -y multiverse
}

ensure_i386_arch() {
  if [[ "$ARCH" != "amd64" ]]; then
    return 0
  fi

  if ! dpkg --print-foreign-architectures | grep -qx 'i386'; then
    log "Enabling i386 architecture support."
    run_cmd sudo dpkg --add-architecture i386
    apt_update
  fi
}

ensure_flatpak_flathub() {
  if ! command_exists flatpak; then
    apt_install flatpak
  fi

  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    printf '[DRY-RUN] sudo flatpak remote-add --if-not-exists --system flathub https://dl.flathub.org/repo/flathub.flatpakrepo\n'
    return 0
  fi

  if ! flatpak remotes --system --columns=name | grep -qx 'flathub'; then
    run_cmd sudo flatpak remote-add --if-not-exists --system flathub https://dl.flathub.org/repo/flathub.flatpakrepo
  fi
}

snap_install() {
  local package="$1"
  shift || true

  if is_snap_installed "$package"; then
    log "Snap already installed: ${package}"
    return 0
  fi

  run_cmd sudo snap install "$package" "$@"
}

flatpak_install() {
  local app_id="$1"

  if is_flatpak_installed "$app_id"; then
    log "Flatpak already installed: ${app_id}"
    return 0
  fi

  run_cmd sudo flatpak install --system -y flathub "$app_id"
}

install_keyring_from_url() {
  local url="$1"
  local destination="$2"
  local temp_file

  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    printf '[DRY-RUN] install keyring from %s to %s\n' "$url" "$destination"
    return 0
  fi

  temp_file="$(mktemp)"
  curl -fsSL "$url" | gpg --dearmor > "$temp_file"
  sudo install -D -m 0644 "$temp_file" "$destination"
  rm -f "$temp_file"
}

write_root_file_from_stdin() {
  local destination="$1"
  local temp_file

  temp_file="$(mktemp)"
  cat > "$temp_file"

  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    printf '[DRY-RUN] write %s\n' "$destination"
    rm -f "$temp_file"
    return 0
  fi

  if [[ -f "$destination" ]] && cmp -s "$temp_file" "$destination"; then
    log "File already up to date: ${destination}"
    rm -f "$temp_file"
    return 0
  fi

  sudo install -D -m 0644 "$temp_file" "$destination"
  rm -f "$temp_file"
}

install_deb_from_url() {
  local url="$1"
  local label="$2"
  local temp_file

  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    printf '[DRY-RUN] download %s and install as %s\n' "$url" "$label"
    return 0
  fi

  temp_file="$(mktemp --suffix="-${label}.deb")"
  curl -fL "$url" -o "$temp_file"
  sudo apt-get install -y "$temp_file"
  rm -f "$temp_file"
}

run_as_real_user() {
  local cmd="$1"

  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    printf '[DRY-RUN] as %s: %s\n' "$REAL_USER" "$cmd"
    return 0
  fi

  if [[ "$REAL_USER" == "root" ]]; then
    bash -lc "$cmd"
  elif [[ "$(id -un)" == "$REAL_USER" ]]; then
    HOME="$REAL_HOME" bash -lc "$cmd"
  else
    sudo -u "$REAL_USER" env HOME="$REAL_HOME" bash -lc "$cmd"
  fi
}

prepare_system() {
  require_sudo
  detect_platform
  export DEBIAN_FRONTEND=noninteractive

  apt_update
  apt_install ca-certificates curl wget gpg gnupg apt-transport-https software-properties-common lsb-release
  ensure_universe
  apt_install snapd flatpak
  ensure_flatpak_flathub
}
