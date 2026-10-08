# Monitoring

Install kube-prometheus-stack:

Before installing, provision a Kubernetes Secret named `cloudops-grafana-admin` in the `monitoring` namespace using the approved secret-management process. It must contain the keys `admin-user` and `admin-password`. The Helm values reference those keys and do not store the credentials. Do not put credential values in this repository or in command-line arguments.

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace -f monitoring/prometheus-values.yaml
```

For the CloudOps application, add a ServiceMonitor after the Prometheus Operator is installed and expose `/metrics` through the Service. If `k8s/networkpolicy.yaml` is applied, its default-deny ingress blocks the Prometheus scrape on TCP port `8000` until a narrow allow rule is added for verified Prometheus namespace and pod labels. Confirm the effective ServiceMonitor and namespace selectors on the installed Prometheus resource; the local ServiceMonitor label alone does not prove discovery.
