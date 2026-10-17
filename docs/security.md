# Security Controls and Limits

CloudOps Platform is a portfolio project, not a production deployment. The repository contains layered source, CI, container, Kubernetes, and bootstrap safeguards, but the Kubernetes and cloud controls have not been exercised in a deployed environment. **SEC-002 remains OPEN.**

## Source and CI

- The `test` job runs Ruff, pytest, and Gitleaks. The workflow uses pinned action commit references and grants read-only repository permissions to the test and image jobs.
- On a `main` push, the `image` job builds the production image in the CI runner and runs Trivy with HIGH and CRITICAL findings configured to fail the job.
- GitHub Actions run [39019245360](https://github.com/avinashmnth2507-dev/cloudops-platform/actions/runs/39019245360) passed for commit `068f3c8c67e754a19a092c79764a7b24fa40c0c1`. The test and image jobs succeeded; the image export and `publish` job were skipped.
- GHCR publishing is intentionally disabled. A successful image job does not mean an image was published.
- The repository includes configuration templates, not credentials. Keep real tokens, passwords, private keys, kubeconfig files, and Terraform state out of source control.

## Container configuration

The production `Dockerfile` uses a digest-pinned Alpine Python base and runs as UID/GID `10001:10001`. `docker-compose.yml` configures a read-only root filesystem, a `/tmp` tmpfs, and `no-new-privileges:true`. The image defines an HTTP healthcheck.

There are two material limits in the current Compose setup:

- It does not set `cap_drop`, so Docker reports no capabilities as dropped.
- The `8000:8000` port mapping has no host-IP restriction and binds the published port on all host interfaces.

The read-only inspection recorded in the [local verification report](local-verification-report.md) found the existing app container stopped. Its stored configuration had a non-root user, read-only root, and no-new-privileges, but no dropped capabilities. Its previous `healthy` health value is stale because the container is exited. The report explains why the container was not started. These observations do not establish a running or current application image.

## Kubernetes and NetworkPolicy

Kubernetes manifests and Helm templates statically configure a non-root identity, disabled privilege escalation, dropped capabilities, seccomp, resources, and probes. Offline tests check these settings; they have not been runtime-verified on a cluster.

The standalone `k8s/networkpolicy.yaml` selects the application pods and denies all ingress without allow rules. Helm NetworkPolicy is disabled by default and has fail-closed selector requirements when enabled. Actual ingress-controller and metrics-scraper identities and CNI enforcement are unresolved. Do not enable or apply a policy until those identities and intended traffic are reviewed and tested. This unresolved deployment path is **SEC-002**.

## K3s and Calico bootstrap

The bootstrap scripts validate offline inputs and require separately approved integrity values, but the K3s script explicitly refuses installation and the Calico path remains NO-GO pending provenance, image integrity, host prerequisites, cluster identity, CNI readiness, and recovery evidence. No K3s or Calico installation was performed. Do not bypass the refusal or treat static checks as deployment approval.

## Verification boundaries

Run `scripts/verify-local.sh` for offline Ruff, pytest, shell syntax, Helm lint/render, and Terraform formatting checks using existing tools. Passing these checks does not establish container hardening at runtime, NetworkPolicy enforcement, artifact authenticity, or production readiness. See the [local verification report](local-verification-report.md) for the recorded container and CI observations.
