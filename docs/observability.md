# Observability

The application emits Prometheus metrics and structured application events to stdout. Kubernetes and infrastructure metrics are collected by the monitoring stack. Grafana is the common visualization layer for metrics and logs.

The CloudOps application can be discovered by Prometheus using `monitoring/service-monitor.yaml` when the Prometheus Operator's ServiceMonitor and namespace selectors include it. If `k8s/networkpolicy.yaml` is applied, its default-deny ingress also blocks scraping until a narrow allow rule is configured for verified Prometheus workload identities.
