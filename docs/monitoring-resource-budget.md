# Monitoring chart and resource budget

This is a local configuration proposal for the full-observability development
profile. It does not install monitoring or establish runtime capacity,
Prometheus discovery, or storage durability.

## Chart release

The candidate is `prometheus-community/kube-prometheus-stack` **91.8.2**.
The exact release metadata declares application version `v0.94.1` (Prometheus
Operator) and `kubeVersion: ">=1.25.0-0"`. That declared Kubernetes constraint
includes the proposed Kubernetes 1.36 line, but does not prove compatibility
with the eventual k3s cluster, CRDs, or runtime configuration.

The chart archive is kept outside the repository. The command below is a
documentation-only future installation example; it was not run:

```sh
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --version 91.8.2 \
  --namespace monitoring --create-namespace \
  -f monitoring/prometheus-values.yaml
```

The installation example in `docs/monitoring.md` pins the chart at `91.8.2`.
The chart package was not installed. For OBS-006, the existing local chart
archive was linted and rendered offline with this values file; these static
checks do not establish runtime compatibility or capacity.

## Discovery scope

`monitoring/prometheus-values.yaml` selects ServiceMonitors with
`release: monitoring` and limits their namespaces to `cloudops` and
`monitoring` using Kubernetes' `kubernetes.io/metadata.name` namespace label.
The standalone and Helm CloudOps ServiceMonitor definitions use the
`release: monitoring` label and target the Service labeled `app: cloudops`,
using its named `http` port and `/metrics` path.

This configuration is intentionally narrower than selecting every monitor in
every namespace. It still permits matching monitors in both listed namespaces,
including monitors supplied by the monitoring chart. The CloudOps Helm release
must be installed into `cloudops` for its ServiceMonitor to fall inside this
namespace selection. Verify the rendered Prometheus selectors and actual
ServiceMonitor discovery after chart installation; local values do not prove
runtime discovery. If the application or monitoring namespace changes, review
and update the explicit namespace allowlist.

## Starting container resource settings

The following are initial configuration estimates, not measured usage or a
capacity guarantee. Paths were checked against the exact 91.8.2 chart and its
declared dependency values. Prometheus values preserve the repository's
existing settings; Grafana, the operator, kube-state-metrics, and node-exporter
receive explicit starting budgets.

| Component | Requests | Limits | Basis and caveat |
|---|---:|---:|---|
| Prometheus | 100m CPU, 256Mi memory | 500m CPU, 768Mi memory | Existing project values; workload and retention volume may require more. |
| Grafana main container | 100m CPU, 128Mi memory | 500m CPU, 512Mi memory | Project starting estimate at the chart's `grafana.resources` path; monitor actual use. |
| Grafana dashboard and datasource sidecars (each) | 25m CPU, 64Mi memory | 100m CPU, 128Mi memory | Project starting estimates at `grafana.sidecar.resources`; applies to both rendered long-running sidecars. |
| Prometheus Operator | 100m CPU, 100Mi memory | 200m CPU, 200Mi memory | Chart's documented example at `prometheusOperator.resources`. |
| kube-state-metrics | 10m CPU, 32Mi memory | 100m CPU, 64Mi memory | Dependency chart's documented example at `kube-state-metrics.resources`. |
| node-exporter | 100m CPU, 30Mi memory | 200m CPU, 50Mi memory | Dependency chart's documented example at `prometheus-node-exporter.resources`; one pod per node. |

The configured requests for the long-running monitoring workloads total
**460m CPU and 674Mi memory**. Configured limits total **1,700m CPU and
1,850Mi memory**. These totals include the Prometheus resources declared on its
custom resource and one node-exporter pod (the DaemonSet budget is per node).
At the application's HPA maximum of four replicas, its configured requests add
200m CPU and 256Mi memory, for combined application-plus-monitoring requests of
**660m CPU and 930Mi memory**. The application's four replicas add limits of
1,000m CPU and 1,024Mi memory, making the combined configured limits
**2,700m CPU and 2,874Mi memory**.

The OBS-006 render also has four containers without requests or limits: the
Grafana `download-dashboards` init container, the `create` and `patch`
Prometheus admission hook Jobs, and the Grafana `monitoring-test` test Pod.
They are one-shot resources and are excluded from the long-running workload
totals above, but can still consume resources during startup, hooks, or tests.

Requests are scheduler inputs, limits are ceilings, and neither sum predicts
actual runtime consumption. The totals exclude the OS, k3s control plane,
Calico, Traefik, CoreDNS, Metrics Server, the four unbudgeted one-shot
containers, and other cluster processes.

The full profile's `t3.large` is an unverified candidate (2 vCPU and 8 GiB RAM),
not a promise that the full stack will fit or remain responsive. T3 is burstable;
CPU credit behavior and account costs need review before any deployment. Measure
CPU, memory, disk, and scrape load in an approved test environment before
adjusting these budgets or treating the profile as adequate.

## Retention and storage

The project keeps its existing Prometheus retention setting of `3d`. Retention
is a time limit, not a storage-capacity guarantee. The values do not configure a
Prometheus `storageSpec`, PVC size, or StorageClass. The Terraform EC2 root
volume is 20 GiB gp3 and encrypted, but that does not configure a Kubernetes
Prometheus volume or prove available disk capacity. Decide whether monitoring
data must survive pod or node replacement, then choose and verify a storage
class and capacity before relying on persistence. Inspect the rendered
StatefulSet/Prometheus resource and actual volume binding in a future authorized
cluster review.

## Remaining verification

- The OBS-006 local chart 91.8.2 lint and render completed, and the rendered
  YAML parsed successfully. These static checks do not establish runtime
  compatibility, resource adequacy, or storage behavior.
- Confirm effective Prometheus ServiceMonitor and namespace selectors and
  successful scraping of the intended CloudOps endpoint.
- Verify Grafana's Secret reference exists at deployment time without placing
  credential values in this repository.
- Decide dashboard provisioning separately; the local dashboard JSON is not
  proven to be loaded by this configuration.
- Choose and test Prometheus storage, then measure resource and disk use on the
  intended node size before approving the full-observability profile.
