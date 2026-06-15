from __future__ import annotations

from system.command import CommandRunner


def command_exists(command: CommandRunner, executable: str) -> bool:
    result = command.run(["bash", "-lc", f"command -v {executable}"], capture=True, check=False)
    return result.returncode == 0
