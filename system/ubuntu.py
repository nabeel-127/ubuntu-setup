from __future__ import annotations

import getpass
import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UbuntuHost:
    os_id: str
    version_id: str
    codename: str
    arch: str
    real_user: str
    real_home: Path
    is_wsl: bool
    has_systemd: bool

    @property
    def is_ubuntu(self) -> bool:
        return self.os_id == "ubuntu"


def detect_host(*, require_ubuntu: bool) -> UbuntuHost:
    release = _read_os_release()
    os_id = release.get("ID", "unknown")
    if require_ubuntu and os_id != "ubuntu":
        raise RuntimeError(f"ubuntu-setup supports Ubuntu only. Detected: {os_id}")

    real_user = os.environ.get("SUDO_USER") or getpass.getuser()
    real_home = _home_for_user(real_user)

    return UbuntuHost(
        os_id=os_id,
        version_id=release.get("VERSION_ID", ""),
        codename=release.get("UBUNTU_CODENAME") or release.get("VERSION_CODENAME", ""),
        arch=_dpkg_arch(),
        real_user=real_user,
        real_home=real_home,
        is_wsl=_is_wsl(),
        has_systemd=_has_systemd(),
    )


def version_ge(version: str, minimum: str) -> bool:
    result = subprocess.run(
        ["dpkg", "--compare-versions", version, "ge", minimum],
        check=False,
    )
    return result.returncode == 0


def _read_os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    if not path.exists():
        return {}
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key] = value.strip().strip('"')
    return data


def _dpkg_arch() -> str:
    try:
        completed = subprocess.run(
            ["dpkg", "--print-architecture"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )
        return completed.stdout.strip()
    except Exception:
        machine = platform.machine()
        if machine == "x86_64":
            return "amd64"
        if machine == "aarch64":
            return "arm64"
        return machine


def _home_for_user(user: str) -> Path:
    try:
        completed = subprocess.run(
            ["getent", "passwd", user],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )
        return Path(completed.stdout.split(":", 6)[5])
    except Exception:
        return Path.home()


def _is_wsl() -> bool:
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
        return True

    for path in [Path("/proc/version"), Path("/proc/sys/kernel/osrelease")]:
        try:
            text = path.read_text(encoding="utf-8").lower()
        except OSError:
            continue
        if "microsoft" in text or "wsl" in text:
            return True

    return False


def _has_systemd() -> bool:
    return Path("/run/systemd/system").is_dir()
