# Observability

## Application request events

The FastAPI middleware attempts one structured JSON request event on stdout for each request, including 404 responses and unhandled exceptions recorded with status `500`. The event contains:

| Field | Meaning |
|---|---|
| `event` | `http_request_completed` |
| `request_id` | Internally generated UUID; client-supplied request IDs are ignored. |
| `method` | Recognized HTTP method, or `OTHER` for an unrecognized method. |
| `route` | An allowlisted route template, or the fixed `unmatched` value. |
| `status_code` | HTTP response status, or `500` for an unhandled application exception. |
| `duration_ms` | Request duration in milliseconds. |

Request and response bodies, query-string values, headers, credentials, and exception messages are not included. The middleware re-raises application exceptions and treats metrics and logging as best-effort instrumentation: it attempts each operation once and does not let instrumentation exceptions replace the application response or exception. A failed metric or logger operation can therefore leave telemetry missing for that request.

## Prometheus metrics

The FastAPI `/metrics` endpoint exposes these application metrics:

- `cloudops_http_requests_total` — Counter with `method`, `path`, and `status` labels.
- `cloudops_http_request_duration_seconds` — Histogram with `method` and `path` labels; histogram observations are in seconds and are exported with `_bucket`, `_sum`, and `_count` series.

The `path` label uses an allowlisted route template; unmatched paths share the fixed `unmatched` value. The Prometheus `method` label uses the HTTP method value. No query strings are used as labels. The request event's method field is bounded to recognized methods or `OTHER`.

The application endpoint and metrics instrumentation are implemented locally. Prometheus, Grafana, and infrastructure monitoring have not been deployed or activated, so no running monitoring stack, scrape, or dashboard is established by these files. Kubernetes and infrastructure metrics would be collected only after a separately reviewed monitoring deployment. See [monitoring status](monitoring.md) and [architecture status](architecture.md).

## Local verification

The following examples issue only bounded GET requests. Run them only when an application instance is already available at `127.0.0.1:8000`; they do not start, stop, restart, or recreate it. They send no credentials or sensitive values.

```bash
for path in / /health /ready /api/v1/status /api/v1/info /metrics; do
  curl --silent --show-error --max-time 3 --max-filesize 65536 \
    --output /dev/null \
    --write-out "$path HTTP %{http_code} content-type %{content_type}\n" \
    "http://127.0.0.1:8000$path"
done
```

To inspect only the application metric definitions and series from the text exposition:

```bash
curl --silent --show-error --max-time 3 --max-filesize 65536 \
  http://127.0.0.1:8000/metrics \
  | grep -E '^# (HELP|TYPE) cloudops_http_(requests_total|request_duration_seconds)|^cloudops_http_(requests_total|request_duration_seconds)(_bucket|_sum|_count)?\{'
```

Request events are written to the application process's stdout. For a directly launched server, inspect the terminal where that already-running process writes output. If an existing Compose service and its logs are accessible, this read-only command displays its recent stdout/stderr without starting or recreating containers:

```bash
docker compose logs --no-color --tail=100 app
```

These instructions do not establish that a local application or Compose container is currently running. Do not use startup or restart commands as part of a read-only verification.

## Monitoring configuration

The CloudOps application can be discovered by Prometheus using `monitoring/service-monitor.yaml` when the Prometheus Operator's ServiceMonitor and namespace selectors include it. If `k8s/networkpolicy.yaml` is applied, its default-deny ingress also blocks scraping until a narrow allow rule is configured for verified Prometheus workload identities. SEC-002 remains open; keep the NetworkPolicy disabled until the required identities and CNI enforcement are verified.
