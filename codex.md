# Codex Work Log

## 2026-06-20

- Added apt maintenance preflight for install runs: after selection, the app now
  runs `apt update` and `apt upgrade -y` before installing selected software.
- Tightened rerun-safe install-or-update behavior across adapters: Snap,
  Flatpak, npm, rustup, apt external repos, vendor debs, and managed vendor
  downloads now update existing selected software where supported.
- Replaced the Android Studio broken generic latest redirect with a resolver for
  the official Android Developers Linux tarball and SHA-256 checksum metadata.
- Added managed vendor download markers for Android Studio and Godot so repeated
  runs skip the same resolved release and update when the upstream release
  changes.
- Added external apt source conflict repair so stale duplicate vendor source
  files, such as old Warp Deb822 sources with a different `Signed-By`, are
  disabled before global apt maintenance runs.
- Added WSL default-unchecked catalog metadata so WSL installs still show
  desktop-heavy items but do not select them by default.
- Removed Swiftly from the catalog and vendor download adapter.
- Added Docker Engine through Docker's official apt repository, including
  Docker Compose as the Compose v2 apt plugin.
- Added external apt conflict removal support for packages such as old distro
  Docker packages before installing vendor packages.
- Added the default terminal checklist flow before installs, with `--yes` as
  the explicit non-interactive bypass.
- Added a modular `--uninstall` route with an unchecked-by-default selector and
  source-specific uninstall adapter hooks.
- Moved Proton Mail from Snap to vendor deb downloads using Proton's Stable
  Linux feed, and added WSL-safe Snap/Flatpak skipping.
- Added item-level failure summaries so one optional app failure does not hide
  the rest of the run outcome.
- Removed Microsoft Teams Wrapper and Outlook Wrapper from the Snap catalog.
- Moved OpenAI Codex CLI from npm to the official standalone installer under
  vendor downloads.
- Added Discord as a direct deb install using Discord's official rolling Linux
  deb endpoint.
- Added direct deb version checks so rolling downloads are safe to rerun.
- Trimmed the planned catalog scope by documenting removal of Go, Maven, Dart
  SDK, Crystal, ChromeDriver, and standalone Android SDK/NDK tools.
- Confirmed Dropbox remains in the external apt source group.
- Noted follow-up for idempotency behavior and smoke tests after the catalog
  trim.

## 2026-06-15

- Re-read the actual repo after identifying that earlier work had targeted the
  wrong project.
- Replaced the Bash installer with a Python CLI.
- Added `config/software.yaml` as the source-first software catalog.
- Added category, source, and logging config files.
- Split application behavior into `runtime/` and host integration into
  `system/`.
- Added package adapters for Ubuntu apt, external apt, Snap, Flatpak, direct deb,
  nvm, npm, rustup, and vendor downloads.
- Updated README and docs to reflect the implemented Python architecture.
- Updated smoke tests for the new CLI.
- Added a root `ubuntu-setup` Bash wrapper that forwards all arguments to
  `main.py`.
