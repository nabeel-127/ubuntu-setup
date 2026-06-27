# Software Sources

`config/software.yaml` is the source of truth for software inventory. This doc
summarizes the source groups and the reason each group exists.

## apt.ubuntu

Packages installed directly from Ubuntu repositories:

- Git
- Python Toolchain
- OpenSSH Client
- Build Essential
- OBS Studio
- Steam
- Wine
- Tor Browser Launcher
- Aravis Tools
- Blender
- .NET SDK

Install runs refresh apt metadata and run `apt upgrade -y` before source
adapters execute. Already installed Ubuntu apt packages are left to apt's normal
upgrade behavior; missing selected packages are installed after any required
Ubuntu components or foreign architectures are enabled.

## apt.external

Packages installed with apt after adding an official or vendor apt repository:

- Microsoft Edge
- Visual Studio Code
- Dropbox
- Beekeeper Studio
- Sublime Text
- Warp
- Docker Engine

Docker Engine uses Docker's official apt repository and installs Docker Compose
as the `docker-compose-plugin` package.

External apt repository files and keyrings are prepared before the global apt
maintenance step so selected vendor repositories can be repaired before `apt
update` runs. The preflight also disables obsolete duplicate `.list` or
`.sources` files for known vendor repositories, such as older Warp sources that
used `/etc/apt/trusted.gpg.d`. If a selected external apt package is already
installed but its repository was added or corrected during the run, the adapter
runs apt install for the full package set so apt can upgrade it from the
configured vendor repository.

## nvm

Node.js is installed through nvm using the upstream Node.js-recommended Linux
flow for version-managed Node installs. Reruns call `nvm install --lts`, which
is idempotent and advances the default LTS when nvm has a newer matching
release.

- Node.js LTS

## npm

The npm adapter remains available for future global npm tools declared in
`config/software.yaml`. Installed global packages are updated with
`npm update -g`; missing packages are installed. There are no current npm
catalog items.

## rustup

Rust is installed through the official rustup flow:

- Rust stable
- `rustfmt`
- `clippy`

Reruns update the configured toolchain and then ensure the default toolchain and
configured components are present.

## snap

Snap is used for packaged desktop apps or wrappers where apt/vendor apt is not
the chosen source:

- WhatsApp Desktop Wrapper
- Notion Desktop Wrapper

Installed selected snaps are refreshed; missing selected snaps are installed.

On WSL, Snap items remain visible in the interactive checklist but start
unchecked by default. Non-interactive WSL runs skip them unless
`--include-wsl-skipped` or `--include-wsl-sandboxed` is passed.

## flatpak

Flatpak is used where the vendor-supported Linux path is Flathub:

- Bottles

Installed selected Flatpak apps are updated from Flathub; missing selected apps
are installed.

On WSL, Flatpak items remain visible in the interactive checklist but start
unchecked by default. Non-interactive WSL runs skip them unless
`--include-wsl-skipped` or `--include-wsl-sandboxed` is passed.

## vendor_download

Vendor downloads are used for tools whose official automation path is a direct
download, release API, or upstream installer:

- OpenAI Codex CLI
- Flutter SDK
- Android Studio
- Godot

Codex reruns the official standalone installer, which resolves the latest
release and reuses complete installed release directories. Flutter reruns
`flutter upgrade` when the SDK is already present. Android Studio resolves the
current Linux tarball from the official Android Developers download page,
verifies the page-provided SHA-256 checksum, and tracks the managed release with
an install marker. Godot resolves the latest GitHub release asset and uses the
managed symlink or marker to skip the same release.

## deb

Vendor deb downloads are used when the vendor-supported Linux package path is a
direct `.deb` download instead of an apt repository:

- Discord
- Proton Mail

Proton Mail resolves the latest Stable Ubuntu/Debian `.deb` from Proton's
official Linux version feed and verifies the feed-provided SHA512 checksum
before installation. Vendor deb installs inspect downloaded package metadata and
skip installation when the installed package version already matches the
downloaded artifact.

## Removed From Scope

The current catalog intentionally excludes JetBrains IDEs, DBeaver, Firefox
Developer Edition, Eclipse, Apache NetBeans, Spring Tools Suite, RStudio Desktop,
Eagle, PhantomJS, Arduino Legacy, Go, Maven, Dart SDK, Crystal, ChromeDriver,
Android SDK Command-line Tools, Android Platform Tools, Android NDK, Microsoft
Teams Wrapper, Outlook Wrapper, Swiftly, and old unused GitHub-release
installers.
