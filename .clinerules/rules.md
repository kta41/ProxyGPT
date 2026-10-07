# Reglas de workspace — ProxyGPT (infraestructura GitOps)

> Este archivo complementa las reglas globales de `~/.clinerules/` (repo
> `cline-config`). Ante conflicto, prevalecen las globales de seguridad.

## Fuentes de verdad (leer antes de tocar nada)

- `docs/CONFIG-GITOPS.md` — arquitectura y flujo GitOps del stack.
- `docs/INSTALL.md` — instalación y operación del repositorio.
- `docs/ROADMAP.md` — hoja de ruta (archivo LOCAL-ONLY: está en
  `.gitignore`, no viaja en Git).
- `docs/SECURITY-EXCEPTIONS.md` — registro de excepciones de seguridad
  (hostNetwork LiteLLM, UID Qdrant, capabilities PostgreSQL).
- Secundarios: `README.md`, `Security.md`, `docs/AI-SECURITY.md`,
  `docs/RAG.md`, `docs/OPENWEBUI-GITOPS.md`.

## Límites duros de este repo

1. **La configuración funcional de Open WebUI (modelos, tools, RAG,
   knowledge) vive en el repo hermano `openwebui-ai-config`, NO aquí.**
   En ProxyGPT solo vive su despliegue (`deploy/openwebui/`) y el script
   de sincronización (`scripts/sync-openwebui-config.sh`).
2. **Prohibido mutar el clúster**: Argo CD es el único aplicador. Solo
   `kubectl get/describe/logs/top/events` y render local con
   `kubectl kustomize`. Nunca `apply/delete/patch/scale/rollout` ni
   `helm`.
3. **Prohibido el push directo a `main`** (repo público): siempre rama
   feature + PR; el CI valida Gitleaks, Trivy y manifests.
4. **`.env` existe localmente con secretos reales** y está en
   `.gitignore`: está PROHIBIDO leerlo o reproducir su contenido. Solo
   `.env.example` puede consultarse.
5. Los PVCs con pruning deshabilitado no se tocan en reconciliaciones.
6. Cambios en workloads con excepción de seguridad documentada →
   actualizar `docs/SECURITY-EXCEPTIONS.md` en el mismo PR.

## Estructura y validación

- Kustomize: `deploy/<componente>/base` + `deploy/<componente>/overlays/prod`
  (`deploy/postgres` se renderiza directo desde `base/`, sin overlay).
- Kustomizations reales: `deploy/postgres/base`,
  `deploy/litellm/overlays/prod`, `deploy/openwebui/overlays/prod`,
  `deploy/mcp/overlays/prod`, `deploy/security/overlays/prod`,
  `deploy/rag/overlays/prod`.
- Validar siempre con `bash scripts/validate-manifests.sh` antes de PR.
- Commits convencionales con scope, en inglés (`feat(litellm): …`).
- Español en conversación; inglés en código, comentarios y commits.

## Workflows

Usar los workflows de `.clinerules/workflows/` para este repo:
`validate.md` (pre-PR), `incident-debug.md` (incidentes) y
`security-review.md` (cambios de seguridad).
