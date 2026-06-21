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

PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --help >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --source apt.ubuntu >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --source npm >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --category programming >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --only git >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --only dropbox >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --only codex >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --only discord >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --only docker >/dev/null
PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --only android-studio >/dev/null

PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --dry-run --only git >/dev/null
docker_dry_run="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --dry-run --only docker)"
assert_output_contains "$docker_dry_run" "/etc/apt/sources.list.d/docker.sources" "--dry-run --only docker output"
assert_output_contains "$docker_dry_run" "apt remove -y docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc" "--dry-run --only docker output"
assert_output_contains "$docker_dry_run" "docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin" "--dry-run --only docker output"

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
    outlook-wrapper
do
    assert_unknown_id "$id"
done

communication_output="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --category communication)"
assert_output_not_contains "$communication_output" "Microsoft Teams Wrapper [teams-for-linux]" "--category communication output"
assert_output_not_contains "$communication_output" "Outlook Wrapper [outlook-wrapper]" "--category communication output"

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

external_output="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --source apt.external)"
assert_output_contains "$external_output" "Docker Engine [docker]" "--source apt.external output"

deb_output="$(PYTHONDONTWRITEBYTECODE=1 ./ubuntu-setup --list --source deb)"
assert_output_contains "$deb_output" "Discord [discord]" "--source deb output"

echo "Smoke tests passed."
