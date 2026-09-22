# AI configuration GitOps

This project keeps infrastructure and the LiteLLM gateway configuration in
this repository. Open WebUI workspace content is maintained in the separate
`../openwebui-ai-config` repository and is applied through the Open WebUI API.

## Ownership

- `deploy/litellm/base/config.yaml`: LiteLLM models, routing and proxy
  settings.
- `../openwebui-ai-config/models/*.json`: Open WebUI custom models, including
  system prompts, tools, knowledge bases and permissions.
- `../openwebui-ai-config/knowledge/.oikb.yaml`: knowledge-base sources synced
  by the official `oikb` tool.
- `../openwebui-ai-config/rag/rag-config.json`: Open WebUI RAG retrieval and
  parsing configuration.
- Kubernetes Secrets: API keys and other credentials. They must not be stored
  in either repository.

LiteLLM models must have one source of truth. This installation uses
`config.yaml`; do not edit the same models from the LiteLLM Admin UI.

## Applying Open WebUI models

The synchronizer uses the administrative reconciliation endpoint:

```bash
OPENWEBUI_URL=https://ia.kta41.local \
OPENWEBUI_API_KEY="$OPENWEBUI_API_KEY" \
scripts/sync-openwebui-config.sh ../openwebui-ai-config
```

`/api/v1/models/sync` creates and updates models and removes models that are
absent from the repository payload. Run it only after reviewing the diff.
Use `--dry-run` to validate the payload without changing Open WebUI.

The endpoint is administrative and experimental. Pin the Open WebUI image
before enabling automated reconciliation and keep the API key in a Kubernetes
Secret or an external secret manager.

RAG changes that affect embeddings, PDF parsing, chunk size, overlap, or
minimum chunk size require re-indexing existing knowledge bases. Retrieval-only
changes such as `top_k`, reranker limits, relevance threshold, and hybrid-search
weights do not normally require re-indexing.

## Rollout

1. Open a pull request in the configuration repository.
2. Validate JSON and Markdown in its CI.
3. Review model deletions and prompt changes.
4. Run the synchronizer from a trusted runner with network access to Open WebUI.
5. Verify LiteLLM `/health`, Open WebUI `/api/models`, a chat request and any
   configured tool or knowledge-base query.

The initial implementation deliberately does not export or version chats,
users, JWTs, API keys, the Open WebUI database, or the PVC.
