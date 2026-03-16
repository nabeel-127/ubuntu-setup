#!/usr/bin/env bash

install_dev_suite() {
  install_git
  install_vscode
  install_warp
  install_python
  install_nodejs
  install_dotnet_sdk
  install_rust
}

install_git() {
  log "Installing Git..."
  apt_install git
}

install_vscode() {
  local url

  case "$ARCH" in
    amd64) url="https://update.code.visualstudio.com/latest/linux-deb-x64/stable" ;;
    arm64) url="https://update.code.visualstudio.com/latest/linux-deb-arm64/stable" ;;
    *)
      warn "Skipping VS Code: unsupported architecture ${ARCH}."
      return 0
      ;;
  esac

  if command_exists code; then
    log "VS Code already present; reinstalling via official .deb is not necessary."
    return 0
  fi

  log "Installing VS Code..."
  install_deb_from_url "$url" "vscode"
}

install_warp() {
  local url

  case "$ARCH" in
    amd64) url="https://app.warp.dev/download?package=deb" ;;
    arm64) url="https://app.warp.dev/download?package=deb_arm64" ;;
    *)
      warn "Skipping Warp: unsupported architecture ${ARCH}."
      return 0
      ;;
  esac

  if command_exists warp-terminal; then
    log "Warp already present; reinstalling via official .deb is not necessary."
    return 0
  fi

  log "Installing Warp..."
  install_deb_from_url "$url" "warp"
}

install_python() {
  log "Installing Python toolchain..."
  apt_install python3 python3-pip python3-venv pipx
  run_as_real_user 'pipx ensurepath || true'
}

install_nodejs() {
  log "Installing Node.js from Ubuntu apt..."
  apt_install nodejs npm
}

install_dotnet_sdk() {
  log "Installing .NET SDK 10.0..."

  if version_ge "$UBUNTU_VERSION" "24.04"; then
    apt_update
    apt_install dotnet-sdk-10.0
    return 0
  fi

  if version_ge "$UBUNTU_VERSION" "22.04"; then
    run_cmd sudo add-apt-repository -y ppa:dotnet/backports
    apt_update
    apt_install dotnet-sdk-10.0
    return 0
  fi

  warn ".NET 10.0 automation is only configured here for Ubuntu 22.04 and newer."
}

install_rust() {
  log "Installing Rust..."
  apt_install build-essential
  write_root_file_from_stdin "/etc/profile.d/99-cargo-path.sh" <<'EOF'
export PATH="$HOME/.cargo/bin:$PATH"
EOF

  if version_ge "$UBUNTU_VERSION" "24.04"; then
    apt_install rustup
    run_as_real_user 'rustup default stable && rustup component add rustfmt clippy'
    return 0
  fi

  run_as_real_user 'if [[ ! -x "$HOME/.cargo/bin/rustup" ]]; then curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y; fi; source "$HOME/.cargo/env" && rustup default stable && rustup component add rustfmt clippy'
}
