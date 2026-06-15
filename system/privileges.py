from __future__ import annotations

from system.command import CommandRunner


def require_sudo(command: CommandRunner) -> None:
    command.ensure_sudo()
