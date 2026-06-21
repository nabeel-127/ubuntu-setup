from __future__ import annotations

import json
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext
from system.shell_profile import ensure_profile_block


ANDROID_STUDIO_URL = "https://redirector.gvt1.com/edgedl/android/studio/ide-zips/latest/android-studio-latest-linux.tar.gz"
FLUTTER_RELEASES_URL = "https://storage.googleapis.com/flutter_infra_release/releases/releases_linux.json"
GODOT_RELEASE_URL = "https://api.github.com/repos/godotengine/godot/releases/latest"


def install_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    handlers = {
        "codex_cli_standalone": _install_codex_standalone,
        "flutter_sdk": _install_flutter,
        "swiftly": _install_swiftly,
        "android_studio_latest": _install_android_studio,
        "godot_latest": _install_godot,
    }

    for item in items:
        method = str(item.data.get("method", ""))
        handler = handlers.get(method)
        if handler is None:
            context.command.warn(f"Skipping {item.title}: unknown vendor method {method}")
            continue
        context.command.info(f"Installing {item.title}")
        handler(item, context)


def _install_codex_standalone(item: SoftwareItem, context: RuntimeContext) -> None:
    install_url = str(item.data.get("install_url", "https://chatgpt.com/codex/install.sh"))
    script = f"""
set -Eeuo pipefail
export CODEX_NON_INTERACTIVE=1
export CODEX_INSTALL_DIR="${{CODEX_INSTALL_DIR:-$HOME/.local/bin}}"
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  . "$NVM_DIR/nvm.sh"
fi
if command -v npm >/dev/null 2>&1 && npm list -g --depth=0 '@openai/codex' >/dev/null 2>&1; then
  npm uninstall -g '@openai/codex'
fi
curl -fsSL {install_url!r} | CODEX_NON_INTERACTIVE=1 sh
"""
    context.command.run_as_user_shell(script)


def _install_flutter(item: SoftwareItem, context: RuntimeContext) -> None:
    target = context.host.real_home / "development" / "flutter"
    if (target / "bin" / "flutter").exists():
        context.command.info("Already installed: Flutter SDK")
        _ensure_flutter_profile(context)
        return
    if context.command.dry_run:
        print(f"[DRY-RUN] install latest Flutter SDK to {target}")
        return

    data = _read_json(FLUTTER_RELEASES_URL)
    stable_hash = data["current_release"]["stable"]
    release = next(item for item in data["releases"] if item["hash"] == stable_hash)
    archive_url = f"{data['base_url']}/{release['archive']}"
    archive = context.command.download_to_temp(archive_url, suffix=".tar.xz")
    destination = target.parent
    destination.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(archive) as tar:
            tar.extractall(destination)
        context.command.chown_to_target(target)
        _ensure_flutter_profile(context)
    finally:
        archive.unlink(missing_ok=True)


def _install_swiftly(item: SoftwareItem, context: RuntimeContext) -> None:
    arch = _swiftly_arch(context.host.arch)
    if not arch:
        context.command.warn(f"Skipping Swiftly: unsupported architecture {context.host.arch}")
        return
    url = f"https://download.swift.org/swiftly/linux/swiftly-{arch}.tar.gz"
    script = f"""
set -Eeuo pipefail
if command -v swiftly >/dev/null 2>&1; then
  echo "Swiftly already installed"
  exit 0
fi
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
curl -fL -o "$tmp/swiftly.tar.gz" {url!r}
tar -xzf "$tmp/swiftly.tar.gz" -C "$tmp"
swiftly_bin="$(find "$tmp" -type f -name swiftly | head -n 1)"
"$swiftly_bin" init --quiet-shell-followup
"""
    context.command.run_as_user_shell(script)


def _install_android_studio(item: SoftwareItem, context: RuntimeContext) -> None:
    target = context.host.real_home / ".local" / "share" / "android-studio"
    if (target / "bin" / "studio.sh").exists():
        context.command.info("Already installed: Android Studio")
        return
    if context.command.dry_run:
        print(f"[DRY-RUN] install latest Android Studio to {target}")
        return

    archive = context.command.download_to_temp(ANDROID_STUDIO_URL, suffix=".tar.gz")
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            with tarfile.open(archive) as tar:
                tar.extractall(temp_dir)
            extracted = Path(temp_dir) / "android-studio"
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                shutil.rmtree(target)
            shutil.move(str(extracted), target)
            context.command.chown_to_target(target)
        finally:
            archive.unlink(missing_ok=True)


def _install_godot(item: SoftwareItem, context: RuntimeContext) -> None:
    if context.host.arch != "amd64":
        context.command.warn(f"Skipping Godot: unsupported architecture {context.host.arch}")
        return
    local_bin = context.host.real_home / ".local" / "bin" / "godot"
    if local_bin.exists():
        context.command.info("Already installed: Godot")
        return
    if context.command.dry_run:
        print(f"[DRY-RUN] install latest Godot to {local_bin}")
        return

    release = _read_json(GODOT_RELEASE_URL)
    asset = next(
        asset
        for asset in release["assets"]
        if "linux.x86_64.zip" in asset["name"] and "mono" not in asset["name"]
    )
    archive = context.command.download_to_temp(asset["browser_download_url"], suffix=".zip")
    install_dir = context.host.real_home / ".local" / "share" / "godot"
    local_bin.parent.mkdir(parents=True, exist_ok=True)
    install_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(install_dir)
        executables = [path for path in install_dir.iterdir() if path.name.startswith("Godot") and path.is_file()]
        executable = sorted(executables)[-1]
        executable.chmod(executable.stat().st_mode | 0o111)
        if local_bin.exists() or local_bin.is_symlink():
            local_bin.unlink()
        local_bin.symlink_to(executable)
        context.command.chown_to_target(install_dir)
        context.command.chown_to_target(local_bin)
    finally:
        archive.unlink(missing_ok=True)


def _ensure_flutter_profile(context: RuntimeContext) -> None:
    _ensure_profile(
        context,
        "flutter",
        'export PATH="$HOME/development/flutter/bin:$PATH"',
    )


def _ensure_profile(context: RuntimeContext, block_id: str, content: str) -> None:
    if context.command.dry_run:
        print(f"[DRY-RUN] update {context.host.real_home / '.profile'} block {block_id}")
        return
    ensure_profile_block(context.host.real_home, block_id, content)
    context.command.chown_to_target(context.host.real_home / ".profile")


def _read_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "ubuntu-setup"})
    with urlopen(request, timeout=120) as response:
        return json.load(response)


def _swiftly_arch(arch: str) -> str | None:
    if arch == "amd64":
        return "x86_64"
    if arch == "arm64":
        return "aarch64"
    return None
