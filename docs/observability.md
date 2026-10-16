# Observability

The application emits Prometheus metrics and one JSON request event to stdout for each completed HTTP request. Each event includes an internally generated UUID request ID, method, bounded route label, status code, and duration in milliseconds. Client-supplied request IDs are ignored. Request and response bodies, query values, credentials, and exception details are not logged; unmatched paths use the fixed `unmatched` route label. The request counter and duration histogram use the same bounded `path` labels, so arbitrary unknown paths do not create separate metric series. Unhandled application exceptions are logged with status `500` and then continue through FastAPI's normal error handling.

Kubernetes and infrastructure metrics are collected by the monitoring stack. Grafana is the common visualization layer for metrics and logs.

The CloudOps application can be discovered by Prometheus using `monitoring/service-monitor.yaml` when the Prometheus Operator's ServiceMonitor and namespace selectors include it. If `k8s/networkpolicy.yaml` is applied, its default-deny ingress also blocks scraping until a narrow allow rule is configured for verified Prometheus workload identities.
