# ubuntu-setup

`ubuntu-setup` is a config-driven Ubuntu workstation installer. It reads the
software catalog from `config/software.yaml`, builds an install plan, and runs
normal Ubuntu package-manager or vendor commands through Python subprocesses.

The default behavior is intentionally simple: run the app with no filters and it
installs every enabled item in the catalog.

## Supported Target

- Ubuntu only for real installation
- Best-supported path: Ubuntu 22.04 and newer on `amd64`
- `--list` works on any host
- `--dry-run` can be used off Ubuntu to inspect planned commands

## Usage

List everything that would be installed:

```bash
./ubuntu-setup --list
```

Install everything:

```bash
./ubuntu-setup
```

Preview commands without changing the system:

```bash
./ubuntu-setup --dry-run
```

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
3. Use the vendor-recommended installer for language/toolchains such as Node.js,
   Rust, Flutter, Swift, Android tools, Godot, and ChromeDriver.
4. Use Snap or Flatpak when that is the practical packaged path.

The Python code does not hardcode categories. Categories are labels in
`config/categories.yaml` and on each software item in `config/software.yaml`.

## Idempotency

The app is safe to rerun. Package adapters check installed state where practical
before installing:

- apt uses `dpkg-query`
- snap uses `snap list`
- flatpak uses `flatpak info`
- npm checks the global package list
- vendor downloads check their installed command or target path

Some toolchain commands may still refresh metadata or ensure defaults, but they
should not repeatedly reinstall the same completed setup.

## Tests

Run smoke tests:

```bash
bash tests/smoke.sh
```

The smoke test checks Python syntax, catalog loading, CLI help/list behavior, and
a dry-run plan for a known package.
