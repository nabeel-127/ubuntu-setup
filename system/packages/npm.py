from __future__ import annotations

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext


def install_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    for item in items:
        package = str(item.data["package"])
        script = f"""
set -Eeuo pipefail
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  . "$NVM_DIR/nvm.sh"
fi
if npm list -g --depth=0 {package!r} >/dev/null 2>&1; then
  echo "{package} already installed"
else
  npm install -g {package!r}
fi
"""
        context.command.info(f"Installing {item.title} through npm")
        context.command.run_as_user_shell(script)
