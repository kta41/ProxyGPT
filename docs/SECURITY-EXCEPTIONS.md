# M1 security exceptions

These exceptions are part of the Git desired state and must be reviewed before
changing the corresponding workload.

## LiteLLM `hostNetwork`

[`deploy/litellm/base/deployment.yaml`](../deploy/litellm/base/deployment.yaml)
uses `hostNetwork: true` and `ClusterFirstWithHostNet` so LiteLLM can reach the
host-local Ollama endpoint at `127.0.0.1:11435`.

This is intentional and is not replaced by a generic `hostPath` or privileged
container exception. A NetworkPolicy does not restrict host-network traffic,
so the operational mitigation is to keep the workload limited to the required
host-local Ollama connection and avoid exposing additional host services.

## PostgreSQL and Open WebUI persistent storage

PostgreSQL and Open WebUI write to PVC-backed application data directories.
`readOnlyRootFilesystem` is therefore not enabled in M1; enabling it requires
testing writable temporary/configuration paths first.

## Kyverno rollout mode

The initial Kyverno policies use `validationFailureAction: Audit`. This makes
the baseline observable without blocking existing workloads that still use
legacy image references or have not yet been fully hardened. Individual rules
can move to `Enforce` after the audit report is clean.

Kyverno is installed declaratively by
[`deploy/argocd/kyverno-app.yaml`](../deploy/argocd/kyverno-app.yaml). Its
sync wave runs before the `security-baseline` Application so the Kyverno CRDs
exist before the policies are applied.
