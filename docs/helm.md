# Helm

## Offline validation

The CloudOps chart has a values schema, default-disabled Ingress, ServiceMonitor, and NetworkPolicy, and guarded image and NetworkPolicy templates. The default image reference is empty, so linting or rendering without an explicit digest fails closed. Supply a syntactically valid, test-only fixture for offline checks:

```bash
helm lint helm/cloudops --set-string image.reference='registry.example.invalid/cloudops-platform@sha256:0000000000000000000000000000000000000000000000000000000000000000'
helm template cloudops helm/cloudops --set-string image.reference='registry.example.invalid/cloudops-platform@sha256:0000000000000000000000000000000000000000000000000000000000000000'
```

`registry.example.invalid` is reserved and the all-zero digest is fictitious. This fixture exists only to test syntax and render the chart; it is not published, approved, pullable, or suitable for deployment. Offline lint and rendering do not contact a registry or cluster. The existing test suite checks that missing references, placeholders, `latest`, tag-only, and malformed references fail, while a syntactically valid digest reference renders. It also checks selectors, probes, security contexts, HPA bounds, and fail-closed NetworkPolicy selectors. `scripts/verify-local.sh` supplies the same fixture only for local lint/render checks. These checks do not prove image existence, API-server acceptance, or runtime behavior.

## Deployment status and prerequisites

No Kubernetes cluster or Helm release has been deployed from this repository. GHCR publishing is disabled, and no approved application image is known to be published. The chart default is empty and requires an explicit immutable reference in the form `registry/repository@sha256:<64 lowercase hexadecimal characters>`. Configure the reference through a reviewed values override or values file only after its image source, publication, integrity, and approval are established. Merely supplying a syntactically valid reference does not publish an image or deploy a cluster.

**Do not run a Helm install or upgrade from this runbook.** A future deployment needs separate review and authorization, an available immutable image, verified CNI readiness, confirmed ingress and Prometheus identities, and resolution of SEC-002. Helm rendering does not validate cluster-specific selectors, NetworkPolicy enforcement, storage, or resource capacity.
