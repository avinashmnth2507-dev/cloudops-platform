# CloudOps Platform Portfolio Completion Checklist

This checklist records repository evidence, not a project completion percentage. “Locally verified” means a local test or static check ran against the current source; it does not imply a deployed service. “CI verified” is tied to the specific run and commit stated in the row.

| Area | Requirement / current state | Status | Evidence and remaining work |
|---|---|---|---|
| Application functionality | Six FastAPI metadata, health, readiness, status, info, and metrics endpoints; display configuration validation. | Locally verified | Endpoint and configuration pytest coverage. The application remains a small demo service; no cloud-resource management feature is implemented. |
| Application reliability | Internally generated request IDs, structured stdout request events, bounded method/route labels, best-effort instrumentation. | Locally verified | Request logging, exception, and metric regression tests. Operational readiness checks do not query external dependencies. |
| Containerization | Digest-pinned Alpine production image, non-root runtime, read-only Compose root, tmpfs `/tmp`, healthcheck and no-new-privileges settings. | Static-only | Dockerfile/Compose regression tests inspect configuration. No container operation was performed in this batch; verify the exact image/runtime only in a separately authorized local run. |
| CI/CD | Workflow runs tests, builds and scans an image on the configured main-push path; the GHCR publish job is disabled. | CI verified | Run #5 passed for older commit `f6ba78bcdda1a843e9cb33742826b46e98976f00`. The project owner reports Run #17 is associated with `27b884194ea7f58316f9561847503e3e082e0dc9`; no local evidence or GitHub API check was available in this task. Verify the run URL/status before making a new independent CI claim. |
| Security | Ruff, pytest, Gitleaks, strict Trivy HIGH/CRITICAL failure behavior, non-root image, and restrictive workload settings are configured. | CI verified / static-only | Historical Run #5 evidence and local structural tests. Run #17 association is owner-reported, not independently checked. A fresh CI result should be recorded for the current commit. SEC-002 remains OPEN. |
| Observability | Structured JSON request logging and bounded Prometheus HTTP metrics are implemented. | Locally verified | API and dashboard consistency tests; local demo validates `/metrics` exposition. Prometheus, Grafana, and Loki are not deployed or activated. |
| Kubernetes | Manifests define app, Service, probes, resources, and default-deny standalone ingress policy. | Static-only | Offline YAML relationship and security tests. No cluster acceptance, scheduling, ingress, CNI, or policy runtime validation. |
| Helm | Chart values schema, default rendering, security context, probes, HPA range, and fail-closed policy guards. | Locally verified / static-only | Local lint/render and offline Helm tests. No Helm release exists; NetworkPolicy remains disabled by default. |
| Infrastructure as Code | Terraform modules and dev examples describe VPC, subnet, security group, IAM, and EC2. | Static-only | Formatting checks only. No Terraform apply or AWS resource creation occurred as part of this project workflow. |
| K3s and Calico | Offline validation scaffolding exists, but both installation paths intentionally refuse installation. | Blocked | K3s and Calico provenance/image integrity, host prerequisites, cluster identity, CNI readiness, recovery, and SEC-002 remain unresolved. Installation remains NO-GO. |
| Documentation | Architecture, deployment, observability, security, Calico, monitoring, local demo, troubleshooting, and evidence guidance. | Implemented | This checklist and the linked runbooks describe static versus runtime evidence. Keep CI/run details tied to a specific commit. |
| Demonstration evidence | A loopback-only script checks six endpoints; existing local portfolio images are external to Git. | Locally verified | Script behavior has mocked tests. No live app was contacted in this task. Review screenshot provenance and capture new live evidence only when the app is intentionally run. |

## Current CI record

Run #17 is recorded here as **owner-reported association** with expected commit `27b884194ea7f58316f9561847503e3e082e0dc9`. No run metadata was present in the repository and this task did not query GitHub. Do not mark its outcome independently verified until checking the Actions run and matching SHA.

## Completion blockers

- Obtain and record independent CI evidence for the current commit.
- Resolve SEC-002 by identifying real ingress and metrics identities and designing a narrow policy, then test enforcement in an authorized disposable cluster.
- Resolve K3s/Calico artifact and image provenance, host prerequisites, installation, readiness, and partial recovery before considering any cluster deployment.
- GHCR image publishing remains intentionally disabled; manifest image references remain placeholders until publishing is separately approved and completed or a reviewed immutable image is selected.
- Terraform infrastructure, monitoring services, and production runtime behavior remain undeployed and unverified.
