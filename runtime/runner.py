from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module

from runtime.planner import InstallPlan
from system.command import CommandRunner
from system.ubuntu import UbuntuHost


@dataclass(frozen=True)
class RuntimeContext:
    command: CommandRunner
    host: UbuntuHost


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


def run_plan(plan: InstallPlan, context: RuntimeContext) -> None:
    _prepare_system(context)

    for source, items in plan.grouped():
        adapter_path = ADAPTERS.get(source)
        if not adapter_path:
            raise ValueError(f"No package adapter is registered for source {source}")
        context.command.info(f"Installing source group: {source}")
        module = import_module(adapter_path)
        module.install_items(items, context)


def _prepare_system(context: RuntimeContext) -> None:
    command = context.command
    command.ensure_sudo()
    command.run(["apt", "update"], sudo=True)
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
