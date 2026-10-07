[Added/Changed] - 2026-10-07
LiteLLM / Ollama connectivity

    The Ollama endpoint was configurable during installation but the generated
    LiteLLM Deployment still hardcoded 127.0.0.1:11435. The production
    Kustomize overlay now propagates OLLAMA_API_BASE into the Deployment, and
    the LiteLLM egress policy explicitly allows TCP 11435. This keeps Git,
    Argo CD, and the runtime endpoint aligned.
    For WSL2 with Ollama on Windows, the installer now defaults to the Windows
    host address from /etc/resolv.conf instead of the WSL loopback address.
    Runtime fix verified on 2026-10-07: Windows Ollama was listening on IPv6
    :::11435 while WSL could not reach the Windows loopback over IPv4. The
    working bridge is a Windows netsh portproxy rule from IPv4 0.0.0.0:11435
    to IPv6 ::1:11435, with an inbound Windows Firewall rule for TCP 11435.
    WSL reaches Ollama through http://10.255.255.254:11435/api/tags. The
    corresponding commands are:

      netsh interface portproxy add v4tov6 listenaddress=0.0.0.0 listenport=11435 connectaddress=::1 connectport=11435
      New-NetFirewallRule -DisplayName "Ollama WSL 11435" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 11435 -Profile Domain,Private,Public

    Do not use 192.168.1.1 as the Ollama endpoint; it is the LAN gateway.
    Do not use 0.0.0.0 as a client destination. Set
    OLLAMA_API_BASE=http://10.255.255.254:11435 in the local .env and let
    Argo CD reconcile the LiteLLM overlay.

[Added/Changed] - 2026-09-09
Argo CD / K3s Infrastructure on WSL2

    argocd-repo-server Network Bypass: The Argo CD repository server deployment
    was modified to use the host network (`hostNetwork: true`). This avoids
    silent packet drops (MTU/TCP checksum offloading) in WSL2 NAT when downloading
    large packages (`git-upload-pack`) from GitHub, resolving `context deadline
    exceeded` errors.

    Hybrid DNS Resolution: The `dnsPolicy: ClusterFirstWithHostNet` policy was
    injected into the `argocd-repo-server` pod. This compensates for the loss of
    Kubernetes DNS caused by the network bypass, allowing the component to
    resolve internal service names such as `argocd-redis` while retaining Internet
    access through the host.

    GitOps Path Correction: The Argo CD Application definition for deploying the
    ProxyGPT project was corrected. The `spec.source.path` block now points to
    the correct relative path inside the remote repository (`deploy/litellm/base`)
    instead of referencing the local filesystem, resolving the `app path does not
    exist` error.
