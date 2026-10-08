# Kubernetes

The raw manifests demonstrate Deployment, Service, ConfigMap, Secret example, Ingress, HPA, ServiceAccount, RBAC and NetworkPolicy.

Before applying `deployment.yaml`, replace `YOUR_GITHUB_OWNER` with the GitHub owner of the public GHCR image.

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
