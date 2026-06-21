from __future__ import annotations

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext


def install_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    for item in items:
        if not _supports_arch(item, context.host.arch):
            context.command.warn(f"Skipping {item.title}: unsupported architecture {context.host.arch}")
            continue

        url = item.data.get("url")
        if not url:
            context.command.warn(f"Skipping {item.title}: no deb URL configured")
            continue

        if context.command.dry_run:
            print(f"[DRY-RUN] download {url} and install {item.title}")
            continue

        deb = context.command.download_to_temp(str(url), suffix=".deb")
        try:
            metadata = _deb_metadata(deb, context)
            package_name = str(item.data.get("package_name") or metadata.get("Package") or "").strip()
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
