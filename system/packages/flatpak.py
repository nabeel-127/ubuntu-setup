from __future__ import annotations

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext


FLATHUB_URL = "https://dl.flathub.org/repo/flathub.flatpakrepo"


def install_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    _ensure_flatpak(context)
    for item in items:
        package = str(item.data["package"])
        if _flatpak_installed(package, context):
            context.command.info(f"Updating {item.title}: {package}")
            context.command.run(["flatpak", "update", "--system", "-y", package], sudo=True)
            continue
        context.command.info(f"Installing {item.title}: {package}")
        context.command.run(["flatpak", "install", "--system", "-y", "flathub", package], sudo=True)


def uninstall_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    if not context.command.dry_run and not context.command.command_exists("flatpak"):
        for item in items:
            context.command.info(f"Not installed: {item.title}")
        return

    for item in items:
        package = str(item.data["package"])
        if not context.command.dry_run and not _flatpak_installed(package, context):
            context.command.info(f"Not installed: {item.title}")
            continue
        context.command.info(f"Uninstalling {item.title}: {package}")
        context.command.run(["flatpak", "uninstall", "--system", "-y", package], sudo=True)


def _ensure_flatpak(context: RuntimeContext) -> None:
    if not _apt_package_installed("flatpak", context):
        context.command.run(["apt", "install", "-y", "flatpak"], sudo=True)
    context.command.run(
        ["flatpak", "remote-add", "--if-not-exists", "--system", "flathub", FLATHUB_URL],
        sudo=True,
    )


def _flatpak_installed(package: str, context: RuntimeContext) -> bool:
    if context.command.dry_run:
        return False
    result = context.command.run(["flatpak", "info", "--system", package], capture=True, check=False)
    return result.returncode == 0


def _apt_package_installed(package: str, context: RuntimeContext) -> bool:
    result = context.command.run(
        ["dpkg-query", "-W", "-f=${Status}", package],
        capture=True,
        check=False,
    )
    return result.returncode == 0 and "install ok installed" in result.stdout
