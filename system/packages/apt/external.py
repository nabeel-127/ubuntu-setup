from __future__ import annotations

from pathlib import Path

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext


APT_SOURCE_DIRS = (Path("/etc/apt/sources.list.d"),)
DISABLED_SOURCE_SUFFIX = ".disabled-by-ubuntu-setup"
SourceFingerprint = tuple[str, str, tuple[str, ...]]


def repair_source_conflicts(items: list[SoftwareItem], context: RuntimeContext) -> None:
    for item in items:
        if not _supports_arch(item, context.host.arch):
            continue
        _disable_source_conflicts(item, context, require_managed_source=True)


def preconfigure_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    for item in items:
        if not _supports_arch(item, context.host.arch):
            continue
        _configure_repository(item, context)


def install_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    pending: list[tuple[SoftwareItem, list[str], list[str], bool]] = []

    for item in items:
        if not _supports_arch(item, context.host.arch):
            context.command.warn(f"Skipping {item.title}: unsupported architecture {context.host.arch}")
            continue

        missing = [package for package in item.packages if not _package_installed(package, context)]
        conflicts = _installed_conflicts(item, context)
        needs_repository_configuration = _repository_needs_configuration(item, context)
        if missing or conflicts or needs_repository_configuration:
            pending.append((item, missing, conflicts, needs_repository_configuration))
        else:
            context.command.info(f"Already installed: {item.title}")

    if not pending:
        return

    for item, _missing, conflicts, needs_repository_configuration in pending:
        _remove_conflicts(item, conflicts, context)
        if needs_repository_configuration:
            _configure_repository(item, context)

    context.command.run(["apt", "update"], sudo=True)

    for item, missing, conflicts, repository_needs_configuration in pending:
        if not missing and not conflicts and not repository_needs_configuration:
            context.command.info(f"Already installed: {item.title}")
            continue
        packages = item.packages if conflicts or repository_needs_configuration else missing
        if not packages:
            context.command.info(f"Already installed: {item.title}")
            continue
        context.command.info(f"Installing {item.title}: {', '.join(packages)}")
        context.command.run(["apt", "install", "-y", *packages], sudo=True)


def uninstall_items(items: list[SoftwareItem], context: RuntimeContext) -> None:
    for item in items:
        if not _supports_arch(item, context.host.arch):
            context.command.warn(f"Skipping {item.title}: unsupported architecture {context.host.arch}")
            continue

        packages = _installed_packages(item.packages, context)
        if not packages:
            context.command.info(f"Not installed: {item.title}")
            continue

        context.command.info(f"Uninstalling {item.title}: {', '.join(packages)}")
        context.command.run(["apt", "remove", "-y", *packages], sudo=True)


def _configure_repository(item: SoftwareItem, context: RuntimeContext) -> None:
    source = item.data.get("source", {})
    if isinstance(source, dict) and source and (not context.catalog_items or not _managed_source_is_current(source, context)):
        _disable_source_conflicts(item, context, require_managed_source=False)

    key = item.data.get("key", {})
    if key:
        context.command.install_keyring_from_url(
            str(key["url"]),
            Path(str(key["keyring"])),
            dearmor=bool(key.get("dearmor", True)),
        )

    if source:
        context.command.root_write_text(Path(str(source["file"])), _source_content(source, context))


def _disable_source_conflicts(item: SoftwareItem, context: RuntimeContext, *, require_managed_source: bool) -> None:
    source = item.data.get("source", {})
    if not isinstance(source, dict) or not source:
        return
    if require_managed_source and not _managed_source_is_current(source, context):
        return

    disabled_paths: set[Path] = set()
    for path in _obsolete_source_files(item):
        _disable_source_file_once(path, context, item, disabled_paths)

    expected = _source_fingerprints(_source_content(source, context))
    if not expected:
        return

    managed_file = Path(str(source["file"]))
    for path in _apt_source_files():
        if _same_path(path, managed_file):
            continue
        try:
            fingerprints = _source_fingerprints(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        if not fingerprints:
            continue
        if fingerprints <= expected:
            _disable_source_file_once(path, context, item, disabled_paths)
        elif fingerprints & expected:
            context.command.warn(f"Mixed apt source file may conflict with {item.title}: {path}")


def _obsolete_source_files(item: SoftwareItem) -> list[Path]:
    return [Path(str(path)) for path in item.data.get("obsolete_source_files", [])]


def _apt_source_files() -> list[Path]:
    files: list[Path] = []
    for directory in APT_SOURCE_DIRS:
        try:
            candidates = sorted(directory.iterdir())
        except OSError:
            continue
        for path in candidates:
            if path.name.endswith(".list") or path.name.endswith(".sources"):
                files.append(path)
    return files


def _disable_source_file(path: Path, context: RuntimeContext, item: SoftwareItem) -> None:
    if not _path_exists(path):
        return
    disabled = path.with_name(f"{path.name}{DISABLED_SOURCE_SUFFIX}")
    context.command.info(f"Disabling conflicting apt source for {item.title}: {path}")
    context.command.run(["mv", "-f", str(path), str(disabled)], sudo=True)


def _disable_source_file_once(path: Path, context: RuntimeContext, item: SoftwareItem, disabled_paths: set[Path]) -> None:
    try:
        normalized = path.resolve()
    except OSError:
        normalized = path.absolute()
    if normalized in disabled_paths:
        return
    disabled_paths.add(normalized)
    _disable_source_file(path, context, item)


def _managed_source_is_current(source: dict[str, object], context: RuntimeContext) -> bool:
    path = Path(str(source["file"]))
    expected = _source_content(source, context)
    if not expected.endswith("\n"):
        expected += "\n"
    try:
        return path.read_text(encoding="utf-8") == expected
    except OSError:
        return False


def _source_fingerprints(content: str) -> set[SourceFingerprint]:
    fingerprints = set()
    for line in content.splitlines():
        fingerprint = _list_source_fingerprint(line)
        if fingerprint:
            fingerprints.add(fingerprint)
    fingerprints.update(_deb822_source_fingerprints(content))
    return fingerprints


def _list_source_fingerprint(line: str) -> SourceFingerprint | None:
    line = line.split("#", 1)[0].strip()
    if not line.startswith(("deb ", "deb-src ")):
        return None

    parts = line.split()
    if len(parts) < 3:
        return None

    index = 1
    if parts[index].startswith("["):
        while index < len(parts) and not parts[index].endswith("]"):
            index += 1
        index += 1

    if index + 1 >= len(parts):
        return None

    return (
        _normalize_uri(parts[index]),
        parts[index + 1],
        tuple(sorted(parts[index + 2 :])),
    )


def _deb822_source_fingerprints(content: str) -> set[SourceFingerprint]:
    fingerprints: set[SourceFingerprint] = set()
    for stanza in content.split("\n\n"):
        fields: dict[str, str] = {}
        for line in stanza.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()

        source_types = set(fields.get("Types", "").split())
        if source_types and not {"deb", "deb-src"} & source_types:
            continue

        uris = fields.get("URIs", "").split()
        suites = fields.get("Suites", "").split()
        components = tuple(sorted(fields.get("Components", "").split()))
        for uri in uris:
            for suite in suites:
                fingerprints.add((_normalize_uri(uri), suite, components))
    return fingerprints


def _normalize_uri(uri: str) -> str:
    return uri.rstrip("/")


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left.absolute() == right.absolute()


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


def _installed_packages(packages: list[str], context: RuntimeContext) -> list[str]:
    if context.command.dry_run:
        return packages
    return [package for package in packages if _package_installed(package, context)]


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
