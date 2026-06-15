from __future__ import annotations

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext


def install_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    for item in items:
        url = item.data.get("url")
        if not url:
            context.command.warn(f"Skipping {item.title}: no deb URL configured")
            continue
        installed_check = item.data.get("installed_command")
        if installed_check and context.command.command_exists(str(installed_check)):
            context.command.info(f"Already installed: {item.title}")
            continue
        if context.command.dry_run:
            print(f"[DRY-RUN] download {url} and install {item.title}")
            continue
        deb = context.command.download_to_temp(str(url), suffix=".deb")
        try:
            context.command.run(["apt", "install", "-y", str(deb)], sudo=True)
        finally:
            deb.unlink(missing_ok=True)
