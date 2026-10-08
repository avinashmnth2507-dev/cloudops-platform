# Monitoring

## Chart and deployment status

The selected `kube-prometheus-stack` chart version is **91.8.2**. Its chart
metadata declares application version `v0.94.1` for the Prometheus Operator
and a Kubernetes constraint of `>=1.25.0-0`. That constraint includes the
proposed Kubernetes 1.36 release, but runtime compatibility with the eventual
k3s cluster, CRDs, and configuration remains unverified.

For OBS-006, chart version 91.8.2 was linted and rendered locally as release
`monitoring` in namespace `monitoring`, targeting Kubernetes 1.36.5 with CRDs
included. The Prometheus discovery selectors were inspected in the rendered
YAML. For OBS-008, the CloudOps chart was rendered locally as release
`cloudops` in namespace `cloudops` with its ServiceMonitor enabled and release
label set to `monitoring`. No monitoring stack has been deployed. These local
checks do not verify runtime Kubernetes compatibility, capacity, or metric
scraping.

Monitoring is not installed or activated. The command below is documentation
only and is **not approved for execution**. It preserves the `monitoring`
release and namespace and pins the chart version:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --version 91.8.2 \
  --namespace monitoring --create-namespace \
  -f monitoring/prometheus-values.yaml
```

The resource requests and limits are configured in
[`monitoring/prometheus-values.yaml`](../monitoring/prometheus-values.yaml) and
are starting estimates, not measured usage or a capacity guarantee. The
full-observability `t3.large` profile is an untested capacity estimate. See
[`monitoring-resource-budget.md`](monitoring-resource-budget.md) for the budget
and its omissions.

## Grafana Secret prerequisite

Before installing, provision a Kubernetes Secret named `cloudops-grafana-admin` in the `monitoring` namespace using the approved secret-management process. It must contain the keys `admin-user` and `admin-password`. The Helm values reference those keys and do not store the credentials. Do not put credential values in this repository or in command-line arguments.

Creating that Secret and provisioning its credentials are separate steps and
are not authorized by this documentation change. No password or token is
stored here. For the documented chart release in namespace `monitoring`, the
Secret must exist in that namespace with the two configured key names.

## ServiceMonitor discovery and storage

The values explicitly select ServiceMonitors labeled `release: monitoring` in
the `cloudops` and `monitoring` namespaces. This is a namespace-bounded
selector, but it can select multiple matching monitors within those
namespaces; it does not uniquely identify only the CloudOps monitor. The
standalone ServiceMonitor is in `cloudops` and carries that release label.
The CloudOps Helm ServiceMonitor uses the configured release label and is
rendered for the Helm release namespace `cloudops`; its template omits an
explicit `metadata.namespace`. The local render confirmed the label
`release: monitoring` and the `app: cloudops` Service selector match the
rendered Prometheus selectors and CloudOps Service. The Service exposes the named
`http` port, which targets the application container on port `8000`; the
ServiceMonitor uses that port and the `/metrics` path. The Prometheus chart
render also confirmed ServiceMonitor namespace selection for `cloudops` and
`monitoring`. These checks establish static configuration compatibility only:
actual discovery and metric scraping remain unverified.

Prometheus retention is configured for three days. Persistent storage, actual
disk usage, and storage durability are not established: the values do not
specify a Prometheus storage spec, PVC size, or StorageClass. The EC2 root disk
setting does not itself configure a Prometheus volume.

The CloudOps chart's ServiceMonitor is disabled by default. When deploying the
application, enable it explicitly or use the standalone ServiceMonitor after
the Prometheus Operator CRDs are available, and expose `/metrics` through the
Service. If `k8s/networkpolicy.yaml` is applied, its default-deny ingress blocks
the Prometheus scrape on TCP port `8000` until a narrow allow rule is added for
verified Prometheus namespace and pod labels. Confirm the effective
ServiceMonitor and namespace selectors on the installed Prometheus resource;
local rendering does not prove discovery or scraping.

SEC-002 remains open. Do not treat local selector configuration or static
rendering as proof of NetworkPolicy enforcement or Prometheus scraping.
