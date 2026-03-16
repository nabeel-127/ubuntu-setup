#!/usr/bin/env bash

install_core_suite() {
  install_microsoft_edge
  install_ms_teams
  install_dropbox
  install_steam
  install_bottles
  install_whatsapp_desktop
  install_wine
  install_notion
  install_proton_mail
  install_outlook
}

install_microsoft_edge() {
  if [[ "$ARCH" != "amd64" ]]; then
    warn "Skipping Microsoft Edge: only amd64 is configured in this script."
    return 0
  fi

  log "Installing Microsoft Edge..."
  install_keyring_from_url "https://packages.microsoft.com/keys/microsoft.asc" "/etc/apt/keyrings/microsoft.gpg"
  write_root_file_from_stdin "/etc/apt/sources.list.d/microsoft-edge.list" <<EOF
deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/edge stable main
EOF
  apt_update
  apt_install microsoft-edge-stable
}

install_ms_teams() {
  log "Installing Microsoft Teams wrapper..."
  snap_install teams-for-linux
}

install_dropbox() {
  if [[ "$ARCH" != "amd64" ]]; then
    warn "Skipping Dropbox: the configured apt repo path here is amd64 only."
    return 0
  fi

  log "Installing Dropbox..."
  install_keyring_from_url "https://linux.dropbox.com/fedora/rpm-public-key.asc" "/etc/apt/keyrings/dropbox.gpg"
  write_root_file_from_stdin "/etc/apt/sources.list.d/dropbox.list" <<EOF
deb [arch=amd64 signed-by=/etc/apt/keyrings/dropbox.gpg] https://linux.dropbox.com/ubuntu ${CODENAME} main
EOF
  apt_update
  apt_install python3-gpg dropbox
}

install_steam() {
  if [[ "$ARCH" != "amd64" ]]; then
    warn "Skipping Steam: this script only enables the Ubuntu x86_64/i386 path."
    return 0
  fi

  log "Installing Steam..."
  ensure_multiverse
  ensure_i386_arch
  apt_update

  if apt-cache show steam >/dev/null 2>&1; then
    apt_install steam
  else
    apt_install steam-installer
  fi
}

install_bottles() {
  log "Installing Bottles..."
  flatpak_install com.usebottles.bottles
}

install_whatsapp_desktop() {
  log "Installing WhatsApp Desktop wrapper..."
  snap_install whatsapp-desktop-client
}

install_wine() {
  if [[ "$ARCH" != "amd64" ]]; then
    warn "Skipping Wine: this script only enables the Ubuntu x86_64/i386 path."
    return 0
  fi

  log "Installing Wine..."
  ensure_multiverse
  ensure_i386_arch
  apt_update
  apt_install wine winetricks
}

install_notion() {
  log "Installing Notion wrapper..."
  snap_install notion-desktop
}

install_proton_mail() {
  log "Installing Proton Mail..."
  snap_install proton-mail
}

install_outlook() {
  log "Installing Outlook wrapper..."
  snap_install outlook-ew
}
