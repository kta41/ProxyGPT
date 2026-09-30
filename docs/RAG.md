# Open WebUI Knowledge Bases (M2)

The user-facing RAG experience is Open WebUI's native Knowledge feature. Both
manual uploads and Git-synchronized documents are indexed by Open WebUI, with
Qdrant as its vector backend and the local `qwen3-embedding:0.6b` model served
through LiteLLM.

```text
Upload in Open WebUI ─┐
                      ├─> Open WebUI Knowledge Base ─> Qdrant
Git source via oikb ──┘                │
                                       └─> LiteLLM -> Ollama embeddings
```

Create two separate Knowledge Bases in **Workspace → Knowledge**:

- One for documents managed manually in the interface.
- One for documents synchronized from Git. Keeping them separate prevents
  source cleanup from affecting files uploaded manually.

Attach either or both Knowledge Bases to a chat or a model in Open WebUI. The
`proxygpt-rag` command-line tool remains available for development, but it
uses its own Qdrant collection; it is not required for normal chat.

## Deployment

Open WebUI is pinned to v0.9.6, the minimum version required by the official
`oikb` synchronizer. Qdrant is deployed by the
[`rag-vector-store` Argo CD Application](../deploy/argocd/rag-app.yaml) with a
10 GiB PVC and a ClusterIP-only service. Argo CD pruning is disabled for the
PVC; do not delete it during ordinary reconciliation. The PVC uses the
cluster's default storage class and has no backup/HA mechanism.

The Qdrant image runs as UID 0 by default. The deployment documents this
compatibility exception and still disables privilege escalation, drops Linux
capabilities, and uses the RuntimeDefault seccomp profile.

The `openwebui-ai-config` repository deploys the official OIKB daemon. It
reads `knowledge/.oikb.yaml`, uses the existing `openwebui-sync-auth` Secret,
and periodically syncs the configured Git source into the Git-managed
Knowledge Base. The daemon only has network access to Open WebUI and HTTPS
egress for the public GitHub source.

## Set up the Git-managed Knowledge Base

1. Wait for the Argo CD Applications `openwebui` and `rag-vector-store` to
   report `Synced` / `Healthy`. The Open WebUI configuration Application must
   also finish deploying its OIKB daemon.
2. Ensure Ollama at `http://127.0.0.1:11435` has the embedding model:

   ```bash
   curl -fsS http://127.0.0.1:11435/api/pull \
     -d '{"model":"qwen3-embedding:0.6b"}'
   ```

3. In Open WebUI, create a Knowledge Base for the Git-synchronized documents.
   Copy its ID from the Knowledge Base URL. Create a different Knowledge Base
   for documents uploaded manually.
4. In `openwebui-ai-config/knowledge/.oikb.yaml`, configure the Git Knowledge
   Base ID:

   ```yaml
   defaults:
     interval: 1h
   sources:
     - name: proxygpt-knowledge
       source: github:kta41/openwebui-ai-config/knowledge
       kb-id: REPLACE_WITH_KNOWLEDGE_BASE_ID
       filter:
         include:
           - "*.md"
           - "**/*.md"
   ```

   The source is public and read-only. Do not add an API key or token to this
   file. The existing `openwebui-sync-auth` Secret supplies the Open WebUI API
   key to OIKB at runtime.
5. Push the configuration change to `openwebui-ai-config`. Argo CD updates the
   ConfigMap and restarts OIKB; it performs an initial sync and checks Git
   hourly. Changes to Markdown files are picked up on the next check.
6. Upload manual documents through **Workspace → Knowledge**. They remain
   independent of the Git synchronization.
7. Attach either Knowledge Base to a chat with `#` or to a model in
   **Workspace → Models**. Ask a question grounded in a source document and
   check the citations against that source.

To inspect synchronization status and logs without exposing credentials:

```bash
kubectl get deployment openwebui-oikb -n default
kubectl logs deployment/openwebui-oikb -n default
```

## Embeddings and retrieval

Open WebUI sends embeddings through the existing OpenAI-compatible LiteLLM
endpoint using the `qwen3-embedding` alias. LiteLLM forwards those requests to
the Ollama model `qwen3-embedding:0.6b`. Generation continues to use the
selected chat model, such as `qwen3-14b`.

The Open WebUI Qdrant integration uses the `open-webui` collection prefix. The
standalone CLI uses a distinct collection and will not populate a Knowledge
Base. Changing embedding models or chunking settings requires reindexing the
affected Knowledge Base documents in Open WebUI.

Qdrant has no Ingress or NodePort. The intended paths are Open WebUI to Qdrant
and authorized operator access through `kubectl port-forward`.

## Validation

```bash
python3 -m pip install -e ./rag
python3 -m unittest discover -s rag/tests -v
bash scripts/validate-manifests.sh
```

The CLI tests exercise its own indexing pipeline. The live UI test requires
the cluster, the embedding model in Ollama, and a completed OIKB sync.

The CLI `ask` and `search` flows also apply deterministic input/output
guardrails and OWASP-aligned regression tests; they do not protect normal
Open WebUI chat. See [`AI-SECURITY.md`](AI-SECURITY.md) for scope and
limitations.
