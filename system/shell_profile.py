from __future__ import annotations

from pathlib import Path


def ensure_profile_block(home: Path, block_id: str, content: str) -> None:
    profile = home / ".profile"
    start = f"# ubuntu-setup:{block_id}:start"
    end = f"# ubuntu-setup:{block_id}:end"
    block = f"{start}\n{content.rstrip()}\n{end}\n"

    existing = profile.read_text(encoding="utf-8") if profile.exists() else ""
    if start in existing and end in existing:
        before, rest = existing.split(start, 1)
        _, after = rest.split(end, 1)
        updated = before.rstrip() + "\n\n" + block + after.lstrip()
    else:
        updated = existing.rstrip() + "\n\n" + block
    profile.write_text(updated, encoding="utf-8")


def remove_profile_block(home: Path, block_id: str) -> None:
    profile = home / ".profile"
    if not profile.exists():
        return

    start = f"# ubuntu-setup:{block_id}:start"
    end = f"# ubuntu-setup:{block_id}:end"
    existing = profile.read_text(encoding="utf-8")
    if start not in existing or end not in existing:
        return

    before, rest = existing.split(start, 1)
    _, after = rest.split(end, 1)
    updated = before.rstrip() + "\n\n" + after.lstrip()
    profile.write_text(updated.rstrip() + "\n", encoding="utf-8")
