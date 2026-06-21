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

## nvm

Node.js is installed through nvm using the upstream Node.js-recommended Linux
flow for version-managed Node installs.

- Node.js LTS

## npm

The npm adapter remains available for future global npm tools declared in
`config/software.yaml`. There are no current npm catalog items.

## rustup

Rust is installed through the official rustup flow:

- Rust stable
- `rustfmt`
- `clippy`

## snap

Snap is used for packaged desktop apps or wrappers where apt/vendor apt is not
the chosen source:

- WhatsApp Desktop Wrapper
- Notion Desktop Wrapper
- Proton Mail

## flatpak

Flatpak is used where the vendor-supported Linux path is Flathub:

- Bottles

## vendor_download

Vendor downloads are used for tools whose official automation path is a direct
download, release API, or upstream installer:

- OpenAI Codex CLI
- Flutter SDK
- Swiftly
- Android Studio
- Godot

## deb

Direct deb downloads are used when the vendor-supported Linux package path is a
rolling `.deb` download instead of an apt repository:

- Discord

## Removed From Scope

The current catalog intentionally excludes JetBrains IDEs, DBeaver, Firefox
Developer Edition, Eclipse, Apache NetBeans, Spring Tools Suite, RStudio Desktop,
Eagle, PhantomJS, Arduino Legacy, Go, Maven, Dart SDK, Crystal, ChromeDriver,
Android SDK Command-line Tools, Android Platform Tools, Android NDK, Microsoft
Teams Wrapper, Outlook Wrapper, and old unused GitHub-release installers.
