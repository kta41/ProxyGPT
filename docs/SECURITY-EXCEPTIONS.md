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

The official PostgreSQL image also performs ownership and permission changes
when it starts against the existing PVC. The PostgreSQL container does not
drop all Linux capabilities in M1 because doing so causes startup failure with
`Operation not permitted`; the pod-level `RuntimeDefault` seccomp profile and
resource limits remain enabled.

## Kyverno policy scope and rollout

The checked-in policies use `validationFailureAction: Enforce` and match only
Pods in `default`, the namespace targeted by the ProxyGPT application
Applications. The manifests enforce explicit non-privileged containers,
disabled privilege escalation, `RuntimeDefault` seccomp, resource bounds,
non-`latest` images, and no unreviewed `hostPath`.

Namespaces used by Argo CD, cert-manager, Kubernetes, and Kyverno are outside
this policy scope because they are managed by platform tooling and are not
owned by the ProxyGPT application manifests. Their security posture requires
separate review before broadening the scope. M1 is complete at runtime only
after Argo CD has reconciled these Git changes and current application
workloads pass admission/report checks.

## Qdrant process UID

The pinned official Qdrant image (`qdrant/qdrant:v1.19.1`) defaults to UID 0.
M2 keeps that UID because the provided image is built with `USER_ID=0`; changing
to a non-root UID without using a compatible image variant would make its
storage paths unsupported. The Qdrant service is ClusterIP-only, its data is
PVC-backed, the deployment disables privilege escalation and drops all Linux
capabilities, and its NetworkPolicy only allows selected in-cluster clients.
Do not expose the API externally without authentication.

Kyverno is installed declaratively by
[`deploy/argocd/kyverno-app.yaml`](../deploy/argocd/kyverno-app.yaml) in the
existing Argo CD namespace (`argocd`). The security Application is also
created in `argocd` and tolerates the short interval in which Kyverno CRDs
are still being installed; Argo CD retries until the policies can be applied.
The Kyverno Application uses server-side apply because its CRDs exceed the
Kubernetes client-side annotation limit.
Argo CD ignores generated CRD metadata annotations for this Application so
server-side ownership metadata does not produce a false `OutOfSync` state.
