from __future__ import annotations

from pathlib import Path

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext


def install_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    for item in items:
        if not _supports_arch(item, context.host.arch):
            context.command.warn(f"Skipping {item.title}: unsupported architecture {context.host.arch}")
            continue
        _configure_repository(item, context)

    context.command.run(["apt", "update"], sudo=True)

    for item in items:
        if not _supports_arch(item, context.host.arch):
            continue
        missing = [package for package in item.packages if not _package_installed(package, context)]
        if not missing:
            context.command.info(f"Already installed: {item.title}")
            continue
        context.command.info(f"Installing {item.title}: {', '.join(missing)}")
        context.command.run(["apt", "install", "-y", *missing], sudo=True)


def _configure_repository(item: SoftwareItem, context: RuntimeContext) -> None:
    key = item.data.get("key", {})
    if key:
        context.command.install_keyring_from_url(
            str(key["url"]),
            Path(str(key["keyring"])),
            dearmor=bool(key.get("dearmor", True)),
        )

    source = item.data.get("source", {})
    if source:
        content = str(source["content"]).format(
            arch=context.host.arch,
            codename=context.host.codename,
            version=context.host.version_id,
        )
        context.command.root_write_text(Path(str(source["file"])), content)


def _package_installed(package: str, context: RuntimeContext) -> bool:
    result = context.command.run(
        ["dpkg-query", "-W", "-f=${Status}", package],
        capture=True,
        check=False,
    )
    return result.returncode == 0 and "install ok installed" in result.stdout


def _supports_arch(item: SoftwareItem, arch: str) -> bool:
    supported = item.data.get("architectures")
    return not supported or arch in supported
