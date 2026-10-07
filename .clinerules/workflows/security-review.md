# Workflow · Revisión de seguridad (ProxyGPT)

**Aplica a**: cambios en `deploy/security/`, NetworkPolicies o
`docs/SECURITY-EXCEPTIONS.md`.

## Checklist

1. **Excepciones mínimas**: cada entrada de
   `docs/SECURITY-EXCEPTIONS.md` sigue justificada y es la mínima
   posible (hostNetwork LiteLLM, UID Qdrant, capabilities PostgreSQL).
2. **Kyverno Enforce**: `deploy/security/base/kyverno-policies.yaml`
   aplica Enforce en `default`; comprobar que los cambios no rompen
   workloads legítimos (revisar `match`/`exclude` y reportes).
3. **Secretos**: `gitleaks detect --no-banner` o revisión manual de
   patrones en el diff.
4. **Efecto en runtime**: enumerar qué cambiará realmente en el clúster
   tras la reconciliación de Argo CD (el baseline de
   `scripts/validate-manifests.sh` lo vuelve a verificar en CI).
5. **Veredicto por punto**: OK / RIESGO / BLOQUEANTE.
