# ubuntu-setup

A modular Ubuntu workstation bootstrap script for installing the base desktop and development software used in this repo.

## Goals

- Keep the user entrypoint simple: one command
- Prefer Ubuntu apt first
- Fall back to Snap only when apt is not the chosen path
- Fall back to Flathub only when apt and Snap are not the chosen path
- Avoid custom/manual installers unless there is no reasonable packaged option
- Keep the structure modular and maintainable for long-term growth

## Current structure

```text
ubuntu-install.sh
scripts/
  core.sh
  dev.sh
  lib/
    common.sh
docs/
  software-sources.md
tests/
  smoke.sh
```

## Supported target

* Ubuntu only
* Best-supported path: Ubuntu 22.04 and 24.04 on amd64
* Some packages also work on arm64, but not every desktop app in this repo supports it

## Install groups

### Core applications

* Microsoft Edge
* Microsoft Teams
* Dropbox
* Steam
* Bottles
* OBS Studio
* WhatsApp Desktop
* Wine
* Notion
* Proton Mail
* Outlook
* Tor Browser Launcher

### Developer applications

* Git
* VS Code
* Warp
* Python
* Node.js
* .NET SDK 10.0
* Rust

## Usage

Run everything:

```bash
chmod +x ubuntu-install.sh scripts/core.sh scripts/dev.sh scripts/lib/common.sh tests/smoke.sh
./ubuntu-install.sh
```

Run only core apps:

```bash
./ubuntu-install.sh --core
```

Run only dev apps:

```bash
./ubuntu-install.sh --dev
```

Preview without making changes:

```bash
./ubuntu-install.sh --dry-run
```

## Notes

* Some requested desktop apps do not have official native Linux packages, so this repo uses packaged wrappers where necessary.
* OBS Studio is installed from Ubuntu apt.
* Tor Browser is installed through `torbrowser-launcher`, which downloads and launches Tor Browser for Linux.
* Bottles uses Flathub.
* See `docs/software-sources.md` for the curated source choices and caveats.

## Tests

Run smoke tests:

```bash
bash tests/smoke.sh
```

The smoke test currently checks:

* shell syntax for all scripts
* `--help`
* dry-run execution on Ubuntu hosts

## Future improvements

* add CI for smoke tests
* add optional uninstall helpers
* add more apps through the same modular pattern
* add a small manifest layer if the package list grows significantly
