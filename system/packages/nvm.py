from __future__ import annotations

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext


def install_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    for item in items:
        install_url = str(item.data["install_url"])
        node_version = str(item.data.get("node_version", "--lts"))
        alias = "lts/*" if node_version == "--lts" else node_version
        script = f"""
set -Eeuo pipefail
export NVM_DIR="$HOME/.nvm"
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
  curl -o- {install_url!r} | bash
fi
. "$NVM_DIR/nvm.sh"
nvm install {node_version}
nvm alias default {alias!r}
node --version
npm --version
"""
        context.command.info(f"Installing {item.title} through nvm")
        context.command.run_as_user_shell(script)
