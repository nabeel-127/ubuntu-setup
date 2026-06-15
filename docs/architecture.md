# Architecture

`ubuntu-setup` is a terminal-only Python application for installing a configured
Ubuntu workstation software catalog.

## Runtime Shape

```text
ubuntu-setup
  -> main.py
  -> bootstrap.main()
      -> config/*.yaml
      -> runtime.catalog
      -> runtime.planner
      -> runtime.runner
          -> system.packages.*
              -> system.command
```

`runtime/` decides what should install. `system/` knows how to inspect and
change the host.

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
| `runtime/` | Catalog validation, category/source filtering, dependency expansion, and plan execution order. |
| `system/` | Ubuntu detection, sudo handling, command execution, profile updates, and package source adapters. |
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

Categories are config labels only. The code loads category names from
`config/categories.yaml` and does not hardcode category behavior.

## Naming Rules

- Use `config/`, not `configs/`.
- Use `system/packages/apt/ubuntu.py` and `system/packages/apt/external.py`.
- Use `system/packages/deb.py`, not `deb_download.py`.
- Use `system/logging.py`, not `logging_config.py`.
- Do not add top-level `installers/`, `providers/`, `src/`, `backend/`,
  `common/`, or `utils/`.
