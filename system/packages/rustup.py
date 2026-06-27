from __future__ import annotations

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext


def install_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    for item in items:
        toolchain = str(item.data.get("package", "stable"))
        components = " ".join(str(component) for component in item.data.get("components", []))
        script = f"""
set -Eeuo pipefail
if [ ! -x "$HOME/.cargo/bin/rustup" ]; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
  installed_now=1
else
  installed_now=0
fi
. "$HOME/.cargo/env"
if [ "$installed_now" -eq 0 ]; then
  rustup update {toolchain}
fi
rustup default {toolchain}
if [ -n {components!r} ]; then
  rustup component add {components}
fi
"""
        context.command.info(f"Installing {item.title} through rustup")
        context.command.run_as_user_shell(script)


def uninstall_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    for item in items:
        script = """
set -Eeuo pipefail
if [ ! -x "$HOME/.cargo/bin/rustup" ]; then
  echo "rustup is not installed"
  exit 0
fi
"$HOME/.cargo/bin/rustup" self uninstall -y
"""
        context.command.info(f"Uninstalling {item.title} through rustup")
        context.command.run_as_user_shell(script)
