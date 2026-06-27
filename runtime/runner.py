from __future__ import annotations

import subprocess
from dataclasses import dataclass
from importlib import import_module

from runtime.catalog import SoftwareItem
from runtime.planner import InstallPlan
from system.command import CommandRunner
from system.ubuntu import UbuntuHost


@dataclass(frozen=True)
class RuntimeContext:
    command: CommandRunner
    host: UbuntuHost
    catalog_items: tuple[SoftwareItem, ...] = ()


@dataclass(frozen=True)
class ItemFailure:
    source: str
    item_id: str
    title: str
    error: str


@dataclass(frozen=True)
class RunSummary:
    failures: tuple[ItemFailure, ...] = ()


ADAPTERS = {
    "apt.ubuntu": "system.packages.apt.ubuntu",
    "apt.external": "system.packages.apt.external",
    "snap": "system.packages.snap",
    "flatpak": "system.packages.flatpak",
    "deb": "system.packages.deb",
    "nvm": "system.packages.nvm",
    "npm": "system.packages.npm",
    "rustup": "system.packages.rustup",
    "vendor_download": "system.packages.vendor_download",
}


BASE_APT_PACKAGES = [
    "ca-certificates",
    "curl",
    "gpg",
    "gnupg",
    "software-properties-common",
    "lsb-release",
    "unzip",
    "tar",
    "xz-utils",
]


ITEM_FAILURE_EXCEPTIONS = (subprocess.CalledProcessError, RuntimeError, OSError)


def run_plan(plan: InstallPlan, context: RuntimeContext) -> RunSummary:
    _repair_configured_sources(context)
    _preconfigure_sources(plan, context)
    _prepare_system(context)
    failures: list[ItemFailure] = []

    for source, items in plan.grouped():
        adapter_path = ADAPTERS.get(source)
        if not adapter_path:
            raise ValueError(f"No package adapter is registered for source {source}")
        context.command.info(f"Installing source group: {source}")
        module = import_module(adapter_path)
        failures.extend(_run_adapter_items(module.install_items, source, items, context))

    return RunSummary(tuple(failures))


def _repair_configured_sources(context: RuntimeContext) -> None:
    if not context.catalog_items:
        return
    by_source: dict[str, list[SoftwareItem]] = {}
    for item in context.catalog_items:
        by_source.setdefault(item.source, []).append(item)

    for source, items in by_source.items():
        adapter_path = ADAPTERS.get(source)
        if not adapter_path:
            continue
        module = import_module(adapter_path)
        repair_source_conflicts = getattr(module, "repair_source_conflicts", None)
        if repair_source_conflicts is None:
            continue
        context.command.info(f"Checking configured source conflicts: {source}")
        repair_source_conflicts(items, context)


def _preconfigure_sources(plan: InstallPlan, context: RuntimeContext) -> None:
    for source, items in plan.grouped():
        adapter_path = ADAPTERS.get(source)
        if not adapter_path:
            raise ValueError(f"No package adapter is registered for source {source}")
        module = import_module(adapter_path)
        preconfigure_items = getattr(module, "preconfigure_items", None)
        if preconfigure_items is None:
            continue
        context.command.info(f"Preparing source group: {source}")
        preconfigure_items(items, context)


def run_uninstall_plan(plan: InstallPlan, context: RuntimeContext) -> RunSummary:
    failures: list[ItemFailure] = []

    for source, items in reversed(plan.grouped()):
        adapter_path = ADAPTERS.get(source)
        if not adapter_path:
            raise ValueError(f"No package adapter is registered for source {source}")
        context.command.info(f"Uninstalling source group: {source}")
        module = import_module(adapter_path)
        uninstall_items = getattr(module, "uninstall_items", None)
        if uninstall_items is None:
            context.command.warn(f"Uninstall is not supported for source group: {source}")
            continue
        failures.extend(_run_adapter_items(uninstall_items, source, items, context))

    return RunSummary(tuple(failures))


def _run_adapter_items(adapter_func, source: str, items: list[SoftwareItem], context: RuntimeContext) -> list[ItemFailure]:
    try:
        adapter_func(items, context)
        return []
    except ITEM_FAILURE_EXCEPTIONS as exc:
        if len(items) == 1:
            return [_failure_for(source, items[0], exc)]

    failures: list[ItemFailure] = []
    for item in items:
        try:
            adapter_func([item], context)
        except ITEM_FAILURE_EXCEPTIONS as exc:
            failures.append(_failure_for(source, item, exc))
    return failures


def _failure_for(source: str, item: SoftwareItem, exc: BaseException) -> ItemFailure:
    return ItemFailure(
        source=source,
        item_id=item.id,
        title=item.title,
        error=_error_text(exc),
    )


def _error_text(exc: BaseException) -> str:
    if isinstance(exc, subprocess.CalledProcessError):
        command = " ".join(str(arg) for arg in exc.cmd)
        detail = (exc.stderr or exc.output or "").strip()
        if detail:
            return f"{command}: {detail}"
        return f"{command} exited with {exc.returncode}"
    return str(exc)


def _prepare_system(context: RuntimeContext) -> None:
    command = context.command
    command.ensure_sudo()
    command.run(["apt", "update"], sudo=True)
    command.run(["apt", "upgrade", "-y"], sudo=True)
    missing = [package for package in BASE_APT_PACKAGES if not _package_installed(package, context)]
    if not missing:
        command.info("Base apt packages already installed")
        return
    command.run(["apt", "install", "-y", *missing], sudo=True)


def _package_installed(package: str, context: RuntimeContext) -> bool:
    result = context.command.run(
        ["dpkg-query", "-W", "-f=${Status}", package],
        capture=True,
        check=False,
    )
    return result.returncode == 0 and "install ok installed" in result.stdout
