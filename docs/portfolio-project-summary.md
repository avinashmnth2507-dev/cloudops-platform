# CloudOps Platform — Portfolio Summary

## Project

CloudOps Platform is a DevOps portfolio project built around a small FastAPI service. It demonstrates an application delivery path and the supporting security, observability, container, CI, infrastructure-as-code, Kubernetes, and Helm configuration without presenting undeployed infrastructure as operational.

## Technology

Python 3.13, FastAPI, Uvicorn, Pydantic Settings, pytest, Ruff, Docker, Docker Compose, GitHub Actions, Gitleaks, Trivy, Terraform, Kubernetes, Helm, Prometheus, Grafana, and Loki configuration.

## Implementation highlights

- Six API endpoints for metadata, health, readiness, status, runtime information, and Prometheus exposition.
- Structured JSON request events with internally generated request IDs and bounded method/route labels; instrumentation failures are isolated from application responses.
- A pinned Alpine production image and Compose hardening settings, including a non-root runtime, read-only root filesystem, `/tmp` tmpfs, and `no-new-privileges`.
- GitHub Actions checks Ruff, pytest, and Gitleaks, then builds and scans the image with Trivy on main pushes. GHCR publishing is disabled.
- Offline validation paths for K3s and Calico. The K3s script refuses installation; Calico has a guarded `--apply` path that is not authorized while the project remains NO-GO pending integrity, image, host, cluster-identity, and recovery decisions.

## Verification performed

GitHub Actions run [39019245360](https://github.com/avinashmnth2507-dev/cloudops-platform/actions/runs/39019245360) passed for commit `068f3c8c67e754a19a092c79764a7b24fa40c0c1`; its test and image jobs succeeded, and its publish job was skipped. Local validation reported 139 passing tests, passing Ruff, shell syntax, Helm lint/render, and Terraform formatting.

The existing Compose container was inspected but was stopped. The loopback application probe was refused, so no live API, metrics, or healthy-container result is claimed. The [local verification report](local-verification-report.md) records the container’s stored security configuration and why it was not started.

## Known limitations

- No AWS resources, Kubernetes cluster, Helm release, or Prometheus/Grafana/Loki deployment has been created by this workflow.
- GHCR publishing remains disabled and deployment image references are placeholders.
- The existing stopped Compose container binds port 8000 on all host interfaces and has no dropped capabilities. Its local image cannot be tied to a source revision. It was not started.
- SEC-002 remains open because ingress and metrics identities and NetworkPolicy enforcement are unverified.
- K3s and Calico bootstrap paths remain NO-GO. Their integrity and runtime prerequisites are unresolved.

## Resume bullet options

- Built a FastAPI service with health/readiness endpoints, structured JSON request logs, bounded Prometheus metrics, and regression tests for request and instrumentation failures.
- Implemented a GitHub Actions pipeline for Ruff, pytest, Gitleaks, container build, and strict Trivy scanning; verified a successful run while keeping GHCR publishing disabled.
- Added offline Kubernetes/Helm and Terraform validation plus fail-closed K3s/Calico bootstrap checks, documenting deployment prerequisites and unresolved security gates.

These bullets describe repository implementation and verification only; they do not claim production use, cloud deployment, or measured performance improvements.
