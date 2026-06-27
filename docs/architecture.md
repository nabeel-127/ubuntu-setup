# Architecture

`ubuntu-setup` is a terminal-only Python application for installing and
uninstalling a configured Ubuntu workstation software catalog.

## Runtime Shape

```text
ubuntu-setup
  -> main.py
  -> bootstrap.main()
      -> config/*.yaml
      -> runtime.catalog
      -> runtime.selector
      -> runtime.planner
      -> runtime.runner
          -> system.packages.*
              -> system.command
```

`runtime/` decides what should install or uninstall. `system/` knows how to
inspect and change the host.

## Structure

```text
main.py
ubuntu-setup
bootstrap.py
pyproject.toml
README.md
codex.md

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
    snap.py
    flatpak.py
    deb.py
    nvm.py
    npm.py
    rustup.py
    vendor_download.py

docs/
tests/
```

## Ownership

| Path | Role |
| --- | --- |
| `ubuntu-setup` | Tiny Bash wrapper that forwards all arguments to `main.py`. |
| `main.py` | Thin executable entrypoint. |
| `bootstrap.py` | CLI parsing, YAML bootstrap, config loading, host detection, and handoff. |
| `config/` | Declarative source, category, logging, and software data. |
| `runtime/` | Catalog validation, terminal software selection, category/source filtering, install dependency expansion, and plan execution order. |
| `system/` | Ubuntu/WSL detection, sudo handling, command execution, profile updates, and package source adapters. |
| `docs/` | Durable project notes. |
| `tests/` | Smoke and validation checks. |
| `codex.md` | Work log and agent-facing project notes. |

## Source Adapters

| Source | Adapter |
| --- | --- |
| `apt.ubuntu` | `system/packages/apt/ubuntu.py` |
| `apt.external` | `system/packages/apt/external.py` |
| `snap` | `system/packages/snap.py` |
| `flatpak` | `system/packages/flatpak.py` |
| `deb` | `system/packages/deb.py` |
| `nvm` | `system/packages/nvm.py` |
| `npm` | `system/packages/npm.py` |
| `rustup` | `system/packages/rustup.py` |
| `vendor_download` | `system/packages/vendor_download.py` |

## Config Model

`config/software.yaml` is grouped by install source. Each item must have:

- `id`
- `title`
- package metadata when applicable
- `categories`

Optional fields include:

- `provides`
- `architectures`
- `depends_on`
- source-specific repository or installer metadata

Categories are config labels. The code loads category names from
`config/categories.yaml` and does not hardcode category behavior. The first
category on a software item is used as its primary category for checklist
grouping; additional categories remain labels and are shown alongside the item.

## Interactive Selection

Install runs open a terminal checklist by default with all matching items
checked. Uninstall runs use the same checklist with all matching items
unchecked. The checklist reads enabled items from `config/software.yaml`, groups
them by category title from `config/categories.yaml`, and returns selected
software ids for the current run only. It does not edit config files.

Install dependency expansion happens after selection, so dependencies of
selected software may be added to the final install plan. Uninstall does not
expand dependencies; it removes only selected or filtered software.

Install execution order is: selection or filter resolution, dependency
expansion, WSL default-skip filtering for non-interactive runs, source
preconfiguration, base system preparation, then source adapters. Source
preconfiguration lets adapters such as external apt repair repository files and
keyrings before apt maintenance.
Install runs also perform a repair-only pass for known configured apt sources
before global apt maintenance, which can disable stale duplicate vendor source
files that would otherwise make `apt update` fail.
Base system preparation runs `apt update` and `apt upgrade -y` before checking
or installing required base apt packages.

`--list` remains non-interactive. `--yes` bypasses the checklist and preserves
the immediate action path for scripts and other non-interactive runs. Any
install/uninstall dry-run command without an interactive terminal must pass
`--yes`. Non-interactive uninstall also requires at least one filter to avoid
accidentally removing the full catalog.

When WSL is detected for an interactive install, items marked
`default_unchecked_on_wsl` in `config/software.yaml` remain visible but start
unchecked. Users can still select them manually. Non-interactive WSL install
runs skip those items by default; `--include-wsl-skipped` includes the full
matching catalog, while `--include-wsl-sandboxed` remains a compatibility
override for Snap and Flatpak items only.

Each package adapter owns both install and uninstall behavior for its source via
`install_items` and `uninstall_items`. Install adapters are expected to be safe
to rerun: install missing software, update already installed selected software
where the source supports it, and avoid duplicating repository, profile, or
managed vendor-download state. Apt-backed adapters remove packages with `apt
remove`; Snap and Flatpak call their native remove commands; vendor and
toolchain adapters perform source-specific cleanup.

Base system preparation remains fail-fast. Normal software item failures are
recorded where possible, remaining selected items continue, and the CLI exits
non-zero after printing a failed-items summary.

## Naming Rules

- Use `config/`, not `configs/`.
- Use `system/packages/apt/ubuntu.py` and `system/packages/apt/external.py`.
- Use `system/packages/deb.py`, not `deb_download.py`.
- Use `system/logging.py`, not `logging_config.py`.
- Do not add top-level `installers/`, `providers/`, `src/`, `backend/`,
  `common/`, or `utils/`.
