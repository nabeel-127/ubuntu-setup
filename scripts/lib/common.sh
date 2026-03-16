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

as_root() {
  if [[ $EUID -eq 0 ]]; then
    run_cmd "$@"
  else
    run_cmd sudo "$@"
  fi
}

require_privilege() {
  if [[ $EUID -eq 0 ]]; then
    return 0
  fi

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
    REAL_USER="$(id -un)"
  fi

  REAL_HOME="$(getent passwd "$REAL_USER" | cut -d: -f6)"

  export UBUNTU_VERSION CODENAME ARCH REAL_USER REAL_HOME

  log "Detected Ubuntu ${UBUNTU_VERSION} (${CODENAME}), architecture ${ARCH}, target user ${REAL_USER}."
}

version_ge() {
  dpkg --compare-versions "$1" ge "$2"
}

apt_update() {
  as_root apt-get update
}

apt_install() {
  as_root apt-get install -y "$@"
}

ensure_universe() {
  as_root add-apt-repository -y universe
}

ensure_multiverse() {
  as_root add-apt-repository -y multiverse
}

ensure_i386_arch() {
  if [[ "$ARCH" != "amd64" ]]; then
    return 0
  fi

  if ! dpkg --print-foreign-architectures | grep -qx 'i386'; then
    log "Enabling i386 architecture support."
    as_root dpkg --add-architecture i386
    apt_update
  fi
}

ensure_snapd() {
  if command_exists snap; then
    return 0
  fi

  apt_install snapd
}

ensure_flatpak_flathub() {
  if ! command_exists flatpak; then
    apt_install flatpak
  fi

  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    printf '[DRY-RUN] '
    if [[ $EUID -eq 0 ]]; then
      printf 'flatpak remote-add --if-not-exists --system flathub https://dl.flathub.org/repo/flathub.flatpakrepo\n'
    else
      printf 'sudo flatpak remote-add --if-not-exists --system flathub https://dl.flathub.org/repo/flathub.flatpakrepo\n'
    fi
    return 0
  fi

  if ! flatpak remotes --system --columns=name | grep -qx 'flathub'; then
    as_root flatpak remote-add --if-not-exists --system flathub https://dl.flathub.org/repo/flathub.flatpakrepo
  fi
}

is_snap_installed() {
  snap list "$1" >/dev/null 2>&1
}

is_flatpak_installed() {
  flatpak info --system "$1" >/dev/null 2>&1
}

snap_install() {
  local package="$1"
  shift || true

  ensure_snapd

  if is_snap_installed "$package"; then
    log "Snap already installed: ${package}"
    return 0
  fi

  as_root snap install "$package" "$@"
}

flatpak_install() {
  local app_id="$1"

  ensure_flatpak_flathub

  if is_flatpak_installed "$app_id"; then
    log "Flatpak already installed: ${app_id}"
    return 0
  fi

  as_root flatpak install --system -y flathub "$app_id"
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

  if [[ $EUID -eq 0 ]]; then
    install -D -m 0644 "$temp_file" "$destination"
  else
    sudo install -D -m 0644 "$temp_file" "$destination"
  fi

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

  if [[ $EUID -eq 0 ]]; then
    install -D -m 0644 "$temp_file" "$destination"
  else
    sudo install -D -m 0644 "$temp_file" "$destination"
  fi

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
  as_root apt-get install -y "$temp_file"
  rm -f "$temp_file"
}

run_as_real_user() {
  local cmd="$1"

  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    printf '[DRY-RUN] as %s: %s\n' "$REAL_USER" "$cmd"
    return 0
  fi

  if [[ "$REAL_USER" == "root" ]]; then
    HOME="$REAL_HOME" bash -lc "$cmd"
  elif [[ "$(id -un)" == "$REAL_USER" ]]; then
    HOME="$REAL_HOME" bash -lc "$cmd"
  else
    sudo -u "$REAL_USER" env HOME="$REAL_HOME" bash -lc "$cmd"
  fi
}

prepare_system() {
  require_privilege
  detect_platform
  export DEBIAN_FRONTEND=noninteractive

  apt_update
  apt_install ca-certificates curl gpg gnupg software-properties-common lsb-release
  ensure_universe
}
