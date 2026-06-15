from __future__ import annotations

from runtime.catalog import Catalog


def validate_item_categories(catalog: Catalog, categories: dict[str, object]) -> None:
    known = set(categories)
    unknown: dict[str, list[str]] = {}
    for item in catalog.items:
        missing = [category for category in item.categories if category not in known]
        if missing:
            unknown[item.id] = missing

    if unknown:
        details = "; ".join(
            f"{item_id}: {', '.join(category_names)}"
            for item_id, category_names in sorted(unknown.items())
        )
        raise ValueError(f"Unknown categories in software catalog: {details}")
