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
fi
. "$HOME/.cargo/env"
rustup default {toolchain}
if [ -n {components!r} ]; then
  rustup component add {components}
fi
"""
        context.command.info(f"Installing {item.title} through rustup")
        context.command.run_as_user_shell(script)
