# Security Policy

## Supported versions

Security fixes are handled for the latest code on the default branch. This
repository describes a self-hosted Kubernetes platform, and deployment
security also depends on the versions and configuration of Kubernetes, K3s,
Argo CD, Kyverno, LiteLLM, Open WebUI, PostgreSQL, Qdrant, Ollama, and other
third-party components used by an installation.

## Responsible use

Deploy and operate ProxyGPT only on infrastructure you own or are explicitly
authorized to administer. Review the target cluster, namespaces, network
boundaries, exposed ingress, and permitted data flows before applying any
manifest or installer action.

Do not use this repository to access, alter, disrupt, or exfiltrate data
without authorization. Review server-side Functions and Tools as privileged
code, and do not expose internal services such as LiteLLM, PostgreSQL, Qdrant,
Ollama, or Open WebUI without an explicit authentication and network-access
policy.

## Secrets and sensitive data

Do not commit or publish `.env` files, API keys, provider credentials, GitHub
tokens, JWTs, cookies, `LITELLM_SALT_KEY`, TLS private keys, database dumps,
model data, or other sensitive material. Kubernetes Secrets and external
secret-management systems must be handled according to the security
requirements of the target cluster.

Keep `LITELLM_SALT_KEY` stable while encrypted LiteLLM credentials exist in the
database. Review generated reports, logs, manifests, and support bundles for
credentials, personal data, prompts, or other sensitive information before
sharing them.

## Reporting a vulnerability

Please do not report suspected vulnerabilities in a public GitHub issue.

Please reach out directly via email at `kta41@proton.me` without including
vulnerability details or sensitive data in a public issue.

Include, when safe to do so:

- the affected commit, component, and deployment version;
- the Kubernetes distribution and relevant configuration;
- a concise description and security impact;
- minimal, reproducible steps that do not access real third-party systems or
  data;
- any suggested mitigation or temporary workaround.

Please allow time for investigation and remediation before publishing details.
Do not include credentials, cluster access information, or production data in
the initial report.

## Scope and limitations

ProxyGPT's Git manifests are declarative desired state; a change is not
considered deployed until Argo CD has reconciled it and the resulting
workloads have passed the applicable Kyverno admission and report checks.
Security exceptions documented in
[`docs/SECURITY-EXCEPTIONS.md`](docs/SECURITY-EXCEPTIONS.md) are intentional
deployment decisions and must be reviewed before changing or broadening them.

The repository's policies and network controls are safeguards, not a guarantee
that every deployment is secure. Operators remain responsible for cluster
access, secret rotation, image provenance, backups, TLS, provider permissions,
logging, monitoring, and the security posture of dependencies and external
configuration repositories.
