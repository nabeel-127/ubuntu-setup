from __future__ import annotations

import argparse
import importlib
import os
import subprocess
import sys
from collections.abc import Sequence

from system.command import CommandRunner
from system.paths import CATEGORIES_CONFIG, LOGGING_CONFIG, SOFTWARE_CONFIG, SOURCES_CONFIG
from system.ubuntu import detect_host


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return _main(argv)
    except (RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


def _main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    _ensure_yaml_dependency(args.dry_run)

    from runtime.catalog import load_catalog, load_categories
    from runtime.categories import validate_item_categories
    from runtime.planner import build_plan
    from runtime.runner import RuntimeContext, run_plan
    from runtime.sources import load_source_order, load_source_titles
    from system.logging import configure_logging

    configure_logging(LOGGING_CONFIG)

    catalog = load_catalog(SOFTWARE_CONFIG)
    categories = load_categories(CATEGORIES_CONFIG)
    validate_item_categories(catalog, categories)
    source_order = load_source_order(SOURCES_CONFIG, catalog.source_names())
    source_titles = {**catalog.source_titles, **load_source_titles(SOURCES_CONFIG)}

    requested_categories = _split_many(args.category)
    requested_sources = _split_many(args.source)
    requested_ids = _split_many(args.only)
    _validate_requested_categories(requested_categories, categories)

    plan = build_plan(
        catalog,
        source_order,
        categories=requested_categories,
        sources=requested_sources,
        only=requested_ids,
    )

    if args.list:
        _print_plan(plan, source_titles)
        return 0

    if not plan.items:
        print("[INFO] No software matched the requested filters.")
        return 0

    host = detect_host(require_ubuntu=not args.dry_run)
    if args.dry_run and not host.is_ubuntu:
        print(f"[WARN] Dry-run is running on non-Ubuntu host: {host.os_id}")
    if os.geteuid() == 0 and not os.environ.get("SUDO_USER"):
        print("[WARN] Running directly as root targets root-owned user tool installs.")

    command = CommandRunner(
        dry_run=args.dry_run,
        target_user=host.real_user,
        target_home=host.real_home,
    )
    context = RuntimeContext(command=command, host=host)
    run_plan(plan, context)
    print("[INFO] Done.")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ubuntu-setup",
        description="Install a configured Ubuntu workstation software catalog.",
    )
    parser.add_argument("--dry-run", action="store_true", help="print commands without changing the system")
    parser.add_argument("--list", action="store_true", help="list matching software grouped by source")
    parser.add_argument("--category", action="append", default=[], help="install/list software from a category")
    parser.add_argument("--source", action="append", default=[], help="install/list software from a source such as apt.ubuntu")
    parser.add_argument("--only", action="append", default=[], help="install/list one software id")
    return parser.parse_args(argv)


def _ensure_yaml_dependency(dry_run: bool) -> None:
    try:
        importlib.import_module("yaml")
        return
    except ImportError:
        pass

    if dry_run:
        raise RuntimeError("PyYAML is required to read config/*.yaml; install python3-yaml or run without --dry-run once.")

    host = detect_host(require_ubuntu=True)
    command = CommandRunner(target_user=host.real_user, target_home=host.real_home)
    command.info("Installing required Python YAML support: python3-yaml")
    command.ensure_sudo()
    command.run(["apt", "update"], sudo=True)
    command.run(["apt", "install", "-y", "python3-yaml"], sudo=True)
    importlib.invalidate_caches()
    importlib.import_module("yaml")


def _split_many(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        result.extend(part.strip() for part in value.split(",") if part.strip())
    return result


def _validate_requested_categories(requested: list[str], categories: dict[str, object]) -> None:
    missing = set(requested) - set(categories)
    if missing:
        raise ValueError(f"Unknown categories: {', '.join(sorted(missing))}")


def _print_plan(plan, source_titles: dict[str, str]) -> None:
    if not plan.items:
        print("No software matched.")
        return

    for source, items in plan.grouped():
        print(f"{source_titles.get(source, source)} ({source})")
        for item in items:
            package_text = _package_text(item)
            categories = ", ".join(item.categories)
            print(f"  - {item.title} [{item.id}]")
            if package_text:
                print(f"    package: {package_text}")
            if categories:
                print(f"    categories: {categories}")


def _package_text(item) -> str:
    if item.data.get("packages"):
        return ", ".join(str(package) for package in item.data["packages"])
    if item.data.get("package_candidates"):
        return " or ".join(str(package) for package in item.data["package_candidates"])
    if item.data.get("package"):
        return str(item.data["package"])
    if item.data.get("method"):
        return str(item.data["method"])
    return ""


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
