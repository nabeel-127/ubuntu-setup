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


WSL_SANDBOXED_SOURCES = {"snap", "flatpak"}
WSL_DEFAULT_UNCHECKED_FIELD = "default_unchecked_on_wsl"


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return _main(argv)
    except (RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


def _main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if _requires_interactive_selector(args) and (not sys.stdin.isatty() or not sys.stdout.isatty()):
        raise RuntimeError(f"Interactive selector requires a terminal. Re-run interactively or pass --yes to {_action_name(args)} without selection.")
    if args.uninstall and args.yes and not args.list and not _has_filters(args):
        raise RuntimeError("Non-interactive uninstall requires --only, --category, or --source.")
    _ensure_yaml_dependency(args.dry_run)

    from runtime.catalog import load_catalog, load_categories
    from runtime.categories import validate_item_categories
    from runtime.planner import build_plan, build_uninstall_plan, filter_candidates
    from runtime.runner import RuntimeContext, run_plan, run_uninstall_plan
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

    if args.list:
        plan_builder = build_uninstall_plan if args.uninstall else build_plan
        plan = plan_builder(
            catalog,
            source_order,
            categories=requested_categories,
            sources=requested_sources,
            only=requested_ids,
        )
        _print_plan(plan, source_titles)
        return 0

    candidate_items = filter_candidates(
        catalog,
        categories=requested_categories,
        sources=requested_sources,
        only=requested_ids,
    )
    if not candidate_items:
        print("[INFO] No software matched the requested filters.")
        return 0

    host = detect_host(require_ubuntu=not args.dry_run)
    if args.dry_run and not host.is_ubuntu:
        print(f"[WARN] Dry-run is running on non-Ubuntu host: {host.os_id}")
    if os.geteuid() == 0 and not os.environ.get("SUDO_USER"):
        print("[WARN] Running directly as root targets root-owned user tool installs.")

    if args.yes:
        plan_builder = build_uninstall_plan if args.uninstall else build_plan
        plan = plan_builder(
            catalog,
            source_order,
            categories=requested_categories,
            sources=requested_sources,
            only=requested_ids,
        )
    else:
        try:
            from runtime.selector import SelectionCancelled, select_software
        except ModuleNotFoundError as exc:
            if exc.name == "curses":
                raise RuntimeError(f"Interactive selector requires Python curses support. Install python3-curses or pass --yes to {_action_name(args)} without selection.") from exc
            raise
        try:
            selected_ids = select_software(
                candidate_items,
                categories,
                title=f"Select software to {_action_name(args)}",
                selected_by_default=not args.uninstall,
                default_selected_ids=_default_selected_ids(candidate_items, host, args),
            )
        except SelectionCancelled:
            print(f"[INFO] {_action_title(args)} cancelled.")
            return 130
        if not selected_ids:
            print("[INFO] No software selected.")
            return 0
        if args.uninstall:
            plan = build_uninstall_plan(catalog, source_order, only=selected_ids)
        else:
            plan = build_plan(catalog, source_order, only=selected_ids)

    if not plan.items:
        print("[INFO] No software matched the requested filters.")
        return 0

    if not args.uninstall and args.yes:
        plan = _apply_wsl_default_policy(plan, host, args)
        if not plan.items:
            print("[INFO] No software selected after WSL default filtering.")
            return 0

    command = CommandRunner(
        dry_run=args.dry_run,
        target_user=host.real_user,
        target_home=host.real_home,
    )
    context = RuntimeContext(command=command, host=host, catalog_items=catalog.items)
    if args.uninstall:
        summary = run_uninstall_plan(plan, context)
    else:
        summary = run_plan(plan, context)
    if summary.failures:
        _print_failures(summary.failures)
        return 1
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
    parser.add_argument("--yes", action="store_true", help="skip the interactive checklist and apply the action to all matching software")
    parser.add_argument("--uninstall", action="store_true", help="remove selected software instead of installing it")
    parser.add_argument("--include-wsl-skipped", action="store_true", help="include software that is unchecked/skipped by default on WSL")
    parser.add_argument("--include-wsl-sandboxed", action="store_true", help="attempt Snap and Flatpak installs on WSL instead of skipping them")
    return parser.parse_args(argv)


def _requires_interactive_selector(args: argparse.Namespace) -> bool:
    return not args.list and not args.yes


def _has_filters(args: argparse.Namespace) -> bool:
    return bool(args.category or args.source or args.only)


def _action_name(args: argparse.Namespace) -> str:
    return "uninstall" if args.uninstall else "install"


def _action_title(args: argparse.Namespace) -> str:
    return "Uninstall" if args.uninstall else "Installation"


def _default_selected_ids(items, host, args: argparse.Namespace) -> set[str] | None:
    if args.uninstall:
        return None
    if not host.is_wsl or args.include_wsl_skipped:
        return None
    return {item.id for item in items if not _wsl_default_skipped(item, args)}


def _apply_wsl_default_policy(plan, host, args: argparse.Namespace):
    if not host.is_wsl or args.include_wsl_skipped:
        return plan

    skipped = [item for item in plan.items if _wsl_default_skipped(item, args)]
    if not skipped:
        return plan

    item_text = ", ".join(f"{item.title} [{item.id}]" for item in skipped)
    print(f"[WARN] WSL detected; skipping default-unchecked software for this non-interactive run: {item_text}")
    print("[INFO] Use --include-wsl-skipped to include all WSL default-unchecked software.")
    return plan.without_ids({item.id for item in skipped})


def _wsl_default_skipped(item, args: argparse.Namespace) -> bool:
    if not bool(item.data.get(WSL_DEFAULT_UNCHECKED_FIELD, False)):
        return False
    return not (args.include_wsl_sandboxed and item.source in WSL_SANDBOXED_SOURCES)


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


def _print_failures(failures) -> None:
    print("[ERROR] Some software failed:")
    for failure in failures:
        print(f"  - {failure.title} [{failure.item_id}] ({failure.source}): {failure.error}")


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
