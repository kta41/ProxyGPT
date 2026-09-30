# Optional Langfuse deployment

`deploy/optional/langfuse-app.yaml` prepares the official Langfuse Helm chart
(`2.1.3`) as an optional Argo CD Application. It is not part of the normal
`deploy/argocd/` bootstrap set. The chart Ingress is disabled, sign-up is
disabled, chart telemetry is disabled, and the web service remains internal
until an operator deliberately configures exposure.

## Prerequisites

The official chart v2 deploys ClickHouse through the ClickHouse Kubernetes
Operator. It requires Kubernetes 1.28 or newer, cert-manager, the
ClickHouse Operator, and their CRDs before synchronization. The current
cluster has cert-manager and is on Kubernetes `v1.36.4+k3s1`, but the latest
resource check found no ClickHouse operator API resources. Do not create the
Langfuse Application in Argo CD until the operator and its CRDs are installed
declaratively and healthy.

The chart bundles PostgreSQL, Valkey, ClickHouse, and SeaweedFS by default.
Review PVC sizes, storage class, resource requests, backup/restore, and
available cluster capacity before enabling it. These stores are independent
of ProxyGPT's existing PostgreSQL and Qdrant. No Langfuse backup or
high-availability policy is defined here.

Langfuse targets its own `langfuse` namespace. M1's Kyverno policies and
NetworkPolicies currently cover the application namespace `default`, not
`langfuse`; add a reviewed Langfuse namespace policy set before treating the
deployment as production-ready.

## Enable through GitOps

1. Add and validate the selected ClickHouse Operator installation as a
   separately managed Argo CD Application. Confirm its CRDs and cert-manager
   dependencies are `Healthy`.
2. Review the upstream [Langfuse Helm chart values](https://github.com/langfuse/langfuse-k8s)
   at the pinned chart version, especially storage, resource limits, and
   network access. Keep ingress disabled until TLS hostname, authentication,
   and access policy are explicitly selected.
3. Apply `deploy/optional/langfuse-app.yaml` once to the `argocd` namespace.
   Argo CD then owns subsequent reconciliation. Do not install the chart
   separately with `helm install`.
4. Wait for the `langfuse` Application and all its workloads/PVCs to become
   healthy. Create an operator account and a project, then store Langfuse
   public/secret API credentials in a Kubernetes Secret, never in Git.
5. Only after confirming the chart's web/worker health and API credentials,
   configure LiteLLM's Langfuse callback and verify a trace with a non-sensitive
   test request. Do not enable in-app agents or other tool-execution features
   as part of this observability rollout.

The optional Application does not yet configure LiteLLM callbacks or Ingress.
Those changes require actual Langfuse API credentials and a selected
operator-controlled hostname; until then, observability is prepared but not
active.
