# Local CloudOps Demonstration

This runbook demonstrates the existing FastAPI application using tools and dependencies that are already installed. The demo script uses the repository `.venv` when present, otherwise the existing `python3` on `PATH`; it never installs dependencies. It never starts or stops an application, Docker container, cluster, or cloud resource. It sends only bounded HTTP GET requests to numeric loopback addresses.

## Start the application manually

From the repository root, use the existing virtual environment:

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

This command is documented for a person who chooses to run the local demonstration. It was not run as part of this repository task. Leave the server terminal open while checking the app. If `.venv/bin/uvicorn` or the existing dependencies are unavailable, stop and record that prerequisite; this runbook does not install packages.

## Run the checks

In a second terminal, from any working directory, run the repository script:

```bash
/path/to/cloudops-platform-full/scripts/demo-local.sh
```

The default endpoint is `http://127.0.0.1:8000`. An alternate endpoint can be supplied explicitly, but the host must be a numeric loopback IP such as `127.0.0.1` or `::1`:

```bash
/path/to/cloudops-platform-full/scripts/demo-local.sh \
  --base-url http://127.0.0.1:8000 \
  --timeout 3
```

Hostnames, remote hosts, HTTPS URLs, credentials, URL paths, queries, fragments, and redirects are rejected or not followed. Each request has a bounded timeout (default 3 seconds; accepted range 0.05–30 seconds), and each response is limited to 1 MiB. The script prints endpoint, status, and expected media type only; it never prints response bodies, headers, or exception text. Any failed endpoint makes the process exit nonzero.

## Expected endpoints

| Endpoint | Purpose | Expected result |
|---|---|---|
| `/` | Application metadata | HTTP 200, valid JSON |
| `/health` | Liveness | HTTP 200, valid JSON |
| `/ready` | Readiness | HTTP 200, valid JSON |
| `/api/v1/status` | Service status | HTTP 200, valid JSON |
| `/api/v1/info` | Runtime information | HTTP 200, valid JSON |
| `/metrics` | Prometheus exposition | HTTP 200, text exposition with the request counter and latency histogram bucket series |

Liveness and readiness are checked independently and shown with different labels. The current endpoints return process/application status; readiness does not check external services. Metrics parsing verifies the exposition format and presence of `cloudops_http_requests_total` and `cloudops_http_request_duration_seconds_bucket`.

## Interpret a failure

- `unavailable or timed out`: confirm the server is already running at the selected loopback address and port. The script does not attempt a restart.
- `expected HTTP 200`: inspect the server's own terminal and endpoint behavior; the response body is intentionally not printed.
- `expected ... content type` or invalid JSON: review the API response contract and run the offline pytest suite.
- malformed or missing metrics: review `/metrics`, `app/metrics.py`, and the existing metrics tests.
- invalid base URL: use an `http://` URL with a numeric loopback IP and no credentials, path, query, or fragment.

## Stop the manually started server

In the terminal where Uvicorn is running, press **Ctrl+C** once and wait for it to exit. The demo script never stops the server for you.

## What the demo proves

A successful run shows that the six endpoints of the application reachable at that moment returned the expected statuses and response formats. It does not prove that a Compose image is current, that Docker or CI passed for a particular commit, that GHCR published an image, or that Terraform, Kubernetes, Helm, Prometheus, Grafana, Loki, K3s, or Calico are deployed. It also does not prove NetworkPolicy enforcement, production readiness, or cloud behavior.
