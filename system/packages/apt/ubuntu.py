from __future__ import annotations

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext


def install_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    command = context.command

    for item in items:
        if not _supports_arch(item, context.host.arch):
            command.warn(f"Skipping {item.title}: unsupported architecture {context.host.arch}")
            continue

        for component in item.data.get("enable_components", []):
            command.run(["add-apt-repository", "-y", str(component)], sudo=True)

        for architecture in item.data.get("foreign_architectures", []):
            _ensure_foreign_architecture(str(architecture), context)

    command.run(["apt", "update"], sudo=True)

    for item in items:
        if not _supports_arch(item, context.host.arch):
            continue
        packages = _packages_for_item(item, context)
        missing = [package for package in packages if not _package_installed(package, context)]
        if not missing:
            command.info(f"Already installed: {item.title}")
            _run_post_install(item, context)
            continue
        command.info(f"Installing {item.title}: {', '.join(missing)}")
        command.run(["apt", "install", "-y", *missing], sudo=True)
        _run_post_install(item, context)


def _packages_for_item(item: SoftwareItem, context: RuntimeContext) -> list[str]:
    if item.data.get("resolver") == "dotnet_lts":
        return [_resolve_dotnet_package(context)]

    candidates = item.data.get("package_candidates")
    if isinstance(candidates, list) and candidates:
        if any(_package_installed(str(candidate), context) for candidate in candidates):
            return []
        for candidate in candidates:
            package = str(candidate)
            if _package_available(package, context):
                return [package]
        return [str(candidates[-1])]

    return item.packages


def _resolve_dotnet_package(context: RuntimeContext) -> str:
    for package in ["dotnet-sdk-10.0", "dotnet-sdk-8.0"]:
        if _package_available(package, context):
            return package
    return "dotnet-sdk-10.0"


def _package_installed(package: str, context: RuntimeContext) -> bool:
    result = context.command.run(
        ["dpkg-query", "-W", "-f=${Status}", package],
        capture=True,
        check=False,
    )
    return result.returncode == 0 and "install ok installed" in result.stdout


def _package_available(package: str, context: RuntimeContext) -> bool:
    if context.command.dry_run:
        return True
    result = context.command.run(["apt-cache", "show", package], capture=True, check=False)
    return result.returncode == 0


def _ensure_foreign_architecture(architecture: str, context: RuntimeContext) -> None:
    if architecture == context.host.arch:
        return
    result = context.command.run(
        ["dpkg", "--print-foreign-architectures"],
        capture=True,
        check=False,
    )
    enabled = set(result.stdout.splitlines())
    if architecture in enabled:
        return
    context.command.info(f"Enabling {architecture} architecture support")
    context.command.run(["dpkg", "--add-architecture", architecture], sudo=True)


def _run_post_install(item: SoftwareItem, context: RuntimeContext) -> None:
    for action in item.data.get("post_install", []):
        if action == "pipx_ensurepath":
            context.command.run_as_user_shell("pipx ensurepath || true")


def _supports_arch(item: SoftwareItem, arch: str) -> bool:
    supported = item.data.get("architectures")
    return not supported or arch in supported
