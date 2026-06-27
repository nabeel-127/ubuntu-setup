# ubuntu-setup

`ubuntu-setup` is a config-driven Ubuntu workstation installer. It reads the
software catalog from `config/software.yaml`, builds an install plan, and runs
normal Ubuntu package-manager or vendor commands through Python subprocesses.

The default behavior is intentionally interactive: run the app with no filters
and it opens a terminal checklist. On normal Ubuntu installs, every enabled
catalog item starts checked. On WSL, desktop-heavy and daemon-oriented items
remain visible but start unchecked. Uncheck or check anything you want for that
run, then continue.
If selected software declares dependencies, those dependencies may still be
added to the final install plan.

## Supported Target

- Ubuntu only for real installation
- Best-supported path: Ubuntu 22.04 and newer on `amd64`
- `--list` works on any host
- `--dry-run` can be used off Ubuntu to inspect planned commands
- Headless, CI, redirected, or otherwise non-interactive install/uninstall dry-run
  commands must pass `--yes`
- WSL is detected automatically. WSL-unsuitable software remains visible in the
  checklist but starts unchecked by default.

## Usage

List everything that would be installed:

```bash
./ubuntu-setup --list
```

Install with the interactive checklist:

```bash
./ubuntu-setup
```

After the checklist or filtered selection is accepted, install runs perform
`sudo apt update` and `sudo apt upgrade -y` before installing selected software.
This also applies to `--yes` install runs. Uninstall does not run apt
maintenance.

Preview commands without changing the system:

```bash
./ubuntu-setup --yes --dry-run
```

Run without the checklist for automation:

```bash
./ubuntu-setup --yes
```

Include WSL default-unchecked software in a non-interactive WSL run:

```bash
./ubuntu-setup --include-wsl-skipped --yes
```

Attempt only Snap and Flatpak installs on WSL through the legacy sandboxed
override:

```bash
./ubuntu-setup --include-wsl-sandboxed
```

Uninstall with the interactive checklist:

```bash
./ubuntu-setup --uninstall
```

Uninstall starts with every item unchecked. Select the software to remove, then
continue. Uninstall removes only selected software; it does not auto-remove
declared dependencies.

Preview an uninstall:

```bash
./ubuntu-setup --uninstall --yes --dry-run --only git
```

For safety, non-interactive uninstall with `--yes` requires at least one filter:
`--only`, `--category`, or `--source`.

Install by category:

```bash
./ubuntu-setup --category programming
./ubuntu-setup --category camera
```

Install by source:

```bash
./ubuntu-setup --source apt.ubuntu
./ubuntu-setup --source apt.external
```

Install specific software IDs:

```bash
./ubuntu-setup --only git --only nodejs --only codex
```

Comma-separated filters also work:

```bash
./ubuntu-setup --only git,nodejs,codex
```

Install filters first narrow the checklist. For example,
`./ubuntu-setup --category programming` shows only matching programming tools,
all checked by default. Use `--yes` with filters to run immediately without the
checklist. Items are grouped under their first configured category; any
additional categories appear on the same row.

On WSL, items marked as unsuitable for the default WSL profile are shown but
start unchecked. In non-interactive WSL runs, those same items are skipped unless
`--include-wsl-skipped` is passed.

Uninstall uses the same filters, but matching items start unchecked by default.

Checklist controls:

- Up/Down or `j`/`k`: move
- Space: toggle an item
- `a`: select all
- `n`: select none
- Enter: continue
- `q` or Esc: cancel

## WSL Defaults

On WSL, the checklist still shows every matching item, but the following items
start unchecked and are skipped by default in `--yes` runs:

- OBS Studio
- Steam
- Wine
- Tor Browser Launcher
- Aravis Tools
- Blender
- Microsoft Edge
- Visual Studio Code
- Dropbox
- Beekeeper Studio
- Sublime Text
- Warp
- Docker Engine
- WhatsApp Desktop Wrapper
- Notion Desktop Wrapper
- Bottles
- Flutter SDK
- Android Studio
- Godot
- Discord
- Proton Mail

Use `--include-wsl-skipped` to include these by default in a non-interactive WSL
run, or check them manually in the interactive checklist.

## Structure

```text
main.py
ubuntu-setup
bootstrap.py
pyproject.toml
config/
  software.yaml
  categories.yaml
  sources.yaml
  logging.yaml
runtime/
  catalog.py
  categories.py
  selector.py
  sources.py
  planner.py
  runner.py
  state.py
system/
  command.py
  ubuntu.py
  privileges.py
  paths.py
  shell_profile.py
  logging.py
  packages/
    apt/
      ubuntu.py
      external.py
    deb.py
    flatpak.py
    npm.py
    nvm.py
    rustup.py
    snap.py
    vendor_download.py
docs/
tests/
```

## Source Policy

The catalog is source-first:

1. Use Ubuntu apt when the package is suitable.
2. Use official/vendor apt repositories when the vendor provides one.
3. Use official vendor deb downloads when that is the vendor-supported Linux
   package path.
4. Use the vendor-recommended installer for toolchains and apps such as Node.js,
   Rust, Codex CLI, Flutter, Android Studio, and Godot.
5. Use Snap or Flatpak when that is the practical packaged path.

Vendor downloads are re-resolved from official sources where practical. Android
Studio uses the official Android Developers Linux tarball and checksum metadata
instead of the old generic `latest` redirect.

The Python code does not hardcode categories. Categories are labels in
`config/categories.yaml` and on each software item in `config/software.yaml`.

## Idempotency

The app is safe to rerun. Install runs start with apt metadata refresh and
system package upgrades, then each adapter uses install-or-update behavior where
the source supports it:

- apt uses `dpkg-query`, apt repositories, and apt install/upgrade semantics
- snap refreshes installed selected snaps and installs missing ones
- flatpak updates installed selected apps and installs missing ones
- npm updates installed global packages and installs missing ones
- rustup updates the selected toolchain and ensures configured components
- vendor deb downloads compare the installed package version before installing
- vendor downloads use upstream installers, release metadata, checksums, or
  managed install markers to avoid replacing the same completed setup

Some toolchain commands may still refresh metadata, ensure defaults, or relink a
managed binary, but they should not repeatedly reinstall unchanged artifacts.

Uninstall removes package-manager packages with the matching package manager and
uses source-specific cleanup for vendor downloads and user toolchains.

If an individual catalog item fails, the app continues with the remaining
selected software where possible, prints a failed-items summary, and exits
non-zero.

## Tests

Run smoke tests:

```bash
bash tests/smoke.sh
```

The smoke test checks Python syntax, catalog loading, CLI help/list behavior, and
dry-run and adapter behavior for rerun-safe installs.
