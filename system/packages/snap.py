from __future__ import annotations

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext


def install_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    _ensure_snapd(context)
    for item in items:
        package = str(item.data["package"])
        if _snap_installed(package, context):
            context.command.info(f"Already installed: {item.title}")
            continue
        args = ["snap", "install", package]
        if item.data.get("classic"):
            args.append("--classic")
        context.command.info(f"Installing {item.title}: {package}")
        context.command.run(args, sudo=True)


def _ensure_snapd(context: RuntimeContext) -> None:
    if context.command.command_exists("snap"):
        return
    context.command.run(["apt", "install", "-y", "snapd"], sudo=True)


def _snap_installed(package: str, context: RuntimeContext) -> bool:
    if context.command.dry_run:
        return False
    result = context.command.run(["snap", "list", package], capture=True, check=False)
    return result.returncode == 0
