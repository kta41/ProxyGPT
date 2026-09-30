# Private RAG baseline (M2)

M2 provides an initial reproducible RAG pipeline for Markdown documents:

```text
Markdown files
  -> heading-aware, overlapping chunks
  -> local Ollama embeddings
  -> Qdrant persistent collection
  -> similarity retrieval with source references
  -> optional grounded answer through LiteLLM
```

This first milestone is intentionally an operator-run CLI, not an autonomous
agent and not a replacement for Open WebUI's built-in Knowledge Bases.

## Components

- Qdrant is deployed in `default` by the
  [`rag-vector-store` Argo CD Application](../deploy/argocd/rag-app.yaml).
- Qdrant uses a 10 GiB PVC with Argo CD pruning disabled for the claim. Do not
  delete that PVC during ordinary reconciliation.
- The PVC uses the cluster's default storage class and has no backup/HA
  mechanism in this milestone.
- Qdrant has a ClusterIP service only; there is no Ingress or NodePort.
- The CLI lives under [`rag/`](../rag/) and reads Markdown from a local
  directory. This lets it index the separate
  [`openwebui-ai-config/knowledge`](../../openwebui-ai-config/knowledge)
  repository without copying functional knowledge content into infrastructure
  Git.
- Ollama generates embeddings locally with `qwen3-embedding:0.6b`.
- LiteLLM can optionally generate an answer using the existing `qwen3-14b`
  model alias.

The Qdrant official image runs as UID 0 by default. The deployment documents
this compatibility exception and still disables privilege escalation, drops
Linux capabilities, and uses the RuntimeDefault seccomp profile.

## First-time setup

The changes in this milestone are local until they are committed and pushed.
After the changes are published, register the Argo CD Application (unless the
installer has already done so) and wait for reconciliation:

```bash
kubectl apply -f deploy/argocd/rag-app.yaml
kubectl get application rag-vector-store -n argocd -w
kubectl get pod,svc -n default -l app=rag-qdrant
kubectl get pvc rag-qdrant-storage -n default
```

Wait for `Synced` / `Healthy`, then stop the watch with `Ctrl+C`.

Pull the embedding model on the same Ollama instance that is reachable at
`http://127.0.0.1:11435`:

```bash
curl -fsS http://127.0.0.1:11435/api/pull \
  -d '{"model":"qwen3-embedding:0.6b"}'
```

Set up the CLI in a virtual environment:

```bash
cd /home/Kta41/ProxyGPT
python3 -m venv /tmp/proxygpt-rag-venv
source /tmp/proxygpt-rag-venv/bin/activate
python -m pip install -e ./rag
```

In separate terminals, forward Qdrant and LiteLLM services to localhost:

```bash
kubectl port-forward -n default svc/rag-qdrant 6333:6333
```

```bash
kubectl port-forward -n default svc/litellm-service 4000:4000
```

The Qdrant API is not exposed externally. Use Kubernetes port-forwarding for
operator access; do not add an Ingress or NodePort without adding
authentication and reviewing the threat model.

## Configure and run

Qdrant and Ollama defaults work with the forwards above. To configure
generation, load the existing local environment without printing its secrets:

```bash
cd /home/Kta41/ProxyGPT
set -a
source .env
set +a
export LITELLM_API_KEY="$LITELLM_MASTER_KEY"
export LITELLM_BASE_URL="http://127.0.0.1:4000/v1"
```

Check connectivity:

```bash
proxygpt-rag doctor
proxygpt-rag doctor --check-litellm
```

Ingest Markdown from the functional configuration repository:

```bash
proxygpt-rag ingest /home/Kta41/openwebui-ai-config/knowledge
```

Ingestion is repeatable: each document's chunks have stable point IDs and are
replaced on re-ingestion. Removed source files are retained by default. To
delete points whose source files are no longer present, explicitly opt in:

```bash
proxygpt-rag ingest \
  /home/Kta41/openwebui-ai-config/knowledge \
  --prune-missing
```

Retrieve relevant passages with their source references:

```bash
proxygpt-rag search "How does Argo CD reconcile Git state?" --limit 5
```

Generate a grounded answer and print the retrieved source references:

```bash
proxygpt-rag ask "How does Argo CD reconcile Git state?" --limit 5
```

The answer prompt treats retrieved passages as untrusted data, not
instructions. Retrieved results and citations are also displayed separately
from the generated answer. This is a defense-in-depth prompt instruction, not
a guarantee against prompt injection.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `QDRANT_URL` | `http://127.0.0.1:6333` | Qdrant endpoint |
| `QDRANT_API_KEY` | unset | Optional Qdrant key, if enabled later |
| `QDRANT_COLLECTION` | derived from embedding model | Isolate vector spaces |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11435` | Ollama API |
| `RAG_EMBEDDING_MODEL` | `qwen3-embedding:0.6b` | Local embedding model |
| `RAG_GENERATION_MODEL` | `qwen3-14b` | Existing LiteLLM alias for `ask` |
| `LITELLM_BASE_URL` | `http://127.0.0.1:4000/v1` | OpenAI-compatible LiteLLM API |
| `LITELLM_API_KEY` | unset | Required only for `ask` and LiteLLM doctor check |
| `RAG_CHUNK_SIZE` | `1800` | Maximum chunk characters |
| `RAG_CHUNK_OVERLAP` | `250` | Character overlap between chunks |
| `RAG_EMBEDDING_BATCH_SIZE` | `16` | Texts sent to Ollama per request |

Changing embedding models creates a distinct default collection. If an
explicit `QDRANT_COLLECTION` is set, use a new collection when changing
embedding models; the CLI rejects vector-dimension mismatches and does not
recreate or erase a collection automatically.

## Validation

Run focused tests and the repository's manifest validation:

```bash
python3 -m pip install -e ./rag
python3 -m unittest discover -s rag/tests -v
bash scripts/validate-manifests.sh
```

Unit tests use fake embedding and vector-store backends; they do not require
the cluster, Ollama, LiteLLM, or Qdrant to be running.
