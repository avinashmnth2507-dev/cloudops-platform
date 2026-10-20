# Security Controls and Limits

CloudOps Platform is a portfolio project, not a production deployment. The repository contains layered source, CI, container, Kubernetes, and bootstrap safeguards, but the Kubernetes and cloud controls have not been exercised in a deployed environment. **SEC-002 remains OPEN.**

## Source and CI

- The `test` job installs the platform-specific development lock with `pip --require-hashes`, then runs Ruff, pytest, and Gitleaks. The workflow actions are pinned to commit SHAs; the test and image jobs have `contents: read` permissions.
- On a push to `main`, the dependent `image` job builds the production image for Linux amd64 and runs Trivy with HIGH and CRITICAL findings configured to fail the job.
- GitHub Actions [run 39468033513](https://github.com/avinashmnth2507-dev/cloudops-platform/actions/runs/39468033513) passed for commit `8e711c8a5338b68fde1bff1ba928088d424c41e9`: dependency install, Ruff, 178 pytest tests, Gitleaks, image build, and Trivy gate succeeded. The image handoff steps and `publish` job were skipped. The image was not published. This run predates the current documentation edits.
- GHCR publishing is intentionally disabled. A successful image job does not mean an image was published.
- The [manual GHCR publication design](ghcr-publication-design.md) is a proposal only; the active workflow has no `workflow_dispatch` trigger and still cannot publish.
- The repository includes configuration templates, not credentials. Keep real tokens, passwords, private keys, kubeconfig files, and Terraform state out of source control.

The runtime and development locks include exact versions and approved SHA-256 artifact hashes. Hash verification protects downloaded artifact contents against those values; it does not establish publisher identity or package trustworthiness.

## Container configuration

The production `Dockerfile` uses a digest-pinned Alpine Python base, hash-verified binary-only runtime dependencies, and UID/GID `10001:10001`. It defines an HTTP healthcheck. `docker-compose.yml` publishes only on `127.0.0.1:8000`, drops all Linux capabilities, uses a read-only root filesystem and `/tmp` tmpfs, and enables `no-new-privileges:true`.

The [DEV-015 local verification report](local-verification-report.md) records a local build and running healthy app with these Compose controls, no unexpected mounts, and six successful endpoint checks. That evidence applies to a disclosed dirty local worktree at the time of the run; it does not establish a currently running container or a cloud/cluster deployment. Earlier stopped-container observations in this report are historical and predate the DEV-011 hardening changes.

## Kubernetes and NetworkPolicy

Kubernetes manifests and Helm templates statically configure a non-root identity, disabled privilege escalation, dropped capabilities, seccomp, resources, and probes. Offline tests check these settings; they have not been runtime-verified on a cluster.

The standalone `k8s/networkpolicy.yaml` selects the application pods and denies all ingress without allow rules. Helm NetworkPolicy is disabled by default and has fail-closed selector requirements when enabled. Actual ingress-controller and metrics-scraper identities and CNI enforcement are unresolved. Do not enable or apply a policy until those identities and intended traffic are reviewed and tested. This unresolved deployment path is **SEC-002**.

## K3s and Calico bootstrap

The bootstrap scripts validate offline inputs and require separately approved integrity values, but the K3s script explicitly refuses installation and the Calico path remains NO-GO pending provenance, image integrity, host prerequisites, cluster identity, CNI readiness, and recovery evidence. No K3s or Calico installation was performed. Do not bypass the refusal or treat static checks as deployment approval.

## Verification boundaries

Run `scripts/verify-local.sh` for offline Ruff, pytest, shell syntax, Helm lint/render, and Terraform formatting checks using existing tools. Passing these checks does not establish container hardening at runtime, NetworkPolicy enforcement, artifact authenticity, or production readiness. See the [local verification report](local-verification-report.md) for the recorded container and CI observations.
