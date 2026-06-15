from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_source_order(path: Path, available_sources: set[str]) -> list[str]:
    configured: list[str] = []
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        order = data.get("order", [])
        if not isinstance(order, list):
            raise ValueError("config/sources.yaml order must be a list")
        configured = [str(source) for source in order]

    ordered = [source for source in configured if source in available_sources]
    ordered.extend(sorted(available_sources - set(ordered)))
    return ordered


def load_source_titles(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data: dict[str, Any] = yaml.safe_load(handle) or {}
    raw_sources = data.get("sources", {})
    if not isinstance(raw_sources, dict):
        return {}
    titles: dict[str, str] = {}
    for source_name, source_data in raw_sources.items():
        if isinstance(source_data, dict) and source_data.get("title"):
            titles[str(source_name)] = str(source_data["title"])
    return titles
