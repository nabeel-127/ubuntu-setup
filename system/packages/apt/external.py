from __future__ import annotations

from pathlib import Path

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext


def install_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    pending: list[tuple[SoftwareItem, list[str], list[str]]] = []

    for item in items:
        if not _supports_arch(item, context.host.arch):
            context.command.warn(f"Skipping {item.title}: unsupported architecture {context.host.arch}")
            continue

        missing = [package for package in item.packages if not _package_installed(package, context)]
        conflicts = _installed_conflicts(item, context)
        if missing or conflicts or _repository_needs_configuration(item, context):
            pending.append((item, missing, conflicts))
        else:
            context.command.info(f"Already installed: {item.title}")

    if not pending:
        return

    for item, _missing, conflicts in pending:
        _remove_conflicts(item, conflicts, context)
        _configure_repository(item, context)

    context.command.run(["apt", "update"], sudo=True)

    for item, missing, _conflicts in pending:
        if not missing:
            context.command.info(f"Already installed: {item.title}")
            continue
        context.command.info(f"Installing {item.title}: {', '.join(missing)}")
        context.command.run(["apt", "install", "-y", *missing], sudo=True)


def _configure_repository(item: SoftwareItem, context: RuntimeContext) -> None:
    key = item.data.get("key", {})
    if key:
        context.command.install_keyring_from_url(
            str(key["url"]),
            Path(str(key["keyring"])),
            dearmor=bool(key.get("dearmor", True)),
        )

    source = item.data.get("source", {})
    if source:
        context.command.root_write_text(Path(str(source["file"])), _source_content(source, context))


def _repository_needs_configuration(item: SoftwareItem, context: RuntimeContext) -> bool:
    key = item.data.get("key", {})
    if key and not _path_exists(Path(str(key["keyring"]))):
        return True

    source = item.data.get("source", {})
    if not source:
        return False

    expected = _source_content(source, context)
    if not expected.endswith("\n"):
        expected += "\n"

    try:
        return Path(str(source["file"])).read_text(encoding="utf-8") != expected
    except OSError:
        return True


def _installed_conflicts(item: SoftwareItem, context: RuntimeContext) -> list[str]:
    conflicts = [str(package) for package in item.data.get("conflicts_remove", [])]
    if context.command.dry_run:
        return conflicts
    return [package for package in conflicts if _package_installed(package, context)]


def _remove_conflicts(item: SoftwareItem, conflicts: list[str], context: RuntimeContext) -> None:
    if not conflicts:
        return
    context.command.info(f"Removing conflicting packages before {item.title}: {', '.join(conflicts)}")
    context.command.run(["apt", "remove", "-y", *conflicts], sudo=True)


def _source_content(source: dict[str, object], context: RuntimeContext) -> str:
    return str(source["content"]).format(
        arch=context.host.arch,
        codename=context.host.codename,
        version=context.host.version_id,
    )


def _path_exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def _package_installed(package: str, context: RuntimeContext) -> bool:
    result = context.command.run(
        ["dpkg-query", "-W", "-f=${Status}", package],
        capture=True,
        check=False,
    )
    return result.returncode == 0 and "install ok installed" in result.stdout


def _supports_arch(item: SoftwareItem, arch: str) -> bool:
    supported = item.data.get("architectures")
    return not supported or arch in supported
