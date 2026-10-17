# Helm

## Offline validation

The CloudOps chart has a values schema, default-disabled Ingress, ServiceMonitor, and NetworkPolicy, and a guarded NetworkPolicy template. When Helm is already installed, these commands validate and render locally without contacting a cluster:

```bash
helm lint helm/cloudops
helm template cloudops helm/cloudops
```

The existing test suite also renders the chart with synthetic values and checks selectors, probes, security contexts, values validation, HPA bounds, and fail-closed NetworkPolicy selectors. `scripts/verify-local.sh` runs lint and a bounded default render when Helm is available. These checks do not prove API-server acceptance or runtime behavior.

## Deployment status and prerequisites

No Kubernetes cluster or Helm release has been deployed from this repository. GHCR publishing is disabled, so no image has been published by this workflow; the chart's image reference is a placeholder until publishing is explicitly enabled and completed or an immutable image is separately selected. A GHCR reference alone does not mean an image exists.

**Do not run a Helm install or upgrade from this runbook.** A future deployment needs separate review and authorization, an available immutable image, verified CNI readiness, confirmed ingress and Prometheus identities, and resolution of SEC-002. Helm rendering does not validate cluster-specific selectors, NetworkPolicy enforcement, storage, or resource capacity.
