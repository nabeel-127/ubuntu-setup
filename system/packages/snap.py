from __future__ import annotations

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext


def install_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    _ensure_snapd(context)
    for item in items:
        package = str(item.data["package"])
        if _snap_installed(package, context):
            context.command.info(f"Updating {item.title}: {package}")
            context.command.run(["snap", "refresh", package], sudo=True)
            continue
        args = ["snap", "install", package]
        if item.data.get("classic"):
            args.append("--classic")
        context.command.info(f"Installing {item.title}: {package}")
        context.command.run(args, sudo=True)


def uninstall_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    if not context.command.dry_run and not context.command.command_exists("snap"):
        for item in items:
            context.command.info(f"Not installed: {item.title}")
        return

    for item in items:
        package = str(item.data["package"])
        if not context.command.dry_run and not _snap_installed(package, context):
            context.command.info(f"Not installed: {item.title}")
            continue
        context.command.info(f"Uninstalling {item.title}: {package}")
        context.command.run(["snap", "remove", package], sudo=True)


def _ensure_snapd(context: RuntimeContext) -> None:
    if _apt_package_installed("snapd", context):
        return
    context.command.run(["apt", "install", "-y", "snapd"], sudo=True)


def _snap_installed(package: str, context: RuntimeContext) -> bool:
    if context.command.dry_run:
        return False
    result = context.command.run(["snap", "list", package], capture=True, check=False)
    return result.returncode == 0


def _apt_package_installed(package: str, context: RuntimeContext) -> bool:
    result = context.command.run(
        ["dpkg-query", "-W", "-f=${Status}", package],
        capture=True,
        check=False,
    )
    return result.returncode == 0 and "install ok installed" in result.stdout
