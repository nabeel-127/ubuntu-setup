# Codex Work Log

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
