# Workflow · Validación pre-PR (ProxyGPT)

**Objetivo**: dejar un cambio listo para PR: sin secretos, sin drift y
con render limpio.

## Pasos

1. `bash scripts/validate-manifests.sh` — ejecuta las 4 fases del repo:
   sintaxis shell, escaneo YAML (`deploy/`, `Infrastructure/`,
   `.github/`), render de overlays y baseline de hardening (Kyverno
   Enforce, securityContext, resources de todos los contenedores).
2. Render explícito de cada kustomization:
   - `kubectl kustomize deploy/postgres/base > /dev/null`
   - `kubectl kustomize deploy/litellm/overlays/prod > /dev/null`
   - `kubectl kustomize deploy/openwebui/overlays/prod > /dev/null`
   - `kubectl kustomize deploy/mcp/overlays/prod > /dev/null`
   - `kubectl kustomize deploy/security/overlays/prod > /dev/null`
   - `kubectl kustomize deploy/rag/overlays/prod > /dev/null`
3. Verificar que el diff **no introduce**:
   - secretos en claro,
   - imágenes con tag flotante (`:latest`, `:main`, …),
   - `hostPath` no documentado,
   - cambios en políticas Kyverno
     (`deploy/security/base/kyverno-policies.yaml`) sin mención
     explícita en el PR,
   - modificaciones en `docs/SECURITY-EXCEPTIONS.md` sin justificación.
4. Si el cambio toca RAG (`deploy/rag/`, `rag/`):
   - chunking / embeddings / modelo de embedding → **requiere
     reindexado** (avisarlo en el PR),
   - retrieval-only (top_k, reranker, umbral) → no lo requiere.
5. **Salida**: tabla con archivos tocados, riesgos y veredicto
   listo-para-PR.

## Regla final

**Nunca pushear ni aplicar nada sin confirmación explícita.** El push a
la rama feature lo hace el humano; el merge lo deciden CI y revisión.
