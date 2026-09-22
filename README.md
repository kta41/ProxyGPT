#  AI-Stack GitOps: LiteLLM + Open WebUI + Postgres

This repository contains the complete architecture for deploying a private, scalable Artificial Intelligence stack on **Kubernetes**. Infrastructure is managed through a **GitOps** model using **Argo CD** and **Kustomize**.

![Status](https://img.shields.io/badge/Status-Production--Ready-green)
![K8s](https://img.shields.io/badge/Kubernetes-K3s-blue)
![GitOps](https://img.shields.io/badge/GitOps-ArgoCD-orange)

## 🏗️ System Architecture

![Argo CD status](./deploy/img/dashboard.png)

The stack consists of three main layers designed to work together in the cluster:

1.  **User Interface (Frontend):** [Open WebUI](https://github.com/open-webui/open-webui), an intuitive interface for interacting with LLMs.
2.  **Model Orchestrator (Middleware):** [LiteLLM](https://github.com/BerriAI/litellm), which acts as a proxy for managing multiple models and providers.
3.  **Persistence (Backend):** **PostgreSQL** database for storing chats, users, and configuration.

LiteLLM is published through Traefik at `https://litellm.kta41.local` and exposes
two local Ollama models (`qwen3-14b` and `qwen3-30b`), along with examples
of external providers. Credentials are not stored in Git; they are injected
from the Secret `litellm-models`.



## 🛠️ Technologies Used

* **Kubernetes (K3s):** Container orchestration.
* **ArgoCD:** Declarative CD for automatic desired-state synchronization.
* **Kustomize:** Layered configuration management (Base and Overlays).
* **Traefik:** Ingress Controller for external traffic and TLS management.
* **Local Path Provisioner:** Data persistence through local volumes.

## 📁 Repository Structure

```text
.
├── deploy/             # Kubernetes deployments and Argo CD Applications
│   ├── argocd/
│   ├── postgres/
│   ├── litellm/
│   └── openwebui/
├── Infrastructure/      # Argo CD, cert-manager, Traefik, and Gitea
├── docs/
└── scripts/
```

The repository is named **ProxyGPT**. The `deploy/` directory contains the
product manifests and avoids duplicating the name in a path such as
`ProxyGPT/Proxygpt/`.

### Migrating the remote and local directory

After renaming the repository on GitHub from `Docker-K8s` to `ProxyGPT`,
update the remote and, if desired, the local directory:

```bash
cd /home/Kta41/Docker-K8s
git remote set-url origin https://github.com/kta41/ProxyGPT.git
cd /home/Kta41
mv Docker-K8s ProxyGPT
cd ProxyGPT
git status --short --branch
```

Rename it on GitHub before running `git push` with the new
URL. The Argo CD Applications in `deploy/argocd/` already point to
`https://github.com/kta41/ProxyGPT.git`.

## 🚀 GitOps Deployment

This project is designed to be deployed instantly through Argo CD.
1. Prerequisites

    A working Kubernetes cluster (K3s recommended).

    Argo CD installed in the `argocd` namespace.

2. Installation

To deploy the complete stack, use the installer:

```bash
cp .env.example .env
chmod 700 scripts/install.sh
scripts/install.sh --env-file .env
```

The installer verifies that Ollama is reachable at `http://127.0.0.1:11435` and
that the models `qwen3:14b` and `qwen3:30b` are downloaded before applying
resources. If Argo CD, Traefik, and cert-manager already exist, answer `yes` to
the first question to keep them.

The orchestration manifests can also be applied manually:

```bash
kubectl apply -f deploy/argocd/
```

ArgoCD will synchronize resources in the correct order, manage dependencies, and ensure that the cluster state matches this repository.

When the PostgreSQL cluster is enabled, the final deployment step is to create the Open WebUI database:

```bash
kubectl exec -it $(kubectl get pod -l app=postgres -o name) -- psql -U admin -d litellm -c "CREATE DATABASE openwebui_db;"
```

### LiteLLM Models

The LiteLLM Application uses `litellm/overlays/prod`, which includes the
Certificate and Ingress for `litellm.kta41.local`. The file
`litellm/base/config.yaml` defines the aliases `ollama-local`, `gpt-4o-mini` and
`claude-3-5-sonnet`. To enable external providers, create the Secret in the
`default` namespace without adding it to the repository:

```bash
kubectl create secret generic litellm-models -n default \
  --from-literal=openai-api-key='sk-...' \
  --from-literal=anthropic-api-key='sk-ant-...'
```

LiteLLM uses the host network (`hostNetwork`) and accesses Ollama through
`http://127.0.0.1:11435`. Port 11435 avoids the Windows `portproxy` that
occupies port 11434. The `qwen3-14b` and `qwen3-30b` aliases use the
`ollama_chat`, which is required to preserve tool calls when
Open WebUI streams the response. Ollama is configured to keep one
generative model loaded at a time through
`OLLAMA_MAX_LOADED_MODELS=1` ; when changing models, unload the previous one before
loading the new one. On Windows, configure it and restart Ollama:

```powershell
setx OLLAMA_MAX_LOADED_MODELS 1
```

After restarting Ollama, select `qwen3-14b` or `qwen3-30b` in Open
WebUI. Both appear in the catalog, but only the selected model remains
loaded in memory.

To download the models manually:

```bash
curl -fsS http://127.0.0.1:11435/api/pull -d '{"model":"qwen3:14b"}'
curl -fsS http://127.0.0.1:11435/api/pull -d '{"model":"qwen3:30b"}'
```

## PostgreSQL and Persistence

PostgreSQL is the shared backend for the stack. LiteLLM uses the
`litellm` database, and Open WebUI uses `openwebui_db`. The installer creates the PostgreSQL Secrets
and the initial installation requires creating the Open WebUI database
if it does not yet exist:

```bash
kubectl exec -it $(kubectl get pod -l app=postgres -o name) -- \
  psql -U admin -d litellm -c "CREATE DATABASE openwebui_db;"
```

PostgreSQL and Open WebUI PVCs are persistent and must not be deleted
during a normal Argo CD synchronization.

## Stack Evolution

The initial branch `feat/postgres-auto-init` consolidated the deployment of
PostgreSQL, LiteLLM, and Open WebUI with Argo CD, cert-manager, Traefik, and Kustomize,
together with a parameterized installer. It also added:

- Domain and certificate overlays for LiteLLM and Open WebUI.
- Secret injection without storing secrets in Git.
- Ollama and Qwen3 model validation before deployment.
- LiteLLM access to host Ollama through `hostNetwork`.
- Support for Ollama tool calls and streaming.

This branch adds optional integration with the second repository
`openwebui-ai-config`, using an Argo CD Application and Sync Hook Job to
synchronize custom models and system prompts through the official Open WebUI API.

## Versioned Open WebUI Configuration

Functional Open WebUI configuration is maintained in the separate repository
 [`kta41/openwebui-ai-config`](https://github.com/kta41/openwebui-ai-config).
This infrastructure repository maintains Kubernetes, Argo CD, Kustomize,
Secrets and declarative LiteLLM configuration; the external repository
maintains custom models, system prompts, and
Knowledge Bases.

```text
git push openwebui-ai-config
        |
        v
Argo CD detects main
        |
        v
Kustomize generates a ConfigMap with a hash
        |
        v
Sync Hook Job uses openwebui-sync-auth
        |
        v
POST /api/v1/models/sync
        |
        v
Open WebUI updates its custom models
```

The Job uses the internal Service:

```text
http://open-webui-service.default.svc.cluster.local:8080
```

Therefore, GitOps synchronization does not depend on the Ingress CA certificate.
The CA is only needed to access
`https://ia.kta41.local`.

### Optional: Enable the Argo CD Application

The public stack does not require the private configuration repository. The
optional Application is at
[`deploy/optional/openwebui-config-app.yaml`](deploy/optional/openwebui-config-app.yaml).
Do not apply it unless you have access to your own compatible configuration
repository and have created the required Secret.
Before applying it, create the Open WebUI API key Secret using the
`.env` local file ignored by Git:

```bash
cd /home/Kta41/ProxyGPT
set -a
source .env
set +a

kubectl create secret generic openwebui-sync-auth \
  --namespace default \
  --from-literal=api-key="$OPENWEBUI_API_KEY" \
  --dry-run=client \
  -o yaml | kubectl apply -f -

unset OPENWEBUI_API_KEY
```

The private repository must also be registered in Argo CD with a
Fine-grained Personal Access Token limited to
`kta41/openwebui-ai-config` with `Contents: Read-only`:

```bash
read -rsp "Read-only GitHub token: " GITHUB_READ_TOKEN
echo

kubectl create secret generic repo-openwebui-ai-config \
  --namespace argocd \
  --from-literal=type=git \
  --from-literal=url=https://github.com/kta41/openwebui-ai-config.git \
  --from-literal=username=kta41 \
  --from-literal=password="$GITHUB_READ_TOKEN" \
  --dry-run=client \
  -o yaml |
  kubectl label --local -f - \
    argocd.argoproj.io/secret-type=repository \
    -o yaml |
  kubectl apply -f -

unset GITHUB_READ_TOKEN
```

Apply and verify:

```bash
kubectl apply -f deploy/optional/openwebui-config-app.yaml
kubectl get application openwebui-config -n argocd
kubectl get jobs,pods -n default -l app=openwebui-model-sync
```

The expected state is `Synced`, `Healthy`, and `Succeeded`.

### Modify Models and Prompts

Edit the external repository:

```bash
cd /home/Kta41/openwebui-ai-config
nano models/qwen3-14b-assistant.json
```

If you create a new JSON file, add it explicitly to
`kustomization.yaml`. Validate and publish:

```bash
python3 -m json.tool models/qwen3-14b-assistant.json >/dev/null
kubectl kustomize . >/dev/null
git add models/ kustomization.yaml
git commit -m "Update Open WebUI model"
git push
```

Argo CD detects the commit, generates a new ConfigMap, and runs the Job
automatically. Reconciliation is exact: models absent from the payload
are removed from Open WebUI.

### Local CA Certificate

The root CA is in the Secret `kta-root-ca` in the `cert-manager`:

```bash
kubectl get secret kta-root-ca \
  -n cert-manager \
  -o jsonpath='{.data.tls\.crt}' |
  base64 -d |
  sudo tee /usr/local/share/ca-certificates/kta-root-ca.crt >/dev/null

sudo update-ca-certificates
```

Afterward, `curl https://ia.kta41.local/health` must work without `-k`.
The Argo CD Job does not need this CA because it uses the internal HTTP Service.

## Related Documentation

- [Complete installation guide](docs/INSTALL.md)
- [GitOps configuration contract](docs/CONFIG-GITOPS.md)
- [Open WebUI GitOps configuration](docs/OPENWEBUI-GITOPS.md)
- [Open WebUI configuration repository](https://github.com/kta41/openwebui-ai-config)
- [Open WebUI documentation](https://docs.openwebui.com/)
- [LiteLLM documentation](https://docs.litellm.ai/)

## Troubleshooting and Lessons Learned

### Persistence and PostgreSQL

- PostgreSQL provides persistence for LiteLLM and Open WebUI through PVCs.
- The `openwebui_db` database must exist before Open WebUI starts with
  `DATABASE_URL` pointing to PostgreSQL.
- PVCs are persistent resources: they must not be recreated or modified
  destructively during an Argo CD synchronization.
- Storage changes must be separated from application changes.

### Argo CD, K3s, and Networking

- Argo CD synchronizes manifests from Git, and Kustomize composes bases and overlays.
- `argocd-repo-server` uses `hostNetwork: true` and
  `ClusterFirstWithHostNet` to avoid MTU, checksum offloading
  and DNS issues in WSL2 when downloading large repositories.
- Traefik and cert-manager are deployed through Argo CD Applications.
- The Open WebUI Application must point to the correct Git path inside
  this repository, never to a local node path.

### WSL2: Timeouts, DNS, and Flannel

If pods cannot reach the Internet or DNS fails in WSL2:

1. Switch Flannel to the host gateway:

   ```bash
   echo "flannel-backend: host-gw" | sudo tee -a /etc/rancher/k3s/config.yaml
   ```

2. Use explicit DNS resolution:

   ```bash
   echo "nameserver 8.8.8.8" | sudo tee -a /etc/rancher/k3s/resolv.conf
   echo "resolv-conf: /etc/rancher/k3s/resolv.conf" | sudo tee -a /etc/rancher/k3s/config.yaml
   ```

3. Restart only after checking the existing interfaces:

   ```bash
   sudo systemctl stop k3s
   sudo ip link delete cni0
   sudo ip link delete flannel.1
   sudo systemctl start k3s
   ```

### Ollama and Qwen3 Models

- LiteLLM accesses Ollama through `hostNetwork` at
  `http://127.0.0.1:11435`.
- Port 11435 avoids the Windows portproxy conflict on
  port 11434.
- `ollama_chat` preserves tool calls during streaming.
- The aliases advertise function calling, parallel function calling, and
  tool choice for the Qwen3 aliases.
- To limit GPU/RAM memory to one loaded model: `OLLAMA_MAX_LOADED_MODELS=1`.
- The installer verifies that `qwen3:14b` and `qwen3:30b` are available before
  applying the resources.

Manual download:

```bash
curl -fsS http://127.0.0.1:11435/api/pull -d '{"model":"qwen3:14b"}'
curl -fsS http://127.0.0.1:11435/api/pull -d '{"model":"qwen3:30b"}'
```

### TLS and Internal CA

The root CA `kta-root-ca` is in `cert-manager`. If the local client reports
`unable to get local issuer certificate`, install `tls.crt` in the trust store;
do not extract or distribute `tls.key`. The GitOps Job does not need this CA because
it uses the internal Open WebUI HTTP Service.

### Secrets and Configuration

- `.env` is used locally only and is excluded by `.gitignore`.
- API keys are injected into Kubernetes Secrets and never stored in Git.
- `LITELLM_SALT_KEY` must remain constant while credentials exist
  encrypted in the database.
- The installer validates domains, Ollama availability, Kustomize, and Secrets
  before applying Applications.
- Do not mix without an explicit policy the LiteLLM models defined in
  `config.yaml` with models managed from the database/Admin UI.

### Open WebUI GitOps

- `/api/v1/models/sync` requires the complete schema for the installed version,
  including `user_id`, `is_active`, `created_at`, and `updated_at`.
- The hook obtains the administrator user through `/api/v1/auths/`.
- A failed hook Job can block an operation; delete only the Job
  `openwebui-model-sync` and refresh the Application.
- Exact reconciliation removes models absent from the payload. Always review
  the diff before deleting JSON from the external repository.

### Security

Do not publish `.env`, API keys, GitHub tokens, JWTs, cookies, provider keys,
`tls.key`, or PostgreSQL dumps. Functions and Tools execute server-side code
and must be reviewed as privileged code.
