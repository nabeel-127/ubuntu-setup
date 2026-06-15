from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""


class CommandRunner:
    def __init__(
        self,
        *,
        dry_run: bool = False,
        target_user: str | None = None,
        target_home: Path | None = None,
    ) -> None:
        self.dry_run = dry_run
        self.target_user = target_user or os.environ.get("SUDO_USER") or os.environ.get("USER") or "root"
        self.target_home = target_home or Path.home()

    def info(self, message: str) -> None:
        print(f"[INFO] {message}")

    def warn(self, message: str) -> None:
        print(f"[WARN] {message}")

    def run(
        self,
        args: list[str],
        *,
        sudo: bool = False,
        capture: bool = False,
        check: bool = True,
        env: dict[str, str] | None = None,
        cwd: Path | None = None,
        input_text: str | None = None,
    ) -> CommandResult:
        full_args = self._with_sudo(args) if sudo else args

        if self.dry_run:
            print(f"[DRY-RUN] {self._quote(full_args)}")
            return CommandResult(full_args, 0)

        completed = subprocess.run(
            full_args,
            check=False,
            text=True,
            input=input_text,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            env=env,
            cwd=str(cwd) if cwd else None,
        )
        if check and completed.returncode != 0:
            raise subprocess.CalledProcessError(
                completed.returncode,
                full_args,
                output=completed.stdout,
                stderr=completed.stderr,
            )
        return CommandResult(
            full_args,
            completed.returncode,
            completed.stdout or "",
            completed.stderr or "",
        )

    def run_as_user_shell(
        self,
        script: str,
        *,
        capture: bool = False,
        check: bool = True,
    ) -> CommandResult:
        if self.dry_run:
            print(f"[DRY-RUN] as {self.target_user}: {script}")
            return CommandResult(["bash", "-lc", script], 0)

        env = os.environ.copy()
        env["HOME"] = str(self.target_home)

        if os.geteuid() == 0 and self.target_user != "root":
            args = ["sudo", "-u", self.target_user, "env", f"HOME={self.target_home}", "bash", "-lc", script]
            return self.run(args, capture=capture, check=check)

        return self.run(["bash", "-lc", script], capture=capture, check=check, env=env)

    def ensure_sudo(self) -> None:
        if os.geteuid() == 0:
            return
        if shutil.which("sudo") is None:
            raise RuntimeError("sudo is required")
        if self.dry_run:
            return
        self.run(["sudo", "-v"])

    def command_exists(self, executable: str) -> bool:
        return shutil.which(executable) is not None

    def root_write_text(self, destination: Path, content: str, mode: str = "0644") -> None:
        if not content.endswith("\n"):
            content += "\n"

        if self.dry_run:
            print(f"[DRY-RUN] write {destination}")
            return

        if destination.exists() and destination.read_text(encoding="utf-8") == content:
            self.info(f"File already up to date: {destination}")
            return

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write(content)
            temp_name = handle.name

        try:
            self.run(["install", "-D", "-m", mode, temp_name, str(destination)], sudo=True)
        finally:
            Path(temp_name).unlink(missing_ok=True)

    def install_keyring_from_url(self, url: str, destination: Path, *, dearmor: bool = True) -> None:
        if self.dry_run:
            print(f"[DRY-RUN] install keyring from {url} to {destination}")
            return

        raw_key = self.download_to_temp(url, suffix=".key")
        output = Path(tempfile.mkstemp(suffix=".gpg" if dearmor else ".asc")[1])
        try:
            if dearmor:
                self.run(["gpg", "--dearmor", "--yes", "--output", str(output), str(raw_key)])
            else:
                shutil.copyfile(raw_key, output)
            self.run(["install", "-D", "-m", "0644", str(output), str(destination)], sudo=True)
        finally:
            raw_key.unlink(missing_ok=True)
            output.unlink(missing_ok=True)

    def download_to_temp(self, url: str, *, suffix: str = "") -> Path:
        fd, temp_name = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        path = Path(temp_name)
        request = Request(url, headers={"User-Agent": "ubuntu-setup"})
        with urlopen(request, timeout=120) as response, path.open("wb") as handle:
            shutil.copyfileobj(response, handle)
        return path

    def download_to_path(self, url: str, destination: Path) -> None:
        if self.dry_run:
            print(f"[DRY-RUN] download {url} to {destination}")
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = Request(url, headers={"User-Agent": "ubuntu-setup"})
        with urlopen(request, timeout=300) as response, destination.open("wb") as handle:
            shutil.copyfileobj(response, handle)
        self.chown_to_target(destination)

    def chown_to_target(self, path: Path) -> None:
        if os.geteuid() != 0 or self.target_user == "root":
            return
        self.run(["chown", "-R", f"{self.target_user}:{self.target_user}", str(path)], sudo=False)

    def _with_sudo(self, args: list[str]) -> list[str]:
        if os.geteuid() == 0:
            return args
        return ["sudo", *args]

    def _quote(self, args: list[str]) -> str:
        return " ".join(shlex.quote(str(arg)) for arg in args)
