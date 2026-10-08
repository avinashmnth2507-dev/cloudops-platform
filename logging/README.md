# Logging

Recommended low-cost lab setup:

1. Install Grafana Loki using the official Loki Helm chart.
2. Run Grafana Alloy or another supported collector on the cluster.
3. Send container logs to Loki.
4. Add Loki as a Grafana datasource.

Example Helm installation:

```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm upgrade --install loki grafana/loki --namespace monitoring --create-namespace -f logging/loki-values.yaml
```

The exact chart values should be checked against the chart version selected at deployment time because Loki chart configuration changes between releases.
