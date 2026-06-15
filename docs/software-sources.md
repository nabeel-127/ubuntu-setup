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
- Go
- Maven
- Blender
- .NET SDK

## apt.external

Packages installed with apt after adding an official or vendor apt repository:

- Microsoft Edge
- Visual Studio Code
- Dropbox
- Dart SDK
- Beekeeper Studio
- Sublime Text
- Warp
- Crystal

## nvm

Node.js is installed through nvm using the upstream Node.js-recommended Linux
flow for version-managed Node installs.

- Node.js LTS

## npm

Global npm tools installed after Node.js is available:

- OpenAI Codex CLI

## rustup

Rust is installed through the official rustup flow:

- Rust stable
- `rustfmt`
- `clippy`

## snap

Snap is used for packaged desktop apps or wrappers where apt/vendor apt is not
the chosen source:

- Microsoft Teams Wrapper
- WhatsApp Desktop Wrapper
- Notion Desktop Wrapper
- Proton Mail
- Outlook Wrapper

## flatpak

Flatpak is used where the vendor-supported Linux path is Flathub:

- Bottles

## vendor_download

Vendor downloads are used for tools whose official automation path is a direct
download, release API, or upstream installer:

- Flutter SDK
- Swiftly
- Android Studio
- Android SDK Command-line Tools
- Android Platform Tools
- Android NDK
- Godot
- ChromeDriver

## Removed From Scope

The current catalog intentionally excludes JetBrains IDEs, DBeaver, Firefox
Developer Edition, Eclipse, Apache NetBeans, Spring Tools Suite, RStudio Desktop,
Eagle, PhantomJS, Arduino Legacy, and old unused GitHub-release installers.
