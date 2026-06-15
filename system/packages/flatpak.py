from __future__ import annotations

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext


FLATHUB_URL = "https://dl.flathub.org/repo/flathub.flatpakrepo"


def install_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    _ensure_flatpak(context)
    for item in items:
        package = str(item.data["package"])
        if _flatpak_installed(package, context):
            context.command.info(f"Already installed: {item.title}")
            continue
        context.command.info(f"Installing {item.title}: {package}")
        context.command.run(["flatpak", "install", "--system", "-y", "flathub", package], sudo=True)


def _ensure_flatpak(context: RuntimeContext) -> None:
    if not context.command.command_exists("flatpak"):
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
