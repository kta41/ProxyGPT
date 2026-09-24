#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

require_cmd kubectl
require_cmd python3

scan_yaml() {
  python3 - "$ROOT_DIR" <<'PY'
import pathlib
import sys
import yaml

root = pathlib.Path(sys.argv[1])
paths = []
paths.extend(root.glob('deploy/**/*.y*ml'))
paths.extend(root.glob('Infrastructure/**/*.y*ml'))
paths.extend(root.glob('.github/**/*.y*ml'))
paths = sorted(set(paths))

failed = []
for path in paths:
    try:
        with path.open('r', encoding='utf-8') as handle:
            for _ in yaml.safe_load_all(handle):
                pass
    except Exception as exc:  # pragma: no cover - surfaced in stderr for CI
        failed.append(f'{path}: {exc}')

if failed:
    print('YAML validation failed:', file=sys.stderr)
    for item in failed:
        print(f'  - {item}', file=sys.stderr)
    raise SystemExit(1)

print(f'Validated {len(paths)} YAML files.')
PY
}

check_shell_syntax() {
  for script in "$ROOT_DIR"/scripts/*.sh; do
    bash -n "$script"
  done
}

render_overlays() {
  local overlays=(
    "$ROOT_DIR/deploy/postgres/base"
    "$ROOT_DIR/deploy/litellm/overlays/prod"
    "$ROOT_DIR/deploy/openwebui/overlays/prod"
    "$ROOT_DIR/deploy/mcp/overlays/prod"
  )

  for overlay in "${overlays[@]}"; do
    echo "Rendering ${overlay}"
    kubectl kustomize "$overlay" >/dev/null
  done

  for overlay in "${overlays[@]}"; do
    local name
    name="$(basename "$overlay")"
    kubectl kustomize "$overlay" > "$TEMP_DIR/${name}.yaml"
  done

  python3 - "$TEMP_DIR" <<'PY'
import pathlib
import sys
import yaml

root = pathlib.Path(sys.argv[1])
files = sorted(root.glob('*.yaml'))
if not files:
    raise SystemExit('No rendered YAML files found.')

failed = []
for path in files:
    try:
        with path.open('r', encoding='utf-8') as handle:
            for _ in yaml.safe_load_all(handle):
                pass
    except Exception as exc:
        failed.append(f'{path}: {exc}')

if failed:
    print('Rendered Kustomize output validation failed:', file=sys.stderr)
    for item in failed:
        print(f'  - {item}', file=sys.stderr)
    raise SystemExit(1)

print(f'Validated {len(files)} rendered manifests.')
PY
}

echo "[1/3] Checking shell syntax"
check_shell_syntax

echo "[2/3] Validating YAML files"
scan_yaml

echo "[3/3] Rendering Kustomize overlays"
render_overlays

echo "ProxyGPT validation baseline passed."
