from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from urllib.request import Request, urlopen

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext


@dataclass(frozen=True)
class DebDownload:
    url: str
    sha512: str | None = None
    version: str | None = None
    channel: str | None = None


def install_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    for item in items:
        if not _supports_arch(item, context.host.arch):
            context.command.warn(f"Skipping {item.title}: unsupported architecture {context.host.arch}")
            continue

        download = _download_for_item(item, context)
        if not download:
            context.command.warn(f"Skipping {item.title}: no deb URL configured")
            continue

        if context.command.dry_run:
            if download.channel:
                print(f"[DRY-RUN] resolve latest {download.channel} deb from {item.data['version_feed']['url']} and install {item.title}")
            else:
                print(f"[DRY-RUN] download {download.url} and install {item.title}")
            continue

        deb = context.command.download_to_temp(download.url, suffix=".deb")
        try:
            if download.sha512:
                _verify_sha512(deb, download.sha512, item)
            metadata = _deb_metadata(deb, context)
            metadata_package = str(metadata.get("Package") or "").strip()
            expected_package = str(item.data.get("package_name") or "").strip()
            if expected_package and metadata_package and expected_package != metadata_package:
                raise RuntimeError(f"{item.title} deb package mismatch: expected {expected_package}, got {metadata_package}")
            package_name = expected_package or metadata_package
            package_version = str(metadata.get("Version") or "").strip()
            if package_name and package_version and _installed_version(package_name, context) == package_version:
                context.command.info(f"Already installed: {item.title} {package_version}")
                continue
            installed_check = item.data.get("installed_command")
            if (not package_name or not package_version) and installed_check and context.command.command_exists(str(installed_check)):
                context.command.info(f"Already installed: {item.title}")
                continue

            context.command.run(["apt", "install", "-y", str(deb)], sudo=True)
        finally:
            deb.unlink(missing_ok=True)


def uninstall_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    for item in items:
        if not _supports_arch(item, context.host.arch):
            context.command.warn(f"Skipping {item.title}: unsupported architecture {context.host.arch}")
            continue

        package_name = str(item.data.get("package_name") or "").strip()
        if not package_name:
            context.command.warn(f"Skipping {item.title}: no deb package_name configured")
            continue

        if not context.command.dry_run and _installed_version(package_name, context) is None:
            context.command.info(f"Not installed: {item.title}")
            continue

        context.command.info(f"Uninstalling {item.title}: {package_name}")
        context.command.run(["apt", "remove", "-y", package_name], sudo=True)


def _download_for_item(item: SoftwareItem, context: RuntimeContext) -> DebDownload | None:
    feed = item.data.get("version_feed")
    if isinstance(feed, dict):
        if context.command.dry_run:
            return DebDownload(
                url=str(feed["url"]),
                channel=str(feed.get("channel", "Stable")),
            )
        return _resolve_version_feed(feed, item)

    url = item.data.get("url")
    if not url:
        return None
    return DebDownload(url=str(url))


def _resolve_version_feed(feed: dict[str, object], item: SoftwareItem) -> DebDownload:
    feed_url = str(feed["url"])
    channel = str(feed.get("channel", "Stable"))
    file_identifier = str(feed.get("file_identifier", ".deb"))
    data = _read_json(feed_url)
    releases = data.get("Releases", [])
    if not isinstance(releases, list):
        raise RuntimeError(f"{item.title} version feed has no Releases list")

    for release in releases:
        if not isinstance(release, dict) or str(release.get("CategoryName", "")) != channel:
            continue
        files = release.get("File", [])
        if not isinstance(files, list):
            continue
        for file_data in files:
            if not isinstance(file_data, dict):
                continue
            identifier = str(file_data.get("Identifier", ""))
            url = str(file_data.get("Url", ""))
            if file_identifier in identifier and url:
                return DebDownload(
                    url=url,
                    sha512=str(file_data.get("Sha512CheckSum") or "") or None,
                    version=str(release.get("Version") or "") or None,
                    channel=channel,
                )

    raise RuntimeError(f"No {channel} deb download found for {item.title}")


def _read_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "ubuntu-setup"})
    with urlopen(request, timeout=120) as response:
        data = json.load(response)
    if not isinstance(data, dict):
        raise RuntimeError(f"{url} did not return a JSON object")
    return data


def _verify_sha512(deb, expected: str, item: SoftwareItem) -> None:
    digest = hashlib.sha512(deb.read_bytes()).hexdigest()
    if digest.lower() != expected.lower():
        raise RuntimeError(f"{item.title} deb checksum mismatch")


def _deb_metadata(deb, context: RuntimeContext) -> dict[str, str]:
    result = context.command.run(
        ["dpkg-deb", "-f", str(deb), "Package", "Version", "Architecture"],
        capture=True,
    )
    metadata: dict[str, str] = {}
    keys = ["Package", "Version", "Architecture"]
    unlabeled: list[str] = []
    for line in result.stdout.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
        else:
            unlabeled.append(line.strip())
    for index, value in enumerate(unlabeled):
        if index < len(keys):
            metadata.setdefault(keys[index], value)
    return metadata


def _installed_version(package: str, context: RuntimeContext) -> str | None:
    result = context.command.run(
        ["dpkg-query", "-W", "-f=${Version}", package],
        capture=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _supports_arch(item: SoftwareItem, arch: str) -> bool:
    supported = item.data.get("architectures")
    return not supported or arch in supported
