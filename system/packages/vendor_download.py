from __future__ import annotations

import hashlib
import json
import re
import shutil
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext
from system.shell_profile import ensure_profile_block, remove_profile_block


ANDROID_STUDIO_DOWNLOAD_PAGE = "https://developer.android.com/studio"
FLUTTER_RELEASES_URL = "https://storage.googleapis.com/flutter_infra_release/releases/releases_linux.json"
GODOT_RELEASE_URL = "https://api.github.com/repos/godotengine/godot/releases/latest"
INSTALL_MARKER = ".ubuntu-setup-install.json"
SHA256_RE = re.compile(r"\b[a-fA-F0-9]{64}\b")


@dataclass(frozen=True)
class AndroidStudioDownload:
    url: str
    filename: str
    sha256: str | None
    title: str | None = None


@dataclass(frozen=True)
class GodotDownload:
    url: str
    tag: str
    asset_name: str


def install_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    handlers = {
        "codex_cli_standalone": _install_codex_standalone,
        "flutter_sdk": _install_flutter,
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


def uninstall_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    handlers = {
        "codex_cli_standalone": _uninstall_codex_standalone,
        "flutter_sdk": _uninstall_flutter,
        "android_studio_latest": _uninstall_android_studio,
        "godot_latest": _uninstall_godot,
    }

    for item in items:
        method = str(item.data.get("method", ""))
        handler = handlers.get(method)
        if handler is None:
            context.command.warn(f"Skipping {item.title}: unknown vendor uninstall method {method}")
            continue
        context.command.info(f"Uninstalling {item.title}")
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


def _uninstall_codex_standalone(item: SoftwareItem, context: RuntimeContext) -> None:
    script = """
set -Eeuo pipefail
removed=0
for path in "$HOME/.local/bin/codex" "$HOME/.codex/bin/codex"; do
  if [ -e "$path" ] || [ -L "$path" ]; then
    rm -f "$path"
    removed=1
  fi
done
if [ "$removed" -eq 0 ]; then
  echo "Codex CLI is not installed"
fi
"""
    context.command.run_as_user_shell(script)


def _install_flutter(item: SoftwareItem, context: RuntimeContext) -> None:
    target = context.host.real_home / "development" / "flutter"
    if (target / "bin" / "flutter").exists():
        _ensure_flutter_profile(context)
        context.command.info("Updating Flutter SDK")
        context.command.run_as_user_shell(
            """
set -Eeuo pipefail
"$HOME/development/flutter/bin/flutter" upgrade
"""
        )
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


def _uninstall_flutter(item: SoftwareItem, context: RuntimeContext) -> None:
    script = """
set -Eeuo pipefail
if [ -d "$HOME/development/flutter" ]; then
  rm -rf "$HOME/development/flutter"
else
  echo "Flutter SDK is not installed"
fi
"""
    context.command.run_as_user_shell(script)
    _remove_profile(context, "flutter")


def _install_android_studio(item: SoftwareItem, context: RuntimeContext) -> None:
    if context.host.arch != "amd64":
        context.command.warn(f"Skipping Android Studio: unsupported architecture {context.host.arch}")
        return

    target = context.host.real_home / ".local" / "share" / "android-studio"
    if context.command.dry_run:
        print(f"[DRY-RUN] resolve latest Android Studio Linux tarball from {ANDROID_STUDIO_DOWNLOAD_PAGE} and install to {target}")
        return

    download = _resolve_android_studio_download()
    marker = target / INSTALL_MARKER
    if (target / "bin" / "studio.sh").exists() and _install_marker_matches(
        marker,
        {
            "source": "android-studio",
            "url": download.url,
            "filename": download.filename,
            "sha256": download.sha256,
        },
    ):
        context.command.info(f"Already installed: Android Studio {download.filename}")
        return

    archive = context.command.download_to_temp(download.url, suffix=".tar.gz")
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            if download.sha256:
                _verify_sha256(archive, download.sha256, "Android Studio")
            with tarfile.open(archive) as tar:
                tar.extractall(temp_dir)
            extracted = Path(temp_dir) / "android-studio"
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                shutil.rmtree(target)
            shutil.move(str(extracted), target)
            _write_install_marker(
                marker,
                {
                    "source": "android-studio",
                    "url": download.url,
                    "filename": download.filename,
                    "sha256": download.sha256,
                    "title": download.title,
                },
            )
            context.command.chown_to_target(target)
        finally:
            archive.unlink(missing_ok=True)


def _uninstall_android_studio(item: SoftwareItem, context: RuntimeContext) -> None:
    script = """
set -Eeuo pipefail
if [ -d "$HOME/.local/share/android-studio" ]; then
  rm -rf "$HOME/.local/share/android-studio"
else
  echo "Android Studio is not installed"
fi
"""
    context.command.run_as_user_shell(script)


def _install_godot(item: SoftwareItem, context: RuntimeContext) -> None:
    if context.host.arch != "amd64":
        context.command.warn(f"Skipping Godot: unsupported architecture {context.host.arch}")
        return
    local_bin = context.host.real_home / ".local" / "bin" / "godot"
    if context.command.dry_run:
        print(f"[DRY-RUN] install latest Godot to {local_bin}")
        return

    download = _resolve_godot_download()
    install_dir = context.host.real_home / ".local" / "share" / "godot"
    marker = install_dir / INSTALL_MARKER
    if _godot_install_current(local_bin, marker, download):
        context.command.info(f"Already installed: Godot {download.tag}")
        if not marker.exists():
            _write_install_marker(
                marker,
                {
                    "source": "godot",
                    "tag": download.tag,
                    "asset_name": download.asset_name,
                    "url": download.url,
                },
            )
            context.command.chown_to_target(marker)
        return

    archive = context.command.download_to_temp(download.url, suffix=".zip")
    local_bin.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            staging = Path(temp_dir) / "godot"
            staging.mkdir()
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(staging)
            executables = [path for path in staging.iterdir() if path.name.startswith("Godot") and path.is_file()]
            if not executables:
                raise RuntimeError("Godot archive did not contain an executable")
            staged_executable = sorted(executables)[-1]
            staged_executable.chmod(staged_executable.stat().st_mode | 0o111)
            _replace_directory(staging, install_dir)
        executable = install_dir / staged_executable.name
        _write_install_marker(
            marker,
            {
                "source": "godot",
                "tag": download.tag,
                "asset_name": download.asset_name,
                "url": download.url,
            },
        )
        if local_bin.exists() or local_bin.is_symlink():
            local_bin.unlink()
        local_bin.symlink_to(executable)
        context.command.chown_to_target(install_dir)
        context.command.chown_to_target(local_bin)
    finally:
        archive.unlink(missing_ok=True)


def _uninstall_godot(item: SoftwareItem, context: RuntimeContext) -> None:
    script = """
set -Eeuo pipefail
removed=0
for path in "$HOME/.local/bin/godot" "$HOME/.local/share/godot"; do
  if [ -e "$path" ] || [ -L "$path" ]; then
    rm -rf "$path"
    removed=1
  fi
done
if [ "$removed" -eq 0 ]; then
  echo "Godot is not installed"
fi
"""
    context.command.run_as_user_shell(script)


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


def _remove_profile(context: RuntimeContext, block_id: str) -> None:
    if context.command.dry_run:
        print(f"[DRY-RUN] remove {context.host.real_home / '.profile'} block {block_id}")
        return
    remove_profile_block(context.host.real_home, block_id)
    context.command.chown_to_target(context.host.real_home / ".profile")


def _read_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "ubuntu-setup"})
    with urlopen(request, timeout=120) as response:
        return json.load(response)


def _read_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "ubuntu-setup"})
    with urlopen(request, timeout=120) as response:
        return response.read().decode("utf-8", errors="replace")


def _resolve_android_studio_download() -> AndroidStudioDownload:
    html = _read_text(ANDROID_STUDIO_DOWNLOAD_PAGE)
    parser = _AndroidStudioPageParser()
    parser.feed(html)

    for href, text in parser.links:
        filename = _android_studio_filename(href) or _android_studio_filename(text)
        if not filename:
            continue
        checksum = _checksum_after_filename(parser.texts, filename)
        if not checksum:
            raise RuntimeError(f"Could not resolve SHA-256 checksum for {filename}")
        return AndroidStudioDownload(
            url=urljoin(ANDROID_STUDIO_DOWNLOAD_PAGE, href),
            filename=filename,
            sha256=checksum,
            title=text or None,
        )

    match = re.search(r'href=["\']([^"\']*android-studio-[^"\']*linux\.tar\.gz[^"\']*)["\']', html)
    if match:
        href = match.group(1)
        filename = _android_studio_filename(href)
        if filename:
            checksum = _checksum_after_filename(parser.texts, filename)
            if not checksum:
                raise RuntimeError(f"Could not resolve SHA-256 checksum for {filename}")
            return AndroidStudioDownload(
                url=urljoin(ANDROID_STUDIO_DOWNLOAD_PAGE, href),
                filename=filename,
                sha256=checksum,
            )

    raise RuntimeError("Could not resolve the latest Android Studio Linux download")


def _android_studio_filename(value: str) -> str | None:
    match = re.search(r"android-studio-[A-Za-z0-9_.-]*linux\.tar\.gz", value)
    if not match:
        return None
    return match.group(0)


def _checksum_after_filename(texts: list[str], filename: str) -> str | None:
    for index, text in enumerate(texts):
        if filename not in text:
            continue
        checksum = SHA256_RE.search(" ".join(texts[index : index + 25]))
        if checksum:
            return checksum.group(0).lower()
    return None


def _resolve_godot_download() -> GodotDownload:
    release = _read_json(GODOT_RELEASE_URL)
    asset = next(
        asset
        for asset in release["assets"]
        if "linux.x86_64.zip" in asset["name"] and "mono" not in asset["name"]
    )
    return GodotDownload(
        url=str(asset["browser_download_url"]),
        tag=str(release["tag_name"]),
        asset_name=str(asset["name"]),
    )


def _godot_install_current(local_bin: Path, marker: Path, download: GodotDownload) -> bool:
    if not local_bin.exists() and not local_bin.is_symlink():
        return False
    try:
        resolved = local_bin.resolve(strict=True)
    except OSError:
        return False
    if _install_marker_matches(
        marker,
        {
            "source": "godot",
            "tag": download.tag,
            "asset_name": download.asset_name,
            "url": download.url,
        },
    ):
        return True
    return resolved.name == Path(download.asset_name).stem


def _install_marker_matches(marker: Path, expected: dict[str, object]) -> bool:
    data = _read_install_marker(marker)
    if not data:
        return False
    return all(data.get(key) == value for key, value in expected.items())


def _read_install_marker(marker: Path) -> dict[str, object] | None:
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _write_install_marker(marker: Path, data: dict[str, object]) -> None:
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _replace_directory(staging: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup_root: tempfile.TemporaryDirectory[str] | None = None
    backup: Path | None = None
    if destination.exists():
        backup_root = tempfile.TemporaryDirectory(prefix=".ubuntu-setup-backup-", dir=destination.parent)
        backup = Path(backup_root.name) / destination.name
        destination.rename(backup)
    try:
        shutil.move(str(staging), destination)
    except Exception:
        if destination.exists():
            shutil.rmtree(destination)
        if backup and backup.exists():
            backup.rename(destination)
        if backup_root:
            backup_root.cleanup()
        raise
    else:
        if backup_root:
            backup_root.cleanup()


def _verify_sha256(path: Path, expected: str, label: str) -> None:
    digest = _file_sha256(path)
    if digest.lower() != expected.lower():
        raise RuntimeError(f"{label} archive checksum mismatch")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class _AndroidStudioPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.texts: list[str] = []
        self._href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attrs_by_name = dict(attrs)
        href = attrs_by_name.get("href")
        if href:
            self._href = href
            self._link_text = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        self.texts.append(text)
        if self._href:
            self._link_text.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._href:
            return
        self.links.append((self._href, " ".join(self._link_text)))
        self._href = None
        self._link_text = []

