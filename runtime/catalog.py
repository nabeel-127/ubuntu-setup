from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SoftwareItem:
    id: str
    title: str
    source: str
    data: dict[str, Any]
    categories: tuple[str, ...] = field(default_factory=tuple)
    enabled: bool = True

    @property
    def packages(self) -> list[str]:
        packages = self.data.get("packages")
        if isinstance(packages, list):
            return [str(package) for package in packages]
        package = self.data.get("package")
        if package:
            return [str(package)]
        return []


@dataclass(frozen=True)
class Catalog:
    items: tuple[SoftwareItem, ...]
    source_titles: dict[str, str]

    def by_id(self) -> dict[str, SoftwareItem]:
        return {item.id: item for item in self.items}

    def source_names(self) -> set[str]:
        return {item.source for item in self.items} | set(self.source_titles)


def load_catalog(path: Path) -> Catalog:
    raw = _load_yaml(path)
    sources = raw.get("sources", {})
    items: list[SoftwareItem] = []
    source_titles: dict[str, str] = {}

    for source_name, source_data in sources.items():
        if not isinstance(source_data, dict):
            continue

        direct_software = source_data.get("software")
        if isinstance(direct_software, list):
            title = str(source_data.get("title", source_name))
            source_titles[source_name] = title
            items.extend(_load_items(source_name, direct_software))
            continue

        for child_name, child_data in source_data.items():
            if child_name == "title" or not isinstance(child_data, dict):
                continue
            software = child_data.get("software")
            if not isinstance(software, list):
                continue
            full_source = f"{source_name}.{child_name}"
            title = str(child_data.get("title", full_source))
            source_titles[full_source] = title
            items.extend(_load_items(full_source, software))

    _validate_unique_ids(items)
    return Catalog(tuple(items), source_titles)


def load_categories(path: Path) -> dict[str, dict[str, Any]]:
    raw = _load_yaml(path)
    categories = raw.get("categories", {})
    if not isinstance(categories, dict):
        raise ValueError("config/categories.yaml must contain a categories mapping")
    return categories


def _load_items(source: str, raw_items: list[dict[str, Any]]) -> list[SoftwareItem]:
    items: list[SoftwareItem] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            raise ValueError(f"Invalid software item under {source}: expected mapping")
        item_id = str(raw_item.get("id", "")).strip()
        title = str(raw_item.get("title", "")).strip()
        if not item_id or not title:
            raise ValueError(f"Every software item under {source} needs id and title")
        categories = tuple(str(category) for category in raw_item.get("categories", []))
        enabled = bool(raw_item.get("enabled", True))
        items.append(
            SoftwareItem(
                id=item_id,
                title=title,
                source=source,
                data=raw_item,
                categories=categories,
                enabled=enabled,
            )
        )
    return items


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def _validate_unique_ids(items: list[SoftwareItem]) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for item in items:
        if item.id in seen:
            duplicates.append(item.id)
        seen.add(item.id)
    if duplicates:
        duplicate_text = ", ".join(sorted(set(duplicates)))
        raise ValueError(f"Duplicate software ids: {duplicate_text}")
