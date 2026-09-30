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
    "$ROOT_DIR/deploy/security/overlays/prod"
    "$ROOT_DIR/deploy/rag/overlays/prod"
  )

  for overlay in "${overlays[@]}"; do
    echo "Rendering ${overlay}"
    kubectl kustomize "$overlay" >/dev/null
  done

  local index=0
  for overlay in "${overlays[@]}"; do
    kubectl kustomize "$overlay" > "$TEMP_DIR/rendered-${index}.yaml"
    index=$((index + 1))
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

echo "[1/4] Checking shell syntax"
check_shell_syntax

echo "[2/4] Validating YAML files"
scan_yaml

echo "[3/4] Rendering Kustomize overlays"
render_overlays

echo "[4/4] Checking enforced workload baseline"
python3 - "$ROOT_DIR" <<'PY'
import pathlib
import sys

import yaml

root = pathlib.Path(sys.argv[1])
errors = []
policy_path = root / 'deploy/security/base/kyverno-policies.yaml'
with policy_path.open('r', encoding='utf-8') as handle:
    policies = list(yaml.safe_load_all(handle))
for policy in policies:
    if policy and policy.get('kind') == 'ClusterPolicy':
        if policy.get('spec', {}).get('validationFailureAction') != 'Enforce':
            errors.append(f"{policy_path}: {policy['metadata']['name']} must enforce validation")

network_policy_path = root / 'deploy/security/base/network-policies.yaml'
with network_policy_path.open('r', encoding='utf-8') as handle:
    network_policies = {
        policy.get('metadata', {}).get('name'): policy
        for policy in yaml.safe_load_all(handle)
        if policy and policy.get('kind') == 'NetworkPolicy'
    }
mcp_ingress = network_policies.get('allow-mcp-ingress', {}).get('spec', {})
ingress_rules = mcp_ingress.get('ingress', [])
if len(ingress_rules) != 1:
    errors.append(f'{network_policy_path}: MCP ingress must have one explicit allow rule')
else:
    peers = ingress_rules[0].get('from', [])
    allowed_sources = [
        peer.get('podSelector', {}).get('matchLabels', {}).get('app')
        for peer in peers
    ]
    allowed_ports = [
        (port.get('protocol'), port.get('port'))
        for port in ingress_rules[0].get('ports', [])
    ]
    if allowed_sources != ['open-webui'] or allowed_ports != [('TCP', 8000)]:
        errors.append(f'{network_policy_path}: MCP ingress must be limited to Open WebUI on TCP/8000')

mcp_egress = network_policies.get('allow-mcp-egress', {}).get('spec', {}).get('egress', [])
egress_ports = [
    (port.get('protocol'), port.get('port'))
    for rule in mcp_egress
    for port in rule.get('ports', [])
]
if egress_ports != [('TCP', 443)]:
    errors.append(f'{network_policy_path}: MCP egress must be limited to HTTPS')

sync_egress = network_policies.get('allow-openwebui-config-sync-egress', {}).get('spec', {}).get('egress', [])
sync_ports = [
    (port.get('protocol'), port.get('port'))
    for rule in sync_egress
    for port in rule.get('ports', [])
]
if sync_ports != [('TCP', 8080)]:
    errors.append(f'{network_policy_path}: Open WebUI sync egress must be limited to TCP/8080')

for path in sorted((root / 'deploy').glob('**/*.yaml')):
    with path.open('r', encoding='utf-8') as handle:
        resources = list(yaml.safe_load_all(handle))
    for resource in resources:
        if not resource:
            continue
        kind = resource.get('kind')
        if kind == 'Deployment':
            pod_spec = resource.get('spec', {}).get('template', {}).get('spec', {})
        elif kind == 'Job':
            pod_spec = resource.get('spec', {}).get('template', {}).get('spec', {})
        else:
            continue

        name = resource.get('metadata', {}).get('name', '<unnamed>')
        pod_ref = f'{path}:{name}'
        if pod_spec.get('automountServiceAccountToken') is not False:
            errors.append(f'{pod_ref}: service-account token automount must be disabled')
        if pod_spec.get('securityContext', {}).get('seccompProfile', {}).get('type') != 'RuntimeDefault':
            errors.append(f'{pod_ref}: pod seccomp profile must be RuntimeDefault')
        for container in pod_spec.get('containers', []) + pod_spec.get('initContainers', []):
            container_name = container.get('name', '<unnamed>')
            container_ref = f'{pod_ref}/{container_name}'
            security = container.get('securityContext', {})
            if security.get('privileged') is not False:
                errors.append(f'{container_ref}: privileged must be explicitly false')
            if security.get('allowPrivilegeEscalation') is not False:
                errors.append(f'{container_ref}: privilege escalation must be disabled')
            resources = container.get('resources', {})
            for bound in ('requests', 'limits'):
                values = resources.get(bound, {})
                if not values.get('cpu') or not values.get('memory'):
                    errors.append(f'{container_ref}: CPU and memory {bound} are required')

if errors:
    print('Enforced workload baseline validation failed:', file=sys.stderr)
    for error in errors:
        print(f'  - {error}', file=sys.stderr)
    raise SystemExit(1)

print('Enforced Kyverno actions and workload hardening are present.')
PY

echo "ProxyGPT validation baseline passed."
