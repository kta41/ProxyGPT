#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE=""
INFRASTRUCTURE_EXISTS=""
ARGOCD_VERSION="${ARGOCD_VERSION:-v2.13.3}"
CERT_MANAGER_VERSION="${CERT_MANAGER_VERSION:-v1.16.2}"
OLLAMA_API_BASE="${OLLAMA_API_BASE:-http://127.0.0.1:11435}"
OLLAMA_REQUIRED_MODELS=("qwen3:14b" "qwen3:30b")

usage() {
  echo "Usage: $0 [--env-file PATH]"
}

while (($#)); do
  case "$1" in
    --env-file)
      (($# >= 2)) || { echo "Missing path after --env-file" >&2; exit 2; }
      ENV_FILE=$2
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -n "$ENV_FILE" ]]; then
  [[ -f "$ENV_FILE" ]] || { echo "Environment file not found: $ENV_FILE" >&2; exit 1; }
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

ask() {
  local name=$1 prompt=$2 default=${3-} value
  value=${!name-}
  if [[ -z "$value" ]]; then
    if [[ -n "$default" ]]; then
      if [[ ! -t 0 ]]; then
        printf -v "$name" '%s' "$default"
        return
      fi
      read -r -p "$prompt [$default]: " value
      value=${value:-$default}
    else
      [[ -t 0 ]] || { echo "$name is required in non-interactive mode." >&2; exit 2; }
      read -r -p "$prompt: " value
    fi
  fi
  printf -v "$name" '%s' "$value"
}

ask_secret() {
  local name=$1 prompt=$2 value
  value=${!name-}
  if [[ -z "$value" ]]; then
    read -r -s -p "$prompt: " value
    echo
  fi
  [[ -n "$value" ]] || { echo "$name must not be empty." >&2; exit 1; }
  printf -v "$name" '%s' "$value"
}

b64() {
  printf '%s' "$1" | base64 | tr -d '\n'
}

echo "Dependency check (answer this before any cluster changes)."
ask INFRASTRUCTURE_EXISTS "Does Argo CD, Traefik and cert-manager already exist? (yes/no)" "yes"

command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required." >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required." >&2; exit 1; }
kubectl version --client >/dev/null || { echo "kubectl client validation failed." >&2; exit 1; }
kubectl cluster-info >/dev/null 2>&1 ||
  { echo "kubectl cannot reach a cluster (check KUBECONFIG/context)." >&2; exit 1; }

ask LITELLM_DOMAIN "LiteLLM domain" "litellm.kta41.local"
ask OPENWEBUI_DOMAIN "Open WebUI domain" "ia.kta41.local"
ask GIT_PUSH "Push generated domain configuration to the Git remote? (yes/no)" "no"
ask_secret POSTGRES_PASSWORD "PostgreSQL password"
ask_secret LITELLM_MASTER_KEY "LiteLLM master key"
ask_secret LITELLM_UI_PASSWORD "LiteLLM UI password"
ask_secret LITELLM_SALT_KEY "LiteLLM salt key (keep this unchanged)"
if [[ -z "${OPENWEBUI_PROXY_KEY-}" ]]; then
  OPENWEBUI_PROXY_KEY="$LITELLM_MASTER_KEY"
fi
ask MODEL_PROVIDER "Model provider (none/openai/anthropic/both)" "none"
case "$MODEL_PROVIDER" in
  none) ;;
  openai|both) ask_secret OPENAI_API_KEY "OpenAI API key" ;;
  anthropic|both) ask_secret ANTHROPIC_API_KEY "Anthropic API key" ;;
  *) echo "MODEL_PROVIDER must be none, openai, anthropic, or both." >&2; exit 1 ;;
esac

valid_domain() {
  [[ "$1" =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$ ]]
}
valid_domain "$LITELLM_DOMAIN" || { echo "Invalid LiteLLM domain: $LITELLM_DOMAIN" >&2; exit 1; }
valid_domain "$OPENWEBUI_DOMAIN" || { echo "Invalid Open WebUI domain: $OPENWEBUI_DOMAIN" >&2; exit 1; }

echo "Checking Ollama at ${OLLAMA_API_BASE}."
OLLAMA_MODELS="$(
  OLLAMA_API_BASE="$OLLAMA_API_BASE" python3 - <<'PY'
import json
import os
import urllib.error
import urllib.request

url = os.environ["OLLAMA_API_BASE"].rstrip("/") + "/api/tags"
try:
    with urllib.request.urlopen(url, timeout=10) as response:
        payload = json.load(response)
except (OSError, ValueError, urllib.error.URLError) as error:
    raise SystemExit(f"Cannot reach Ollama at {url}: {error}")

for model in payload.get("models", []):
    print(model.get("name", ""))
PY
)" || {
  echo "Ollama is required before deploying LiteLLM." >&2
  echo "Expected endpoint: ${OLLAMA_API_BASE}" >&2
  exit 1
}

for required_model in "${OLLAMA_REQUIRED_MODELS[@]}"; do
  if ! grep -Fxq "$required_model" <<<"$OLLAMA_MODELS"; then
    echo "Required Ollama model is missing: $required_model" >&2
    echo "Install it with: curl -fsS ${OLLAMA_API_BASE}/api/pull -d '{\"model\":\"${required_model}\"}'" >&2
    exit 1
  fi
done
echo "Ollama models available: ${OLLAMA_REQUIRED_MODELS[*]}"
echo "Ollama must run with OLLAMA_MAX_LOADED_MODELS=1 so only the selected model stays loaded."

if [[ "$INFRASTRUCTURE_EXISTS" =~ ^([Nn][Oo]|[Nn])$ ]]; then
  echo "Installing Argo CD and cert-manager; Traefik will be reconciled by Argo CD."
  kubectl apply -f "https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml"
  kubectl create namespace cert-manager --dry-run=client -o yaml | kubectl apply -f -
  kubectl apply -f "https://github.com/cert-manager/cert-manager/releases/download/${CERT_MANAGER_VERSION}/cert-manager.yaml"
  kubectl rollout status deployment/argocd-server -n argocd --timeout=10m
  kubectl rollout status deployment/cert-manager -n cert-manager --timeout=10m
  kubectl rollout status deployment/cert-manager-webhook -n cert-manager --timeout=10m
  kubectl rollout status deployment/cert-manager-cainjector -n cert-manager --timeout=10m
else
  echo "Using existing Argo CD, Traefik and cert-manager."
fi

replace_domain() {
  local kustomization=$1 ingress=$2 certificate=$3 desired=$4
  python3 - "$kustomization" "$ingress" "$certificate" "$desired" <<'PY'
import pathlib
import re
import sys

kustomization, ingress, certificate, desired = sys.argv[1:]
kustomization_path = pathlib.Path(kustomization)
text = kustomization_path.read_text()
match = re.search(r"full_domain=([^\s]+)", text)
if not match:
    raise SystemExit(f"full_domain not found in {kustomization}")
current = match.group(1)
kustomization_path.write_text(text.replace(f"full_domain={current}", f"full_domain={desired}"))

for filename in (ingress, certificate):
    path = pathlib.Path(filename)
    content = path.read_text()
    if current not in content:
        raise SystemExit(f"domain {current} not found in {filename}")
    path.write_text(content.replace(current, desired))
PY
}

replace_domain \
  "$ROOT_DIR/deploy/litellm/overlays/prod/kustomization.yaml" \
  "$ROOT_DIR/deploy/litellm/overlays/prod/ingress.yaml" \
  "$ROOT_DIR/deploy/litellm/overlays/prod/cert.yaml" \
  "$LITELLM_DOMAIN"
replace_domain \
  "$ROOT_DIR/deploy/openwebui/overlays/prod/kustomization.yaml" \
  "$ROOT_DIR/deploy/openwebui/overlays/prod/ingress.yaml" \
  "$ROOT_DIR/deploy/openwebui/overlays/prod/cert.yaml" \
  "$OPENWEBUI_DOMAIN"

if ! kubectl kustomize "$ROOT_DIR/deploy/litellm/overlays/prod" >/dev/null ||
   ! kubectl kustomize "$ROOT_DIR/deploy/openwebui/overlays/prod" >/dev/null; then
  echo "Generated overlays failed Kustomize validation; aborting before cluster changes." >&2
  exit 1
fi

echo "Applying application secrets (values are sent only to the Kubernetes API)."
kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: postgres-auth
  namespace: default
type: Opaque
data:
  postgres-password: $(b64 "$POSTGRES_PASSWORD")
---
apiVersion: v1
kind: Secret
metadata:
  name: litellm-auth
  namespace: default
type: Opaque
data:
  master-key: $(b64 "$LITELLM_MASTER_KEY")
  ui-password: $(b64 "$LITELLM_UI_PASSWORD")
  salt-key: $(b64 "$LITELLM_SALT_KEY")
---
apiVersion: v1
kind: Secret
metadata:
  name: openwebui-auth
  namespace: default
type: Opaque
data:
  proxy-key: $(b64 "$OPENWEBUI_PROXY_KEY")
EOF

if [[ "$MODEL_PROVIDER" != none ]]; then
  {
    cat <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: litellm-models
  namespace: default
type: Opaque
data:
EOF
    [[ "$MODEL_PROVIDER" == openai || "$MODEL_PROVIDER" == both ]] &&
      printf '  openai-api-key: %s\n' "$(b64 "$OPENAI_API_KEY")"
    [[ "$MODEL_PROVIDER" == anthropic || "$MODEL_PROVIDER" == both ]] &&
      printf '  anthropic-api-key: %s\n' "$(b64 "$ANTHROPIC_API_KEY")"
  } | kubectl apply -f -
fi

CUSTOM_DOMAINS=false
if [[ "$LITELLM_DOMAIN" != "litellm.kta41.local" || "$OPENWEBUI_DOMAIN" != "ia.kta41.local" ]]; then
  CUSTOM_DOMAINS=true
fi

if [[ "$GIT_PUSH" =~ ^([Yy][Ee][Ss]|[Yy])$ ]]; then
  git -C "$ROOT_DIR" add deploy/litellm/overlays/prod deploy/openwebui/overlays/prod
  git -C "$ROOT_DIR" commit -m "Configure AI stack domains"
  git -C "$ROOT_DIR" push
elif [[ "$CUSTOM_DOMAINS" == true ]]; then
  echo "Domain overlays were updated locally. Commit and push them before Argo CD can use them." >&2
  echo "Secrets were created, but Applications were not applied to avoid syncing old domains." >&2
  exit 1
fi

echo "Applying existing Argo CD Application manifests (no project manifests are changed)."
find "$ROOT_DIR/deploy/argocd" "$ROOT_DIR/Infrastructure" -type f -name '*app.yaml' -print0 |
  while IFS= read -r -d '' manifest; do
    kubectl apply -f "$manifest"
  done
echo "Selected domains: LiteLLM=$LITELLM_DOMAIN OpenWebUI=$OPENWEBUI_DOMAIN"
echo "Installation submitted. Argo CD will reconcile the Applications."
