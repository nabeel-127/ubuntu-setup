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


def uninstall_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    for item in items:
        node_version = str(item.data.get("node_version", "--lts"))
        script = f"""
set -Eeuo pipefail
export NVM_DIR="$HOME/.nvm"
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
  echo "nvm is not installed"
  exit 0
fi
. "$NVM_DIR/nvm.sh"
target={node_version!r}
if [ "$target" = "--lts" ]; then
  version="$(nvm version default 2>/dev/null || true)"
  if [ -z "$version" ] || [ "$version" = "N/A" ]; then
    version="$(nvm version --lts 2>/dev/null || true)"
  fi
else
  version="$(nvm version "$target" 2>/dev/null || true)"
fi
if [ -z "$version" ] || [ "$version" = "N/A" ]; then
  echo "Node.js version is not installed"
  exit 0
fi
nvm deactivate >/dev/null 2>&1 || true
nvm uninstall "$version"
"""
        context.command.info(f"Uninstalling {item.title} through nvm")
        context.command.run_as_user_shell(script)
