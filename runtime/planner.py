from __future__ import annotations

from dataclasses import dataclass

from runtime.catalog import Catalog, SoftwareItem


@dataclass(frozen=True)
class InstallPlan:
    items: tuple[SoftwareItem, ...]
    source_order: tuple[str, ...]

    def grouped(self) -> list[tuple[str, list[SoftwareItem]]]:
        by_source: dict[str, list[SoftwareItem]] = {}
        for item in self.items:
            by_source.setdefault(item.source, []).append(item)

        groups: list[tuple[str, list[SoftwareItem]]] = []
        seen: set[str] = set()
        for source in self.source_order:
            if source in by_source:
                groups.append((source, by_source[source]))
                seen.add(source)
        for source in sorted(set(by_source) - seen):
            groups.append((source, by_source[source]))
        return groups


def build_plan(
    catalog: Catalog,
    source_order: list[str],
    categories: list[str] | None = None,
    sources: list[str] | None = None,
    only: list[str] | None = None,
) -> InstallPlan:
    selected = filter_candidates(
        catalog,
        categories=categories,
        sources=sources,
        only=only,
    )

    return InstallPlan(tuple(_with_dependencies(selected, catalog)), tuple(source_order))


def filter_candidates(
    catalog: Catalog,
    categories: list[str] | None = None,
    sources: list[str] | None = None,
    only: list[str] | None = None,
) -> list[SoftwareItem]:
    selected = [item for item in catalog.items if item.enabled]

    if only:
        requested = set(only)
        known = catalog.by_id()
        missing = requested - set(known)
        if missing:
            raise ValueError(f"Unknown software ids: {', '.join(sorted(missing))}")
        selected = [item for item in selected if item.id in requested]

    if categories:
        requested_categories = set(categories)
        selected = [
            item
            for item in selected
            if requested_categories.intersection(item.categories)
        ]

    if sources:
        requested_sources = set(sources)
        known_sources = catalog.source_names()
        missing_sources = requested_sources - known_sources
        if missing_sources:
            raise ValueError(f"Unknown sources: {', '.join(sorted(missing_sources))}")
        selected = [item for item in selected if item.source in requested_sources]

    return selected


def _with_dependencies(items: list[SoftwareItem], catalog: Catalog) -> list[SoftwareItem]:
    by_id = catalog.by_id()
    expanded: list[SoftwareItem] = []
    added: set[str] = set()

    def add_item(item: SoftwareItem) -> None:
        if item.id in added:
            return
        for dependency_id in item.data.get("depends_on", []):
            dependency = by_id.get(str(dependency_id))
            if dependency is None:
                raise ValueError(f"{item.id} depends on unknown software id {dependency_id}")
            add_item(dependency)
        expanded.append(item)
        added.add(item.id)

    for selected_item in items:
        add_item(selected_item)

    return expanded
