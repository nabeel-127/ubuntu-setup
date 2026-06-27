#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

assert_output_contains() {
    local output="$1"
    local expected="$2"
    local context="$3"

    case "$output" in
        *"$expected"*) ;;
        *)
            printf 'Expected %s to contain: %s\nOutput:\n%s\n' "$context" "$expected" "$output" >&2
            exit 1
            ;;
    esac
}

assert_output_not_contains() {
    local output="$1"
    local unexpected="$2"
    local context="$3"

    case "$output" in
        *"$unexpected"*)
            printf 'Expected %s not to contain: %s\nOutput:\n%s\n' "$context" "$unexpected" "$output" >&2
            exit 1
            ;;
    esac
}

assert_unknown_id() {
    local id="$1"
    local output

    if output="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --only "$id" 2>&1)"; then
        printf 'Expected unknown software id to fail: %s\nOutput:\n%s\n' "$id" "$output" >&2
        exit 1
    fi

    assert_output_contains "$output" "Unknown software ids: $id" "--only $id failure output"
}

PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from pathlib import Path

paths = [Path("bootstrap.py"), Path("main.py")]
paths.extend(Path("runtime").glob("*.py"))
paths.extend(Path("system").glob("*.py"))
paths.extend(Path("system/packages").glob("*.py"))
paths.extend(Path("system/packages/apt").glob("*.py"))

for path in paths:
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY

help_output="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --help)"
assert_output_contains "$help_output" "--yes" "--help output"
assert_output_contains "$help_output" "--uninstall" "--help output"
assert_output_contains "$help_output" "--include-wsl-skipped" "--help output"
assert_output_contains "$help_output" "--include-wsl-sandboxed" "--help output"
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --uninstall --only git >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --source apt.ubuntu >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --source npm >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --category programming >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --only git >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --only dropbox >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --only codex >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --only discord >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --only proton-mail >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --only docker >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --only android-studio >/dev/null

PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import builtins
import contextlib
import io

import bootstrap

real_import = builtins.__import__


def blocked_import(name, *args, **kwargs):
    if name == "curses":
        raise ModuleNotFoundError("No module named curses", name="curses")
    return real_import(name, *args, **kwargs)


builtins.__import__ = blocked_import
stdout = io.StringIO()
try:
    with contextlib.redirect_stdout(stdout):
        code = bootstrap.main(["--list", "--only", "git"])
finally:
    builtins.__import__ = real_import

assert code == 0
assert "Git [git]" in stdout.getvalue()
PY

PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import contextlib
import importlib
import io

import bootstrap

real_import_module = importlib.import_module


def blocked_import_module(name, *args, **kwargs):
    if name == "yaml":
        raise AssertionError("YAML bootstrap ran before the non-TTY selector guard")
    return real_import_module(name, *args, **kwargs)


importlib.import_module = blocked_import_module
stderr = io.StringIO()
try:
    with contextlib.redirect_stderr(stderr):
        code = bootstrap.main(["--only", "git"])
finally:
    importlib.import_module = real_import_module

assert code == 1
assert "Interactive selector requires a terminal" in stderr.getvalue()
PY

if output="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --dry-run --only git 2>&1)"; then
    printf 'Expected non-interactive install without --yes to fail.\nOutput:\n%s\n' "$output" >&2
    exit 1
fi
assert_output_contains "$output" "Interactive selector requires a terminal" "non-interactive install output"

if output="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --uninstall --dry-run --only git 2>&1)"; then
    printf 'Expected non-interactive uninstall without --yes to fail.\nOutput:\n%s\n' "$output" >&2
    exit 1
fi
assert_output_contains "$output" "Interactive selector requires a terminal" "non-interactive uninstall output"

if output="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --uninstall --yes --dry-run 2>&1)"; then
    printf 'Expected non-interactive uninstall without filters to fail.\nOutput:\n%s\n' "$output" >&2
    exit 1
fi
assert_output_contains "$output" "Non-interactive uninstall requires --only, --category, or --source" "unfiltered uninstall output"

git_install_dry_run="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --yes --dry-run --only git)"
assert_output_contains "$git_install_dry_run" "sudo apt update" "--dry-run --only git output"
assert_output_contains "$git_install_dry_run" "sudo apt upgrade -y" "--dry-run --only git output"
assert_output_contains "$git_install_dry_run" "Installing Git: git" "--dry-run --only git output"
git_uninstall_dry_run="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --uninstall --yes --dry-run --only git)"
assert_output_contains "$git_uninstall_dry_run" "Uninstalling source group: apt.ubuntu" "--uninstall --only git output"
assert_output_contains "$git_uninstall_dry_run" "apt remove -y git" "--uninstall --only git output"
discord_uninstall_dry_run="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --uninstall --yes --dry-run --only discord)"
assert_output_contains "$discord_uninstall_dry_run" "Uninstalling source group: deb" "--uninstall --only discord output"
assert_output_contains "$discord_uninstall_dry_run" "apt remove -y discord" "--uninstall --only discord output"
proton_dry_run="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --yes --dry-run --only proton-mail)"
assert_output_contains "$proton_dry_run" "resolve latest Stable deb from https://proton.me/download/mail/linux/version.json" "--dry-run --only proton-mail output"
proton_uninstall_dry_run="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --uninstall --yes --dry-run --only proton-mail)"
assert_output_contains "$proton_uninstall_dry_run" "Uninstalling source group: deb" "--uninstall --only proton-mail output"
assert_output_contains "$proton_uninstall_dry_run" "apt remove -y proton-mail" "--uninstall --only proton-mail output"
docker_dry_run="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --yes --dry-run --only docker)"
assert_output_contains "$docker_dry_run" "/etc/apt/sources.list.d/docker.sources" "--dry-run --only docker output"
assert_output_contains "$docker_dry_run" "apt remove -y docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc" "--dry-run --only docker output"
assert_output_contains "$docker_dry_run" "docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin" "--dry-run --only docker output"
snap_dry_run="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --include-wsl-sandboxed --yes --dry-run --source snap)"
assert_output_contains "$snap_dry_run" "sudo apt install -y snapd" "--dry-run --source snap output"
assert_output_not_contains "$snap_dry_run" "proton-mail" "--dry-run --source snap output"
flatpak_dry_run="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --include-wsl-sandboxed --yes --dry-run --source flatpak)"
assert_output_contains "$flatpak_dry_run" "sudo apt install -y flatpak" "--dry-run --source flatpak output"
wsl_snap_dry_run="$(WSL_DISTRO_NAME=Ubuntu PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --yes --dry-run --source snap)"
assert_output_contains "$wsl_snap_dry_run" "WSL detected; skipping default-unchecked software" "WSL --source snap output"
assert_output_not_contains "$wsl_snap_dry_run" "snap install" "WSL --source snap output"
wsl_snap_override="$(WSL_DISTRO_NAME=Ubuntu PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --include-wsl-sandboxed --yes --dry-run --source snap)"
assert_output_contains "$wsl_snap_override" "sudo snap install whatsapp-desktop-client" "WSL override --source snap output"
wsl_dropbox_dry_run="$(WSL_DISTRO_NAME=Ubuntu PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --yes --dry-run --only dropbox)"
assert_output_contains "$wsl_dropbox_dry_run" "WSL detected; skipping default-unchecked software" "WSL --only dropbox output"
assert_output_not_contains "$wsl_dropbox_dry_run" "apt install -y python3-gpg dropbox" "WSL --only dropbox output"
wsl_dropbox_override="$(WSL_DISTRO_NAME=Ubuntu PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --include-wsl-skipped --yes --dry-run --only dropbox)"
assert_output_contains "$wsl_dropbox_override" "apt install -y python3-gpg dropbox" "WSL override --only dropbox output"
wsl_git_dry_run="$(WSL_DISTRO_NAME=Ubuntu PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --yes --dry-run --only git)"
assert_output_contains "$wsl_git_dry_run" "Installing Git: git" "WSL --only git output"

PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import os
import pty
import select
import subprocess
import time


def run_pty(args: list[str], keys: bytes, extra_env: dict[str, str] | None = None) -> tuple[int, str]:
    master, slave = pty.openpty()
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["TERM"] = "xterm"
    if extra_env:
        env.update(extra_env)
    process = subprocess.Popen(
        ["./ubuntu-setup", *args],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
        env=env,
    )
    os.close(slave)
    output = bytearray()
    deadline = time.monotonic() + 15
    try:
        ready_deadline = time.monotonic() + 2
        while time.monotonic() < ready_deadline and process.poll() is None:
            readable, _, _ = select.select([master], [], [], 0.1)
            if not readable:
                continue
            try:
                output.extend(os.read(master, 4096))
            except OSError:
                break
            if b"Space toggles" in output or b"Select software" in output:
                break
        os.write(master, keys)
        while process.poll() is None and time.monotonic() < deadline:
            readable, _, _ = select.select([master], [], [], 0.1)
            if readable:
                try:
                    output.extend(os.read(master, 4096))
                except OSError:
                    break
        if process.poll() is None:
            process.kill()
            raise AssertionError("interactive selector test timed out")
        while True:
            readable, _, _ = select.select([master], [], [], 0)
            if not readable:
                break
            try:
                chunk = os.read(master, 4096)
            except OSError:
                break
            if not chunk:
                break
            output.extend(chunk)
    finally:
        os.close(master)
    return process.returncode, output.decode(errors="replace")


code, output = run_pty(["--dry-run", "--only", "git"], b"\n")
assert code == 0, output
assert "Installing Git: git" in output, output

code, output = run_pty(["--dry-run", "--only", "git"], b"q")
assert code == 130, output
assert "Installation cancelled" in output, output

code, output = run_pty(["--dry-run", "--only", "git"], b"n\n")
assert code == 0, output
assert "No software selected" in output, output

code, output = run_pty(["--uninstall", "--dry-run", "--only", "git"], b"\n")
assert code == 0, output
assert "No software selected" in output, output

code, output = run_pty(["--uninstall", "--dry-run", "--only", "git"], b" \n")
assert code == 0, output
assert "Uninstalling Git: git" in output, output
assert "apt remove -y git" in output, output

code, output = run_pty(["--dry-run", "--source", "snap"], b"\n", {"WSL_DISTRO_NAME": "Ubuntu"})
assert code == 0, output
assert "No software selected" in output, output
assert "snap install" not in output, output

code, output = run_pty(["--dry-run", "--source", "snap"], b" \n", {"WSL_DISTRO_NAME": "Ubuntu"})
assert code == 0, output
assert "sudo snap install whatsapp-desktop-client" in output, output
PY

PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from pathlib import Path

from runtime.catalog import load_catalog
from runtime.planner import build_uninstall_plan, filter_candidates

catalog = load_catalog(Path("config/software.yaml"))

assert [item.id for item in filter_candidates(catalog, only=["git"])] == ["git"]
assert [item.id for item in filter_candidates(catalog, sources=["deb"])] == ["discord", "proton-mail"]
assert "docker" in [item.id for item in filter_candidates(catalog, categories=["programming"])]
assert [item.id for item in build_uninstall_plan(catalog, [], only=["git"]).items] == ["git"]
PY

PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import contextlib
import io
import sys
import types
from pathlib import Path

from runtime.catalog import SoftwareItem
from runtime.planner import InstallPlan
from runtime.runner import ADAPTERS, RuntimeContext, run_plan
from system.command import CommandRunner
from system.ubuntu import UbuntuHost

module = types.ModuleType("fake_failure_adapter")
calls = []


def install_items(items, context):
    if len(items) > 1:
        raise RuntimeError("group failed")
    item = items[0]
    if item.id == "bad":
        raise RuntimeError("bad failed")
    calls.append(item.id)


module.install_items = install_items
sys.modules[module.__name__] = module
ADAPTERS["test.failure"] = module.__name__
try:
    plan = InstallPlan(
        (
            SoftwareItem(id="good", title="Good", source="test.failure", data={}),
            SoftwareItem(id="bad", title="Bad", source="test.failure", data={}),
        ),
        ("test.failure",),
    )
    host = UbuntuHost(
        os_id="ubuntu",
        version_id="24.04",
        codename="noble",
        arch="amd64",
        real_user="nabeel",
        real_home=Path("/home/nabeel"),
        is_wsl=False,
        has_systemd=True,
    )
    with contextlib.redirect_stdout(io.StringIO()):
        summary = run_plan(plan, RuntimeContext(CommandRunner(dry_run=True), host))
finally:
    ADAPTERS.pop("test.failure", None)
    sys.modules.pop(module.__name__, None)

assert calls == ["good"]
assert len(summary.failures) == 1
assert summary.failures[0].item_id == "bad"
assert "bad failed" in summary.failures[0].error
PY

PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import tempfile
from pathlib import Path

from runtime.catalog import SoftwareItem
from runtime.runner import RuntimeContext
from system.command import CommandResult
from system.ubuntu import UbuntuHost
import system.packages.apt.external as external
import system.packages.deb as deb
import system.packages.flatpak as flatpak
import system.packages.npm as npm
import system.packages.rustup as rustup
import system.packages.snap as snap
import system.packages.vendor_download as vendor_download


class FakeCommand:
    dry_run = False

    def __init__(self):
        self.calls = []
        self.scripts = []
        self.writes = []
        self.keyrings = []
        self._temps = []

    def run(self, args, *, sudo=False, capture=False, check=True, env=None, cwd=None, input_text=None):
        self.calls.append((list(args), sudo))
        return CommandResult(list(args), 0, "", "")

    def run_as_user_shell(self, script, *, capture=False, check=True):
        self.scripts.append(script)
        return CommandResult(["bash", "-lc", script], 0, "", "")

    def download_to_temp(self, url, *, suffix=""):
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        handle.close()
        path = Path(handle.name)
        self._temps.append(path)
        return path

    def root_write_text(self, destination, content, mode="0644"):
        self.writes.append((Path(destination), content, mode))

    def install_keyring_from_url(self, url, destination, *, dearmor=True):
        self.keyrings.append((url, Path(destination), dearmor))

    def info(self, message):
        pass

    def warn(self, message):
        pass


host = UbuntuHost(
    os_id="ubuntu",
    version_id="24.04",
    codename="noble",
    arch="amd64",
    real_user="nabeel",
    real_home=Path("/home/nabeel"),
    is_wsl=False,
    has_systemd=True,
)


def context():
    return RuntimeContext(FakeCommand(), host)


item = SoftwareItem(
    id="edge",
    title="Microsoft Edge",
    source="apt.external",
    data={"packages": ["microsoft-edge-stable"]},
)
ctx = context()
original_package_installed = external._package_installed
original_repository_needs_configuration = external._repository_needs_configuration
try:
    external._package_installed = lambda package, _context: package == "microsoft-edge-stable"
    external._repository_needs_configuration = lambda _item, _context: True
    external.install_items([item], ctx)
finally:
    external._package_installed = original_package_installed
    external._repository_needs_configuration = original_repository_needs_configuration
assert (["apt", "install", "-y", "microsoft-edge-stable"], True) in ctx.command.calls

item = SoftwareItem(
    id="mixed",
    title="Mixed External",
    source="apt.external",
    data={"packages": ["installed-pkg", "missing-pkg"]},
)
ctx = context()
original_package_installed = external._package_installed
original_repository_needs_configuration = external._repository_needs_configuration
try:
    external._package_installed = lambda package, _context: package == "installed-pkg"
    external._repository_needs_configuration = lambda _item, _context: True
    external.install_items([item], ctx)
finally:
    external._package_installed = original_package_installed
    external._repository_needs_configuration = original_repository_needs_configuration
assert (["apt", "install", "-y", "installed-pkg", "missing-pkg"], True) in ctx.command.calls

with tempfile.TemporaryDirectory() as temp_dir:
    temp_path = Path(temp_dir)
    managed = temp_path / "warpdotdev.list"
    stale = temp_path / "warpdotdev.sources"
    managed.write_text(
        "deb [arch=amd64 signed-by=/etc/apt/keyrings/warpdotdev.gpg] https://releases.warp.dev/linux/deb stable main\n",
        encoding="utf-8",
    )
    stale.write_text(
        """Types: deb
URIs: https://releases.warp.dev/linux/deb
Suites: stable
Components: main
Signed-By: /etc/apt/trusted.gpg.d/warpdotdev.gpg
""",
        encoding="utf-8",
    )
    warp_item = SoftwareItem(
        id="warp",
        title="Warp",
        source="apt.external",
        data={
            "packages": ["warp-terminal"],
            "architectures": ["amd64"],
            "source": {
                "file": str(managed),
                "content": managed.read_text(encoding="utf-8"),
            },
            "obsolete_source_files": [str(stale)],
        },
    )
    ctx = context()
    original_source_dirs = external.APT_SOURCE_DIRS
    try:
        external.APT_SOURCE_DIRS = (temp_path,)
        external.repair_source_conflicts([warp_item], ctx)
    finally:
        external.APT_SOURCE_DIRS = original_source_dirs
    assert (["mv", "-f", str(stale), f"{stale}.disabled-by-ubuntu-setup"], True) in ctx.command.calls

snap_item = SoftwareItem(id="whatsapp", title="WhatsApp", source="snap", data={"package": "whatsapp-desktop-client"})
ctx = context()
original_snapd_installed = snap._apt_package_installed
original_snap_installed = snap._snap_installed
try:
    snap._apt_package_installed = lambda _package, _context: True
    snap._snap_installed = lambda _package, _context: True
    snap.install_items([snap_item], ctx)
finally:
    snap._apt_package_installed = original_snapd_installed
    snap._snap_installed = original_snap_installed
assert (["snap", "refresh", "whatsapp-desktop-client"], True) in ctx.command.calls

flatpak_item = SoftwareItem(id="bottles", title="Bottles", source="flatpak", data={"package": "com.usebottles.bottles"})
ctx = context()
original_flatpak_installed = flatpak._apt_package_installed
original_app_installed = flatpak._flatpak_installed
try:
    flatpak._apt_package_installed = lambda _package, _context: True
    flatpak._flatpak_installed = lambda _package, _context: True
    flatpak.install_items([flatpak_item], ctx)
finally:
    flatpak._apt_package_installed = original_flatpak_installed
    flatpak._flatpak_installed = original_app_installed
assert (["flatpak", "update", "--system", "-y", "com.usebottles.bottles"], True) in ctx.command.calls

npm_item = SoftwareItem(id="example", title="Example", source="npm", data={"package": "example-package"})
ctx = context()
npm.install_items([npm_item], ctx)
assert "npm update -g 'example-package'" in ctx.command.scripts[0]

rust_item = SoftwareItem(id="rust", title="Rust", source="rustup", data={"package": "stable", "components": ["rustfmt"]})
ctx = context()
rustup.install_items([rust_item], ctx)
assert "rustup update stable" in ctx.command.scripts[0]

deb_item = SoftwareItem(
    id="discord",
    title="Discord",
    source="deb",
    data={"url": "https://example.invalid/discord.deb", "package_name": "discord"},
)
ctx = context()
original_deb_metadata = deb._deb_metadata
original_installed_version = deb._installed_version
try:
    deb._deb_metadata = lambda _path, _context: {"Package": "discord", "Version": "1.0"}
    deb._installed_version = lambda _package, _context: "1.0"
    deb.install_items([deb_item], ctx)
finally:
    deb._deb_metadata = original_deb_metadata
    deb._installed_version = original_installed_version
    for path in ctx.command._temps:
        path.unlink(missing_ok=True)
assert not any(call[0][:3] == ["apt", "install", "-y"] for call in ctx.command.calls)

ctx = context()
original_deb_metadata = deb._deb_metadata
original_installed_version = deb._installed_version
try:
    deb._deb_metadata = lambda _path, _context: {"Package": "not-discord", "Version": "1.0"}
    deb._installed_version = lambda _package, _context: None
    try:
        deb.install_items([deb_item], ctx)
    except RuntimeError as exc:
        assert "deb package mismatch" in str(exc)
    else:
        raise AssertionError("expected deb package mismatch")
finally:
    deb._deb_metadata = original_deb_metadata
    deb._installed_version = original_installed_version
    for path in ctx.command._temps:
        path.unlink(missing_ok=True)

html = """
<a href="https://edgedl.me.gvt1.com/android/studio/ide-zips/2026.1.1.10/android-studio-quail1-patch2-linux.tar.gz">Download</a>
<span>android-studio-quail1-patch2-linux.tar.gz</span>
<span>1.5 GB</span>
<span>fbd3f116d12caed724ea8da0d2cdae7e791170f79f2aa11273ea0f2d22a224dc</span>
"""
original_read_text = vendor_download._read_text
try:
    vendor_download._read_text = lambda _url: html
    download = vendor_download._resolve_android_studio_download()
finally:
    vendor_download._read_text = original_read_text
assert download.filename == "android-studio-quail1-patch2-linux.tar.gz"
assert download.sha256 == "fbd3f116d12caed724ea8da0d2cdae7e791170f79f2aa11273ea0f2d22a224dc"

html_without_checksum = """
<a href="https://edgedl.me.gvt1.com/android/studio/ide-zips/2026.1.1.10/android-studio-quail1-patch2-linux.tar.gz">Download</a>
<span>android-studio-quail1-patch2-linux.tar.gz</span>
"""
original_read_text = vendor_download._read_text
try:
    vendor_download._read_text = lambda _url: html_without_checksum
    try:
        vendor_download._resolve_android_studio_download()
    except RuntimeError as exc:
        assert "SHA-256 checksum" in str(exc)
    else:
        raise AssertionError("expected Android Studio checksum resolution failure")
finally:
    vendor_download._read_text = original_read_text

with tempfile.TemporaryDirectory() as temp_dir:
    root = Path(temp_dir)
    executable = root / "share" / "godot" / "Godot_v4.7-stable_linux.x86_64"
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")
    local_bin = root / "bin" / "godot"
    local_bin.parent.mkdir()
    local_bin.symlink_to(executable)
    assert vendor_download._godot_install_current(
        local_bin,
        executable.parent / ".ubuntu-setup-install.json",
        vendor_download.GodotDownload(
            url="https://example.invalid/Godot_v4.7-stable_linux.x86_64.zip",
            tag="4.7-stable",
            asset_name="Godot_v4.7-stable_linux.x86_64.zip",
        ),
    )

with tempfile.TemporaryDirectory() as temp_dir:
    root = Path(temp_dir)
    local_bin = root / "bin" / "godot"
    local_bin.parent.mkdir()
    local_bin.symlink_to(root / "missing-godot")
    marker = root / "share" / "godot" / ".ubuntu-setup-install.json"
    vendor_download._write_install_marker(
        marker,
        {
            "source": "godot",
            "tag": "4.7-stable",
            "asset_name": "Godot_v4.7-stable_linux.x86_64.zip",
            "url": "https://example.invalid/Godot_v4.7-stable_linux.x86_64.zip",
        },
    )
    assert not vendor_download._godot_install_current(
        local_bin,
        marker,
        vendor_download.GodotDownload(
            url="https://example.invalid/Godot_v4.7-stable_linux.x86_64.zip",
            tag="4.7-stable",
            asset_name="Godot_v4.7-stable_linux.x86_64.zip",
        ),
    )
PY

mapfile -t catalog_ids < <(
    PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from pathlib import Path

from runtime.catalog import load_catalog

for item in load_catalog(Path("config/software.yaml")).items:
    if item.enabled:
        print(item.id)
PY
)

for id in "${catalog_ids[@]}"; do
    PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --only "$id" >/dev/null
done

for id in \
    go \
    maven \
    dart \
    crystal \
    chromedriver \
    android-sdk-command-line-tools \
    android-platform-tools \
    android-ndk \
    teams-for-linux \
    outlook-wrapper \
    swiftly
do
    assert_unknown_id "$id"
done

communication_output="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --category communication)"
assert_output_not_contains "$communication_output" "Microsoft Teams Wrapper [teams-for-linux]" "--category communication output"
assert_output_not_contains "$communication_output" "Outlook Wrapper [outlook-wrapper]" "--category communication output"
assert_output_contains "$communication_output" "Proton Mail [proton-mail]" "--category communication output"

mobile_output="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --category mobile)"
assert_output_contains "$mobile_output" "Flutter SDK [flutter]" "--category mobile output"
assert_output_contains "$mobile_output" "Android Studio [android-studio]" "--category mobile output"
assert_output_not_contains "$mobile_output" "Android SDK Command-line Tools [android-sdk-command-line-tools]" "--category mobile output"
assert_output_not_contains "$mobile_output" "Android Platform Tools [android-platform-tools]" "--category mobile output"
assert_output_not_contains "$mobile_output" "Android NDK [android-ndk]" "--category mobile output"

programming_output="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --category programming)"
assert_output_not_contains "$programming_output" "Go [go]" "--category programming output"
assert_output_not_contains "$programming_output" "Maven [maven]" "--category programming output"
assert_output_not_contains "$programming_output" "Dart SDK [dart]" "--category programming output"
assert_output_not_contains "$programming_output" "Crystal [crystal]" "--category programming output"
assert_output_not_contains "$programming_output" "ChromeDriver [chromedriver]" "--category programming output"
assert_output_not_contains "$programming_output" "Android SDK Command-line Tools [android-sdk-command-line-tools]" "--category programming output"
assert_output_not_contains "$programming_output" "Android Platform Tools [android-platform-tools]" "--category programming output"
assert_output_not_contains "$programming_output" "Android NDK [android-ndk]" "--category programming output"

vendor_output="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --source vendor_download)"
assert_output_contains "$vendor_output" "OpenAI Codex CLI [codex]" "--source vendor_download output"
assert_output_not_contains "$vendor_output" "Swiftly [swiftly]" "--source vendor_download output"
vendor_dry_run="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --yes --dry-run --source vendor_download)"
assert_output_contains "$vendor_dry_run" "resolve latest Android Studio Linux tarball from https://developer.android.com/studio" "--dry-run --source vendor_download output"

external_output="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --source apt.external)"
assert_output_contains "$external_output" "Docker Engine [docker]" "--source apt.external output"

deb_output="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --source deb)"
assert_output_contains "$deb_output" "Discord [discord]" "--source deb output"
assert_output_contains "$deb_output" "Proton Mail [proton-mail]" "--source deb output"

echo "Smoke tests passed."
