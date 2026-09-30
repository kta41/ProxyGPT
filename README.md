<div align="center">

# ⚡ ProxyGPT: Enterprise AI-Stack on Kubernetes

### Declarative GitOps Architecture for Private, Multi-Provider LLMs

[![Status](https://img.shields.io/badge/Status-Production--Ready-success?style=for-the-badge&logo=statuspage&logoColor=white)](https://github.com/kta41/ProxyGPT)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-K3s-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)](https://k3s.io/)
[![GitOps](https://img.shields.io/badge/GitOps-Argo_CD-EF6B48?style=for-the-badge&logo=argo&logoColor=white)](https://argo-cd.readthedocs.io/)
[![Security](https://img.shields.io/badge/Security-Kyverno%20%7C%20Zero--Trust-blueviolet?style=for-the-badge&logo=securityscorecard&logoColor=white)](https://kyverno.io/)
[![License](https://img.shields.io/badge/License-MIT-gray?style=for-the-badge)](LICENSE)

<br/>

<p align="center">
  A production-grade, self-hosted, and scalable <b>Artificial Intelligence platform</b> deployed on <b>Kubernetes (K3s)</b>.<br/>
  Orchestrated end-to-end via <b>GitOps (Argo CD & Kustomize)</b> with strict network isolation, automated model synchronization, and a zero-trust security baseline.
</p>

</div>

<img src="[https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=50&section=header](https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=50&section=header)" width="100%" />

---

## 🏗️ System Architecture

![Argo CD status](./deploy/img/dashboard.png)

ProxyGPT decouples infrastructure orchestration from functional model management through a multi-tier GitOps model.

```text
                                  [ External / Local Traffic ]
                                               │
                                               ▼
                                    ┌──────────────────────┐
                                    │   Traefik Ingress    │ (TLS / Cert-Manager)
                                    └──────────┬───────────┘
                                               │
                     ┌─────────────────────────┴─────────────────────────┐
                     ▼                                                   ▼
       ┌──────────────────────────┐                        ┌───────────────────────────┐
       │   Open WebUI (Frontend)  │                        │   LiteLLM (AI Gateway)    │
       │   https://ia.kta41.local │                        │ https://litellm.kta41.local│
       └─────────────┬────────────┘                        └─────────────┬─────────────┘
                     │                                                   │
                     ├──────────────► [ PostgreSQL PVC ] ◄───────────────┤
                     │                 (Shared Backend)                  │
                     │                                                   │
                     ▼                                                   ▼
       ┌──────────────────────────┐                        ┌───────────────────────────┐
       │ Model Sync Hook (ArgoCD) │                        │ Ollama Engine (Host Net)  │
       │  API-driven declarative  │                        │  qwen3:14b / qwen3:30b    │
       │      prompt sync         │                        │  Local GPU acceleration   │
       └──────────────────────────┘                        └───────────────────────────┘
```

The stack operates across three fundamental layers:

1. **User Interface (Frontend):** [Open WebUI](https://github.com/open-webui/open-webui), an intuitive interface for interacting with LLMs.
2. **Model Orchestrator (Middleware):** [LiteLLM](https://github.com/BerriAI/litellm), which acts as a proxy for managing multiple models and providers.
3. **Persistence (Backend):** **PostgreSQL** database for storing chats, users, and configuration.

LiteLLM is published through Traefik at `[https://litellm.kta41.local](https://litellm.kta41.local)` and exposes two local Ollama models (`qwen3-14b` and `qwen3-30b`), along with examples of external providers. Credentials are not stored in Git; they are injected from the Secret `litellm-models`.

---

## 🛠️ Technologies Used

| Domain | Technologies Used |
| :--- | :--- |
| **Orchestration & Ingress** | **Kubernetes (K3s)**, **Traefik**, **Cert-Manager** |
| **GitOps & Delivery** | **ArgoCD**, **Kustomize** (Bases & Overlays) |
| **Core AI Engines** | **LiteLLM**, **Open WebUI**, **Ollama** (`qwen3:14b`, `qwen3:30b`) |
| **Persistence** | **PostgreSQL**, **Local Path Provisioner** |
| **Policy & Security** | **Kyverno**, **Kubernetes NetworkPolicies**, **Gitleaks**, **Trivy** |

---

## 📁 Repository Structure

```text
.
├── deploy/              # Kubernetes deployments and Argo CD Applications
│   ├── argocd/
│   ├── postgres/
│   ├── litellm/
│   ├── openwebui/
│   ├── security/        # Kyverno policies and NetworkPolicies
│   └── rag/             # Qdrant vector store
├── rag/                 # Local RAG ingestion, retrieval, and citation CLI
├── Infrastructure/      # Argo CD, cert-manager, Traefik, and Gitea
├── docs/
└── scripts/
```

The repository is named **ProxyGPT**. The `deploy/` directory contains the product manifests and avoids duplicating the name in a path such as `ProxyGPT/Proxygpt/`.

### Migrating the Remote and Local Directory

After renaming the repository on GitHub from `Docker-K8s` to `ProxyGPT`, update the remote and, if desired, the local directory:

```bash
cd /home/Kta41/Docker-K8s
git remote set-url origin https://github.com/kta41/ProxyGPT.git
cd /home/Kta41
mv Docker-K8s ProxyGPT
cd ProxyGPT
git status --short --branch
```

Rename it on GitHub before running `git push` with the new URL. The Argo CD Applications in `deploy/argocd/` already point to `[https://github.com/kta41/ProxyGPT.git](https://github.com/kta41/ProxyGPT.git)`.

---

## 🚀 GitOps Deployment

This project is designed to be deployed instantly through Argo CD.

### Prerequisites

* A working Kubernetes cluster (K3s recommended).
* Argo CD installed in the `argocd` namespace.
* Local Ollama instance listening at `127.0.0.1:11435` with target models pulled:
  ```bash
  curl -fsS http://127.0.0.1:11435/api/pull -d '{"model":"qwen3:14b"}'
  curl -fsS http://127.0.0.1:11435/api/pull -d '{"model":"qwen3:30b"}'
  ```

### Installation

To deploy the complete stack, use the installer:

```bash
cp .env.example .env
chmod 700 scripts/install.sh
scripts/install.sh --env-file .env
```

The installer verifies that Ollama is reachable at `[http://127.0.0.1:11435](http://127.0.0.1:11435)` and that the models `qwen3:14b` and `qwen3:30b` are downloaded before applying resources. If Argo CD, Traefik, and cert-manager already exist, answer `yes` to the first question to keep them. The installer also submits the Kyverno Argo CD Application before the security baseline and waits for the Kyverno CRDs before submitting the policy Application.

The orchestration manifests can also be applied manually:

```bash
kubectl apply -f deploy/argocd/
```

ArgoCD will synchronize resources in the correct order, manage dependencies, and ensure that the cluster state matches this repository.

---

## 🛡️ CI/CD & Security Baselines

### CI/CD Validation Baseline (M0)

This repository validates infrastructure changes before merge. GitHub Actions are used for validation only: they do not deploy to Kubernetes. Argo CD remains the deployment controller and reconciles the repository to the cluster.

This repository owns the infrastructure layer (`ProxyGPT`), while the functional Open WebUI configuration remains in the separate repository `openwebui-ai-config`. The validation pipeline therefore guards the GitOps source of truth for the cluster, without mixing deployment with functional app configuration.

The validation baseline includes:
- Shell syntax checks for the deployment scripts.
- YAML parsing checks for the repository manifests.
- Kustomize render validation for the production overlays.
- Secret scanning with Gitleaks.
- IaC/config scanning with Trivy.

### Kubernetes Security Baseline (M1)

The M1 baseline is versioned under [`deploy/security/`](deploy/security/) and is reconciled by the [`security-baseline` Argo CD Application](deploy/argocd/security-app.yaml). The repository desired state enforces the workload and image rules for applications in `default`; platform namespaces are deliberately outside this policy scope. Application Pods disable service-account token automount and use `RuntimeDefault` seccomp, non-privileged containers, and bounded resources. The baseline provides:

- Default-deny ingress and egress policies for the application namespace.
- Explicit service-to-service access for Open WebUI, LiteLLM, PostgreSQL, and MCP.
- DNS and required HTTPS egress.
- Kyverno enforcement for privileged containers, privilege escalation, seccomp, resource bounds, explicit `latest` image tags, and `hostPath`.
- Baseline container hardening and resource limits in the application Deployments.

Kyverno is installed declaratively by [`deploy/argocd/kyverno-app.yaml`](deploy/argocd/kyverno-app.yaml). The Application is managed in the `argocd` namespace and deploys Kyverno into the `kyverno` namespace. Its CRDs use server-side apply because some Kyverno CRDs exceed the Kubernetes client-side annotation limit. The Git desired state now uses `Enforce` for `default`; the cluster still needs Argo CD reconciliation and a fresh report check before runtime completion can be claimed. The required `hostNetwork` exception for LiteLLM, PostgreSQL PVC initialization compatibility, and storage exceptions are documented in [`docs/SECURITY-EXCEPTIONS.md`](docs/SECURITY-EXCEPTIONS.md).

To inspect the M1 state:

```bash
kubectl get application kyverno security-baseline -n argocd
kubectl get pods -n kyverno
kubectl get clusterpolicies
kubectl get networkpolicies -n default
```

The checked-in manifests are not proof that the cluster has reconciled the new policy. Verify that `security-baseline` is `Synced` / `Healthy` and that the current application workloads are accepted by Kyverno before considering M1 complete at runtime. Changes are delivered by Argo CD; do not apply a parallel permanent state with `kubectl`.

### Private RAG baseline (M2)

Open WebUI's native Knowledge Bases use the in-cluster Qdrant vector store.
Manual uploads and Git-managed Markdown use separate Knowledge Bases. Argo CD
renders `openwebui-ai-config/knowledge` into a ConfigMap mounted by the official
`oikb` daemon, which synchronizes it into the Git Knowledge Base without giving
OIKB direct GitHub credentials or egress. Either source can be attached to a
chat or model in Open WebUI after indexing succeeds.

Open WebUI uses the local `qwen3-embedding:0.6b` model through LiteLLM for
embeddings. The standalone `proxygpt-rag` CLI remains an optional development
and retrieval tool; its collection is separate from Open WebUI's native
Knowledge Bases. See [`docs/RAG.md`](docs/RAG.md) for setup and usage.

The Qdrant deployment, PVC, service, network policy, Argo CD Application, both
Knowledge Bases, and OIKB configuration are in place. Runtime checks confirmed
Open WebUI and Qdrant are ready and OIKB is deployed. M2 remains incomplete:
LiteLLM's embedding request currently fails because Ollama is not reachable at
`127.0.0.1:11435`; indexing and an end-to-end cited answer still need to be
verified. See [`docs/RAG.md`](docs/RAG.md).

### MCP and AI guardrails

The deployed MCP integration is the Tavily web-search proxy, not a general
agent execution service. NetworkPolicy limits its ingress to Open WebUI and
egress to HTTPS; requests sent to Tavily leave the cluster. The standalone RAG
CLI now applies input bounds, blocks common credential/personal-data patterns,
and rejects generated citations that do not match retrieved evidence. OWASP-
aligned deterministic regression tests run in CI. These controls do not yet
intercept normal Open WebUI chats or replace an AI red-team assessment; details
are in [`docs/AI-SECURITY.md`](docs/AI-SECURITY.md).

### Langfuse preparation

An optional Argo CD Helm Application is prepared for the official Langfuse
chart, pinned to `2.1.3`, with signup and chart-managed Ingress disabled by
default. It is intentionally not registered in the always-applied
`deploy/argocd/` set. The current cluster does not advertise the ClickHouse
operator resources required by the chart's bundled ClickHouse; see
[`docs/LANGFUSE.md`](docs/LANGFUSE.md) before enabling it. LiteLLM tracing is
not enabled until Langfuse has been deployed and its API credentials have been
provisioned outside Git.

---

## ⚙️ Service Configuration

### LiteLLM Models

The LiteLLM Application uses `litellm/overlays/prod`, which includes the Certificate and Ingress for `litellm.kta41.local`. The file `litellm/base/config.yaml` defines the aliases `ollama-local`, `gpt-4o-mini`, and `claude-3-5-sonnet`. To enable external providers, create the Secret in the `default` namespace without adding it to the repository:

```bash
kubectl create secret generic litellm-models -n default \
  --from-literal=openai-api-key='sk-...' \
  --from-literal=anthropic-api-key='sk-ant-...'
```

LiteLLM uses the host network (`hostNetwork`) and accesses Ollama through `[http://127.0.0.1:11435](http://127.0.0.1:11435)`. Port 11435 avoids the Windows `portproxy` that occupies port 11434. The `qwen3-14b` and `qwen3-30b` aliases use `ollama_chat`, which is required to preserve tool calls when Open WebUI streams the response. Ollama is configured to keep one generative model loaded at a time through `OLLAMA_MAX_LOADED_MODELS=1`; when changing models, unload the previous one before loading the new one. On Windows, configure it and restart Ollama:

```powershell
setx OLLAMA_MAX_LOADED_MODELS 1
```

After restarting Ollama, select `qwen3-14b` or `qwen3-30b` in Open WebUI. Both appear in the catalog, but only the selected model remains loaded in memory.

### PostgreSQL and Persistence

PostgreSQL is the shared backend for the stack. LiteLLM uses the `litellm` database, and Open WebUI uses `openwebui_db`. The installer creates the PostgreSQL Secrets and the initial installation requires creating the Open WebUI database if it does not yet exist:

```bash
kubectl exec -it $(kubectl get pod -l app=postgres -o name) -- \
  psql -U admin -d litellm -c "CREATE DATABASE openwebui_db;"
```

PostgreSQL and Open WebUI PVCs are persistent and must not be deleted during a normal Argo CD synchronization.

---

## 🔄 Versioned Open WebUI Configuration

Functional Open WebUI configuration is maintained in the separate repository [`kta41/openwebui-ai-config`](https://github.com/kta41/openwebui-ai-config). This infrastructure repository maintains Kubernetes, Argo CD, Kustomize, Secrets, and declarative LiteLLM configuration; the external repository maintains custom models, system prompts, and Knowledge Bases.

```text
git push openwebui-ai-config
        │
        ▼
Argo CD detects main
        │
        ▼
Kustomize generates a ConfigMap with a hash
        │
        ▼
Sync Hook Job uses openwebui-sync-auth
        │
        ▼
POST /api/v1/models/sync
        │
        ▼
Open WebUI updates its custom models
```

The Job uses the internal Service:

```text
http://open-webui-service.default.svc.cluster.local:8080
```

Therefore, GitOps synchronization does not depend on the Ingress CA certificate. The CA is only needed to access `[https://ia.kta41.local](https://ia.kta41.local)`.

### Enable the Argo CD Application (Optional)

The public stack does not require the private configuration repository. The optional Application is at [`deploy/optional/openwebui-config-app.yaml`](deploy/optional/openwebui-config-app.yaml). Do not apply it unless you have access to your own compatible configuration repository and have created the required Secret.

Before applying it, create the Open WebUI API key Secret using the `.env` local file ignored by Git:

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

Register the private repository in Argo CD with a Fine-grained Personal Access Token limited to `kta41/openwebui-ai-config` with `Contents: Read-only`:

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

If you create a new JSON file, add it explicitly to `kustomization.yaml`. Validate and publish:

```bash
python3 -m json.tool models/qwen3-14b-assistant.json >/dev/null
kubectl kustomize . >/dev/null
git add models/ kustomization.yaml
git commit -m "Update Open WebUI model"
git push
```

Argo CD detects the commit, generates a new ConfigMap, and runs the Job automatically. Reconciliation is exact: models absent from the payload are removed from Open WebUI.

---

## 🔐 Local CA Certificate

The root CA is in the Secret `kta-root-ca` in `cert-manager`:

```bash
kubectl get secret kta-root-ca \
  -n cert-manager \
  -o jsonpath='{.data.tls\.crt}' |
  base64 -d |
  sudo tee /usr/local/share/ca-certificates/kta-root-ca.crt >/dev/null

sudo update-ca-certificates
```

Afterward, `curl [https://ia.kta41.local/health](https://ia.kta41.local/health)` must work without `-k`. The Argo CD Job does not need this CA because it uses the internal HTTP Service.

---

## 💡 Troubleshooting & Lessons Learned

<details>
<summary><b>1. Persistence and PostgreSQL</b></summary>

- PostgreSQL provides persistence for LiteLLM and Open WebUI through PVCs.
- The `openwebui_db` database must exist before Open WebUI starts with `DATABASE_URL` pointing to PostgreSQL.
- PVCs are persistent resources: they must not be recreated or modified destructively during an Argo CD synchronization.
- Storage changes must be separated from application changes.
</details>

<details>
<summary><b>2. Argo CD, K3s, and Networking</b></summary>

- Argo CD synchronizes manifests from Git, and Kustomize composes bases and overlays.
- `argocd-repo-server` uses `hostNetwork: true` and `ClusterFirstWithHostNet` to avoid MTU, checksum offloading, and DNS issues in WSL2 when downloading large repositories.
- Traefik and cert-manager are deployed through Argo CD Applications.
- The Open WebUI Application must point to the correct Git path inside this repository, never to a local node path.
</details>

<details>
<summary><b>3. WSL2: Timeouts, DNS, and Flannel</b></summary>

If pods cannot reach the Internet or DNS fails in WSL2:

```bash
# 1. Switch Flannel to host gateway
echo "flannel-backend: host-gw" | sudo tee -a /etc/rancher/k3s/config.yaml

# 2. Use explicit DNS resolution
echo "nameserver 8.8.8.8" | sudo tee -a /etc/rancher/k3s/resolv.conf
echo "resolv-conf: /etc/rancher/k3s/resolv.conf" | sudo tee -a /etc/rancher/k3s/config.yaml

# 3. Restart network interfaces
sudo systemctl stop k3s
sudo ip link delete cni0
sudo ip link delete flannel.1
sudo systemctl start k3s
```
</details>

<details>
<summary><b>4. Ollama and Qwen3 Models</b></summary>

- LiteLLM accesses Ollama through `hostNetwork` at `[http://127.0.0.1:11435](http://127.0.0.1:11435)`.
- Port 11435 avoids the Windows portproxy conflict on port 11434.
- `ollama_chat` preserves tool calls during streaming.
- The aliases advertise function calling, parallel function calling, and tool choice for the Qwen3 aliases.
- To limit GPU/RAM memory to one loaded model: `OLLAMA_MAX_LOADED_MODELS=1`.
- The installer verifies that `qwen3:14b` and `qwen3:30b` are available before applying the resources.
</details>

<details>
<summary><b>5. Secrets and Configuration Security</b></summary>

- `.env` is used locally only and is excluded by `.gitignore`.
- API keys are injected into Kubernetes Secrets and never stored in Git.
- `LITELLM_SALT_KEY` must remain constant while credentials exist encrypted in the database.
- The installer validates domains, Ollama availability, Kustomize, and Secrets before applying Applications.
- Do not mix without an explicit policy the LiteLLM models defined in `config.yaml` with models managed from the database/Admin UI.
- Do not publish `.env`, API keys, GitHub tokens, JWTs, cookies, provider keys, `tls.key`, or PostgreSQL dumps. Functions and Tools execute server-side code and must be reviewed as privileged code.
</details>

---

## 📚 Related Documentation

- [Complete installation guide](docs/INSTALL.md)
- [GitOps configuration contract](docs/CONFIG-GITOPS.md)
- [Open WebUI GitOps configuration](docs/OPENWEBUI-GITOPS.md)
- [Open WebUI configuration repository](https://github.com/kta41/openwebui-ai-config)
- [Open WebUI documentation](https://docs.openwebui.com/)
- [LiteLLM documentation](https://docs.litellm.ai/)

---

<div align="center">

Developed and maintained by **[Tomás Vinuesa Lago](https://github.com/Kta41)**  
*Contributions, suggestions, and feedback are always welcome.*

</div>
