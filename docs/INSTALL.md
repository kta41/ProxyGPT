# Installation

The installer provisions the stack's Kubernetes Secrets, configures the
selected domains in the tracked overlays, and submits the existing Argo CD
`Application` manifests. It never edits or deletes databases, PVCs, or
existing Secrets unless Kubernetes applies the explicitly named Secret.

## Prerequisites

- A reachable Kubernetes cluster and a configured `kubectl` context.
- `kubectl` with permission to create cluster resources.
- An existing `ClusterIssuer` and CA Secret if your overlays use the internal
  CA (`kta-ca-issuer` and `kta-root-ca` by default).

## Usage

Copy the example file to a local, ignored file and fill in its values:

```bash
cp .env.example .env
chmod 700 scripts/install.sh
scripts/install.sh --env-file .env
```

Without `--env-file`, the installer prompts for every value. It first asks
whether Argo CD, Traefik, and cert-manager already exist. If the answer is
`no`, it installs pinned Argo CD and cert-manager releases and then lets Argo
CD reconcile Traefik. It validates `kubectl`, asks for domains, credentials,
and model-provider keys, and applies Secrets with `kubectl apply`. Secret
values are never written to this repository. The provider choice can be
`none`, `openai`, `anthropic`, or `both`.

When using the internal TLS overlays, the CA Secret and `ClusterIssuer` still
need to be provisioned separately; the installer does not generate or replace
your CA.

`.env` is local configuration containing secrets and must remain untracked;
only `.env.example` belongs in Git. The installer updates the tracked
LiteLLM/Open WebUI overlays with the selected domains, validates them with
Kustomize, and asks whether to commit and push those domain-only changes.
Secrets are never committed. If you answer `no`, commit and push the changed
overlays manually before syncing Argo CD.

The installer also checks the local Ollama endpoint at
`http://127.0.0.1:11435` and requires the `qwen3:14b` and `qwen3:30b` models.
On Windows, set `OLLAMA_MAX_LOADED_MODELS=1` and restart Ollama so both models
remain visible to Open WebUI while only the selected model is loaded:

```powershell
setx OLLAMA_MAX_LOADED_MODELS 1
```

`LITELLM_SALT_KEY` must be generated once and kept unchanged for the lifetime
of the LiteLLM database. Changing it can make provider credentials stored in
PostgreSQL unreadable.

The public stack does not require the optional Open WebUI configuration
repository. To enable custom models and prompts from a compatible repository,
follow [the optional Open WebUI GitOps guide](OPENWEBUI-GITOPS.md) after the
base installation.

## MCP tools

MCP integrations are managed separately from the model stack under
`deploy/mcp/`. Each MCP server gets its own adapter Deployment and internal
Service so credentials, upgrades, and failures remain isolated. The first
integration is Tavily web search, exposed through MCPO as an OpenAPI tool
server for Open WebUI.

The Tavily credential is not stored in Git. Create or update the existing
Secret in the `default` namespace before enabling the Argo CD Application:

```bash
kubectl create secret generic web-search-mcp \
  --namespace default \
  --from-literal=tavily-api-key='YOUR_TAVILY_API_KEY' \
  --dry-run=client \
  -o yaml | kubectl apply -f -
```

The Deployment reads the `tavily-api-key` key from `web-search-mcp`. Register
the internal OpenAPI server in Open WebUI using:

```text
http://web-search-mcp.default.svc.cluster.local:8000
```

Apply the MCP Argo CD Application once:

```bash
kubectl apply -f deploy/argocd/mcp-app.yaml
```

To add another MCP later, create another server directory under
`deploy/mcp/servers/` and include it from the production overlay. Do not
reuse Tavily credentials or place provider keys in tracked manifests.

## Rendering checks

Render the overlays before applying changes:

```bash
kubectl kustomize deploy/postgres/base >/dev/null
kubectl kustomize deploy/litellm/overlays/prod >/dev/null
kubectl kustomize deploy/openwebui/overlays/prod >/dev/null
kubectl kustomize deploy/mcp/overlays/prod >/dev/null
```
