from __future__ import annotations

import json
import os
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext
from system.shell_profile import ensure_profile_block


ANDROID_STUDIO_URL = "https://redirector.gvt1.com/edgedl/android/studio/ide-zips/latest/android-studio-latest-linux.tar.gz"
ANDROID_REPOSITORY_XML = "https://dl.google.com/android/repository/repository2-1.xml"
ANDROID_REPOSITORY_BASE = "https://dl.google.com/android/repository/"
PLATFORM_TOOLS_URL = "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
CHROME_FOR_TESTING_URL = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
FLUTTER_RELEASES_URL = "https://storage.googleapis.com/flutter_infra_release/releases/releases_linux.json"
GODOT_RELEASE_URL = "https://api.github.com/repos/godotengine/godot/releases/latest"


def install_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    handlers = {
        "flutter_sdk": _install_flutter,
        "swiftly": _install_swiftly,
        "android_studio_latest": _install_android_studio,
        "android_sdk_command_line_tools": _install_android_cmdline_tools,
        "android_platform_tools": _install_android_platform_tools,
        "android_ndk": _install_android_ndk,
        "godot_latest": _install_godot,
        "chromedriver_latest": _install_chromedriver,
    }

    for item in items:
        method = str(item.data.get("method", ""))
        handler = handlers.get(method)
        if handler is None:
            context.command.warn(f"Skipping {item.title}: unknown vendor method {method}")
            continue
        context.command.info(f"Installing {item.title}")
        handler(item, context)


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


def _install_android_cmdline_tools(item: SoftwareItem, context: RuntimeContext) -> None:
    sdk_root = _android_sdk_root(context)
    target = sdk_root / "cmdline-tools" / "latest"
    if (target / "bin" / "sdkmanager").exists():
        context.command.info("Already installed: Android SDK command-line tools")
        _ensure_android_profile(context)
        return
    if context.command.dry_run:
        print(f"[DRY-RUN] install Android SDK command-line tools to {target}")
        return

    archive_url = _latest_android_cmdline_tools_url()
    archive = context.command.download_to_temp(archive_url, suffix=".zip")
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(temp_dir)
            extracted = Path(temp_dir) / "cmdline-tools"
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                shutil.rmtree(target)
            shutil.move(str(extracted), target)
            context.command.chown_to_target(sdk_root)
            _ensure_android_profile(context)
            _accept_android_licenses(context)
        finally:
            archive.unlink(missing_ok=True)


def _install_android_platform_tools(item: SoftwareItem, context: RuntimeContext) -> None:
    sdk_root = _android_sdk_root(context)
    target = sdk_root / "platform-tools"
    if (target / "adb").exists():
        context.command.info("Already installed: Android Platform Tools")
        _ensure_android_profile(context)
        return
    if context.command.dry_run:
        print(f"[DRY-RUN] install Android Platform Tools to {target}")
        return

    archive = context.command.download_to_temp(PLATFORM_TOOLS_URL, suffix=".zip")
    try:
        sdk_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(sdk_root)
        context.command.chown_to_target(sdk_root)
        _ensure_android_profile(context)
    finally:
        archive.unlink(missing_ok=True)


def _install_android_ndk(item: SoftwareItem, context: RuntimeContext) -> None:
    sdkmanager = _android_sdk_root(context) / "cmdline-tools" / "latest" / "bin" / "sdkmanager"
    configured_package = str(item.data.get("sdk_package", "ndk;latest"))
    if context.command.dry_run:
        print(f"[DRY-RUN] install Android NDK using {sdkmanager}")
        return
    if not sdkmanager.exists():
        raise RuntimeError("Android NDK requires Android SDK command-line tools first")

    package_expr = sh_quote(configured_package)
    if configured_package == "ndk;latest":
        package_expr = "$({sdkmanager} --list | awk '/^  ndk;[0-9]/ {{print $1}}' | sort -V | tail -n 1)".format(
            sdkmanager=sh_quote(str(sdkmanager))
        )

    script = f"""
set -Eeuo pipefail
SDKMANAGER={sh_quote(str(sdkmanager))}
if "$SDKMANAGER" --list_installed | grep -q '^ndk;'; then
  echo "Android NDK already installed"
  exit 0
fi
yes | "$SDKMANAGER" --licenses >/dev/null || true
package={package_expr}
"$SDKMANAGER" "$package"
"""
    context.command.run_as_user_shell(script)


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


def _install_chromedriver(item: SoftwareItem, context: RuntimeContext) -> None:
    local_bin = context.host.real_home / ".local" / "bin" / "chromedriver"
    if local_bin.exists():
        context.command.info("Already installed: ChromeDriver")
        return
    if context.command.dry_run:
        print(f"[DRY-RUN] install latest ChromeDriver to {local_bin}")
        return

    data = _read_json(CHROME_FOR_TESTING_URL)
    downloads = data["channels"]["Stable"]["downloads"]["chromedriver"]
    download = next(item for item in downloads if item["platform"] == "linux64")
    archive = context.command.download_to_temp(download["url"], suffix=".zip")
    local_bin.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(temp_dir)
            source = Path(temp_dir) / "chromedriver-linux64" / "chromedriver"
            shutil.copyfile(source, local_bin)
            local_bin.chmod(0o755)
            context.command.chown_to_target(local_bin)
        finally:
            archive.unlink(missing_ok=True)


def _android_sdk_root(context: RuntimeContext) -> Path:
    return context.host.real_home / "Android" / "Sdk"


def _ensure_flutter_profile(context: RuntimeContext) -> None:
    _ensure_profile(
        context,
        "flutter",
        'export PATH="$HOME/development/flutter/bin:$PATH"',
    )


def _ensure_android_profile(context: RuntimeContext) -> None:
    _ensure_profile(
        context,
        "android",
        '\n'.join(
            [
                'export ANDROID_HOME="$HOME/Android/Sdk"',
                'export ANDROID_SDK_ROOT="$ANDROID_HOME"',
                'export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"',
            ]
        ),
    )


def _ensure_profile(context: RuntimeContext, block_id: str, content: str) -> None:
    if context.command.dry_run:
        print(f"[DRY-RUN] update {context.host.real_home / '.profile'} block {block_id}")
        return
    ensure_profile_block(context.host.real_home, block_id, content)
    context.command.chown_to_target(context.host.real_home / ".profile")


def _accept_android_licenses(context: RuntimeContext) -> None:
    sdkmanager = _android_sdk_root(context) / "cmdline-tools" / "latest" / "bin" / "sdkmanager"
    context.command.run_as_user_shell(f"yes | {sh_quote(str(sdkmanager))} --licenses >/dev/null || true")


def _latest_android_cmdline_tools_url() -> str:
    root = ET.fromstring(_read_bytes(ANDROID_REPOSITORY_XML))
    candidates: list[tuple[int, str]] = []
    for package in root.findall(".//remotePackage"):
        path = package.attrib.get("path", "")
        if not path.startswith("cmdline-tools;"):
            continue
        url_node = package.find("archives/archive/complete/url")
        revision = package.find("revision")
        major_node = revision.find("major") if revision is not None else None
        if url_node is None or major_node is None:
            continue
        if "linux" not in (url_node.text or ""):
            continue
        if path == "cmdline-tools;latest":
            return f"{ANDROID_REPOSITORY_BASE}{url_node.text}"
        candidates.append((int(major_node.text or "0"), url_node.text or ""))
    if not candidates:
        raise RuntimeError("Could not resolve latest Android command-line tools")
    _, archive = sorted(candidates)[-1]
    return f"{ANDROID_REPOSITORY_BASE}{archive}"


def _read_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "ubuntu-setup"})
    with urlopen(request, timeout=120) as response:
        return json.load(response)


def _read_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "ubuntu-setup"})
    with urlopen(request, timeout=120) as response:
        return response.read()


def _swiftly_arch(arch: str) -> str | None:
    if arch == "amd64":
        return "x86_64"
    if arch == "arm64":
        return "aarch64"
    return None


def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"
