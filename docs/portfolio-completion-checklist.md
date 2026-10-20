# CloudOps Platform Portfolio Completion Checklist

This checklist describes repository evidence, not project completion percentage or production readiness. No AWS infrastructure, Kubernetes cluster, Helm release, or monitoring stack has been deployed. GHCR publishing is disabled.

| Status | Meaning |
|---|---|
| Implemented and validated | Code or configuration has local tests or an exact-commit CI result. Validation scope is stated. |
| Prepared or documented only | Configuration or procedures exist; runtime behavior has not been verified. |
| Blocked | A security, integrity, or runtime prerequisite prevents safe activation. |
| Not implemented | The capability is not provided by the repository. |

| Area | Current state | Status | Evidence and remaining work |
|---|---|---|---|
| FastAPI application | Six endpoints, validated settings, structured request events, bounded labels, counters, and latency histogram. | Implemented and validated | Current local pytest suite covers endpoint and instrumentation behavior. Readiness reports app/process readiness only; it does not check external dependencies. |
| Local API demonstration | Bounded loopback checker validates all six responses and parses Prometheus exposition. | Implemented and locally demonstrated | DEV-015 recorded six HTTP 200 responses and request counters from a local container. That run used a disclosed dirty worktree and is historical local evidence, not a current deployment. |
| Production Docker image | Digest-pinned Python Alpine base, hash-verified binary-only runtime lock, non-root user, healthcheck. | Implemented and validated | Local DEV-015 build/runtime inspection and the later exact-commit CI image build provide evidence. No image was published. |
| Docker Compose | Loopback-only binding, all capabilities dropped, non-root image, read-only root, `/tmp` tmpfs, no-new-privileges. | Implemented and locally validated | Compose tests and the DEV-015 secure local run cover configuration/runtime at that time. No container was started for the current documentation task. |
| Dependency integrity | Separate Alpine runtime and Ubuntu development locks pin exact versions and SHA-256 artifact hashes. | Implemented and validated | Hash-required target installs were recorded in DEV-037; CI dependency installation passed in run 39468033513. Hashes do not authenticate package publishers. |
| CI, Ruff, and pytest | Pull-request/main test job; main image build and scan; publication guards remain disabled. | Implemented and CI-validated | [Run 39468033513](https://github.com/avinashmnth2507-dev/cloudops-platform/actions/runs/39468033513) passed for `8e711c8a5338b68fde1bff1ba928088d424c41e9`; Ruff and 178 tests passed. The current portfolio docs are later working-tree edits and are not covered by that run. |
| Gitleaks and Trivy | Source secret scanning and HIGH/CRITICAL image gate. | Implemented and CI-validated | Gitleaks and Trivy steps passed in run 39468033513. This is scan evidence for that commit/image, not a security certification. |
| Kubernetes manifests | Deployment, Service, probes, resources, security context, ServiceAccount, HPA, Ingress, and policy examples. | Prepared; offline validated | Static YAML tests cover relationships and security fields. No API-server acceptance, scheduling, container startup, or cluster behavior was tested. |
| Helm chart | Schema and templates validate immutable image input and deployment settings. | Prepared; offline validated | Chart tests and local lint/template checks are available. No Helm release has been installed. HPA requires a working Metrics API. |
| NetworkPolicy | Standalone policy denies ingress; Helm policy is disabled by default and requires explicit selectors. | Blocked | Actual ingress/monitoring identities and CNI enforcement are unverified. Keep SEC-002 OPEN and do not enable/apply policy yet. |
| Resource sizing and autoscaling | Kubernetes requests/limits and CPU HPA settings are declared and statically checked. | Prepared only | No cluster scheduling, Metrics API, scaling behavior, or capacity test has been performed. |
| Prometheus, Grafana, and Loki | Application metrics/log events and service configuration are present. | Prepared only | No monitoring scrape, dashboard provisioning, persistence, or log collection is running. |
| Terraform/AWS | Network, IAM, and EC2 examples are present. | Prepared only | No Terraform initialization/plan/apply or AWS resource creation was performed; examples may incur charges. |
| K3s and Calico | Offline checks and bootstrap configuration exist. K3s script refuses installation; Calico installation is NO-GO. | Blocked | Provenance, approved artifacts/images, host prerequisites, CNI readiness, cluster identity, recovery, and SEC-002 remain unresolved. |
| GHCR publication | Workflow handoff steps and publication job are guarded off. | Disabled | No image was published. A separately approved process, repository protections, provenance/SBOM/signature decisions, and digest verification remain future work. |
| Cloud resource management API | Application endpoints report service metadata/status; they do not manage cloud resources. | Not implemented | This project demonstrates delivery/security practices, not a cloud control plane. |

## Verified CI record

GitHub Actions [run 39468033513](https://github.com/avinashmnth2507-dev/cloudops-platform/actions/runs/39468033513) was triggered by a push to `main` for commit `8e711c8a5338b68fde1bff1ba928088d424c41e9`. The `test` job passed dependency installation, Ruff, pytest (178 passed), and Gitleaks. The `image` job passed the Linux amd64 build and Trivy HIGH/CRITICAL gate. Image export, checksum, artifact upload, and the `publish` job were skipped. The workflow did not publish or deploy an image. This run does not cover the uncommitted documentation changes described in this checklist.

## Remaining deployment blockers

- Resolve SEC-002 by verifying actual ingress and metrics workload identities, adding only narrowly scoped policy rules, and testing enforcement with a verified CNI in an authorized disposable cluster.
- Resolve K3s/Calico artifact provenance, host compatibility, CNI installation/readiness, cluster identity, and recovery before considering deployment.
- Select or separately publish and verify an approved immutable image digest; keep GHCR publication disabled until separately authorized.
- Validate Kubernetes API acceptance, scheduling, health, HPA/Metrics API, storage, monitoring discovery/scraping, and capacity in an authorized environment.
- Review Terraform cost, network exposure, and failure cleanup before any separately approved AWS operation.

## Evidence links

- [Portfolio evidence index](portfolio-evidence.md)
- [Local verification report](local-verification-report.md)
- [Architecture and implementation status](architecture.md)
- [Kubernetes prerequisites](kubernetes.md)
- [Helm offline validation](helm.md)
- [Security controls and limits](security.md)
