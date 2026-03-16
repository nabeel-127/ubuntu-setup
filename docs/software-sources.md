# software sources

This file documents the curated install source chosen for each application.

The repo policy is:

1. Prefer apt
2. If apt is not the chosen path, use Snap
3. If apt and Snap are not the chosen path, use Flathub
4. Use custom/manual installers only as a last resort

## Core applications

| Application | Source | Package / Method | Status | Notes |
|---|---|---|---|---|
| Microsoft Edge | apt | `microsoft-edge-stable` | official | Uses Microsoft's apt repository |
| Microsoft Teams | Snap | `teams-for-linux` | unofficial wrapper | Electron wrapper around the Teams web app |
| Dropbox | apt | `dropbox` | official | Uses Dropbox Linux apt repository |
| Steam | apt | `steam` or `steam-installer` | distro package path | Requires multiverse and i386 support on amd64 |
| Bottles | Flathub | `com.usebottles.bottles` | official / recommended | Chosen because Bottles documents Flatpak as the supported path |
| OBS Studio | apt | `obs-studio` | distro package path | Chosen because Ubuntu already ships it in universe, avoiding an unofficial Snap |
| WhatsApp Desktop | Snap | `whatsapp-desktop-client` | unofficial wrapper | Packaged wrapper |
| Wine | apt | `wine` and `winetricks` | distro package path | Uses Ubuntu packages |
| Notion | Snap | `notion-desktop` | unofficial wrapper | Packaged wrapper |
| Proton Mail | Snap | `proton-mail` | official publisher | Snap path |
| Outlook | Snap | `outlook-ew` | unofficial wrapper | Packaged wrapper |
| Tor Browser | apt | `torbrowser-launcher` | launcher package | Downloads and runs Tor Browser instead of bundling it directly in apt |

## Developer applications

| Application | Source | Package / Method | Status | Notes |
|---|---|---|---|---|
| Git | apt | `git` | distro package path | Standard Ubuntu package |
| VS Code | official deb | downloaded `.deb` | official | Uses Microsoft's published package |
| Warp | official deb | downloaded `.deb` | official | Uses Warp's published package |
| Python | apt | `python3`, `python3-pip`, `python3-venv`, `pipx` | distro package path | Standard Ubuntu packages |
| Node.js | apt | `nodejs`, `npm` | distro package path | Intentionally uses Ubuntu packages instead of custom version managers |
| .NET SDK 10.0 | apt / PPA | `dotnet-sdk-10.0` | official package path | Ubuntu feed on 24.04+, dotnet backports PPA on 22.04 |
| Rust | apt or rustup | `rustup` or official `rustup` bootstrap | mixed | apt on newer Ubuntu, official rustup fallback on older Ubuntu |

## Caveats

- Several requested applications do not provide official native Linux desktop packages, so the repo uses packaged wrappers where necessary.
- The goal here is a practical packaged Ubuntu bootstrap, not perfect upstream purity for every app.
- Tor Browser in this repo uses the packaged launcher route because it best fits the apt-first repo rule.
