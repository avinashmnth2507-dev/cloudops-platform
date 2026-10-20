# CloudOps Platform — Portfolio Summary

## Project

CloudOps Platform is a small FastAPI service surrounded by a locally validated application-delivery path and deployment configuration prepared for future review. The project demonstrates how to pair a simple API with dependency integrity, container hardening, CI security checks, observability instrumentation, and fail-closed Kubernetes configuration.

It is a portfolio project, not a production service. No AWS infrastructure, Kubernetes cluster, Helm release, or monitoring stack has been deployed. GHCR publishing remains disabled and no image has been published.

## Technology

Python 3.13, FastAPI, Uvicorn, Pydantic Settings, pytest, Ruff, pip-compatible hash-verified dependency locks, Docker, Docker Compose, GitHub Actions, Gitleaks, Trivy, Terraform, Kubernetes, Helm, Prometheus client instrumentation, Grafana configuration, and Loki configuration.

## Engineering highlights

- Six API endpoints for metadata, liveness, readiness, service status, runtime information, and Prometheus exposition.
- Structured JSON request events with internal request IDs, bounded route/method labels, and instrumentation that does not replace application responses.
- Digest-pinned Alpine production base with an exact, hash-verified, binary-only runtime lock; non-root execution and an HTTP healthcheck.
- Hardened local Compose settings: loopback-only port publishing, all capabilities dropped, read-only root filesystem, `/tmp` tmpfs, and no-new-privileges.
- GitHub Actions test path with hash-required dependencies, Ruff, pytest, and Gitleaks; main-branch image build with a Trivy HIGH/CRITICAL failure gate.
- Offline Kubernetes and Helm validation for image references, probes, resources, pod/container security, Service wiring, HPA settings, and fail-closed NetworkPolicy selectors.
- Guarded K3s/Calico preparation and detailed deployment, cost, security, and rollback documentation.

## Verification evidence

GitHub Actions [run 39468033513](https://github.com/avinashmnth2507-dev/cloudops-platform/actions/runs/39468033513) passed for commit `8e711c8a5338b68fde1bff1ba928088d424c41e9`. Ruff, 178 pytest tests, Gitleaks, the Linux amd64 image build, and the configured Trivy gate passed. Image handoff and GHCR publication were skipped. That run verifies its commit and predates the current documentation edits.

The [DEV-015 local verification report](local-verification-report.md) records a secured local container and successful HTTP 200 responses from all six endpoints, plus incrementing Prometheus request counters. That image was built from a dirty local worktree with the state disclosed in the report. It is local demonstration evidence, not cloud or cluster deployment evidence. The [portfolio evidence index](portfolio-evidence.md) records provenance and limits for each item.

## Known limits

- No cloud resources, Kubernetes cluster, Helm release, or Prometheus/Grafana/Loki services have been deployed.
- The Kubernetes image must be supplied as an approved immutable digest; configuration does not publish an image.
- NetworkPolicy enforcement, ingress and monitoring workload identities, and CNI readiness are unverified. **SEC-002 remains OPEN.**
- K3s and Calico installation remain **NO-GO** pending provenance, artifact verification, host compatibility, CNI readiness, and recovery evidence.
- HPA needs a working Metrics API. Prometheus discovery, scrape success, storage, Grafana dashboard provisioning, and Loki collection are unverified.
- Terraform examples can create billable resources and have not been applied.
- Dependency hashes establish artifact integrity against approved values, not publisher authenticity. CI and Trivy checks do not certify production runtime security.
- The service does not manage cloud resources and has no production user, uptime, performance, or certification claims.

## Resume bullet options

- Built a FastAPI service with health and readiness endpoints, structured JSON request events, bounded Prometheus metrics, and regression coverage for instrumentation and error handling.
- Added hash-verified runtime and CI dependency locks and a hardened Docker/Compose path; CI verifies tests, secret scanning, image builds, and a HIGH/CRITICAL vulnerability gate while keeping publication disabled.
- Prepared offline-tested Kubernetes and Helm configuration with immutable-image validation and security defaults, documenting the runtime, identity, and CNI checks still required before deployment.

These bullets describe repository implementation and verification only. They do not claim production use, cloud deployment, image publication, or measured performance improvements.
