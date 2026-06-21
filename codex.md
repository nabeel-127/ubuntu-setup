# Codex Work Log

## 2026-06-20

- Added Docker Engine through Docker's official apt repository, including
  Docker Compose as the Compose v2 apt plugin.
- Added external apt conflict removal support for packages such as old distro
  Docker packages before installing vendor packages.
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
