# Workflow · Debug de incidentes (ProxyGPT)

## Pasos

1. **Estado GitOps**: `kubectl get applications -n argocd` → ¿Synced y
   Healthy en todo el stack?
2. **Pods**: `kubectl get pods -A` filtrando el stack: litellm,
   open-webui, postgres, qdrant, mcp, rag.
3. **CrashLoopBackOff**: leer SIEMPRE la instancia caída:
   `kubectl logs <pod> -n <ns> --previous`.
4. **Errores Alembic** (PostgreSQL / Open WebUI): comparar la revisión
   de la DB con el pin de imagen; SOLO proponer el camino de migración,
   nunca ejecutar nada contra la DB.
5. **Conectividad**: revisar NetworkPolicies (las de `deploy/mcp/` y
   `deploy/security/`) y reportes de Kyverno (Enforce en `default`).
   Recordatorio: LiteLLM usa hostNetwork hacia Ollama local
   (`192.168.1.141:4001`); es una excepción documentada en
   `docs/SECURITY-EXCEPTIONS.md`: **no se "arregla" eliminándola**.
6. **Documentar** causa raíz + fix aplicado o propuesto antes de cerrar
   el incidente.
