# Kubernetes

The raw manifests demonstrate Deployment, Service, ConfigMap, Secret example, Ingress, HPA, ServiceAccount, RBAC and NetworkPolicy.

## Offline static validation

No cluster connection is needed to check the repository's Kubernetes YAML relationships. With the existing test environment, run:

```bash
.venv/bin/pytest -q tests/test_kubernetes_manifests.py
```

This parses the Kubernetes and monitoring YAML and checks the app Deployment/Service/Ingress selectors and ports, probe routes, namespace and ConfigMap references, resource request/limit relationships, runtime security context, NetworkPolicy intent, ServiceMonitor selectors, and dashboard metric names. It does not call `kubectl`, validate against an API server, or prove scheduling, CNI behavior, discovery, or enforcement. See [Helm offline validation](helm.md) for chart lint and render checks.

## Deployment prerequisites

**Not approved for execution.** No Kubernetes cluster has been deployed from this repository. GHCR publishing is disabled, and no approved application image is known to be published. The standalone Deployment intentionally has an empty `image` field; do not apply it until a separately reviewed and approved digest-pinned image reference is supplied. Use the full form `registry/repository@sha256:<64 lowercase hexadecimal characters>`. A configured reference does not prove that an image was published, is accessible, or was approved. Image configuration, image publication, and cluster deployment are separate steps. The CNI and NetworkPolicy enforcement are unverified, and SEC-002 remains open.

For the standalone manifest, keep the checked-in base empty and create a deployment-specific overlay or rendered copy that supplies the approved immutable reference. Inspect the resulting manifest before any separately authorized apply. Never substitute a tag-only reference or treat a syntactically valid digest as proof of publication.

The following `kubectl apply` commands are future examples only; they create or change cluster resources:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
```

## NetworkPolicy safety

`k8s/networkpolicy.yaml` selects the CloudOps pods in namespace `cloudops` and applies default-deny ingress to them. It has no ingress allow rules. Applying it blocks requests through Traefik and Prometheus scraping of `/metrics` on TCP port `8000` until narrowly scoped allow rules are added. Egress is not restricted by this policy. Whether the policy is enforced depends on the installed CNI.

Do not add source selectors until the actual workload identities and required traffic are verified. In an approved future local-cluster review, identify namespace labels and controller/scraper pod labels from the running workloads rather than inferring them from names:

```bash
kubectl get namespaces --show-labels
kubectl get deployments,statefulsets,daemonsets,pods -A --show-labels
kubectl get servicemonitors -A --show-labels
kubectl get prometheus -A -o yaml
```

For the Prometheus resource, review `spec.serviceMonitorSelector` and `spec.serviceMonitorNamespaceSelector`; verify that the CloudOps ServiceMonitor is selected. Inspect the ingress controller and Prometheus pod specifications for networking modes such as `hostNetwork`. Confirm the installed CNI and its NetworkPolicy enforcement support from the deployed CNI configuration and version-specific documentation.

The Helm NetworkPolicy remains disabled by default and requires explicit selectors when enabled. Keep it disabled until the workload identities and CNI enforcement are verified. In an approved disposable local-cluster test, verify that the intended Traefik route and `/metrics` scrape succeed after their narrow allow rules are configured, an unapproved test workload cannot reach the application on TCP `8000`, and health/readiness probes remain healthy. Local YAML parsing and Helm lint/render checks do not prove runtime policy enforcement or Prometheus discovery. Do not enable or apply a policy based on test selectors or rendered YAML alone.
