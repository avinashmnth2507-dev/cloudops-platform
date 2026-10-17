# Troubleshooting

This runbook separates checks against an application started manually from offline repository checks. It does not authorize container, cloud, Terraform, or cluster operations. Sanitize logs before sharing them; never include environment dumps, credentials, request bodies, or secret-bearing URLs.

## Local application unavailable

The demonstration script checks only numeric loopback URLs and does not start the application. If the local server is not reachable, start it manually only when desired and when the existing Python environment is available. Review the server terminal for startup errors. On macOS, the following read-only command can identify a listener on port 8000:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

Do not terminate an unfamiliar process to free the port. Confirm which process owns it first. See [local demo instructions](local-demo.md).

## Liveness or readiness check fails

The demo checks `/health` (liveness) and `/ready` (readiness) separately and expects HTTP 200 with JSON from both. These endpoints currently report application-process health and readiness; they do not check external services. A failure can indicate that the server is stopped, the port or URL is wrong, or the response contract changed. The demo reports status and content type without printing response bodies.

## Metrics are missing or malformed

The demo expects a plain-text Prometheus exposition containing the request counter and latency histogram bucket series. Check the `/metrics` response using `scripts/demo-local.sh`; do not paste full metrics output into public issue reports because labels may include operational metadata. If the endpoint responds but validation fails, run the existing local API tests and inspect `app/metrics.py` and the `/metrics` implementation.

## Ruff or pytest fails

Use the existing environment only:

```bash
.venv/bin/ruff check .
.venv/bin/pytest -q
```

`scripts/verify-local.sh` runs these checks together with shell syntax, optional Helm lint/render, and optional Terraform formatting. If a command is unavailable, do not install packages as a workaround for a review failure; record the skipped check.

For a GitHub Actions failure, review the failing job and step for the exact commit. Run `39019245360` passed for `068f3c8c67e754a19a092c79764a7b24fa40c0c1`; run #5 is historical for an earlier commit. CI success does not imply image publishing or deployment. The publish job remains disabled.

## Docker build or Trivy scan failure

The current CI workflow builds the production image in its runner and then fails on HIGH or CRITICAL Trivy findings. Review the workflow log, production `Dockerfile`, dependency manifests, and finding details. Do not remove or soften the Trivy gate to obtain a pass. GHCR publishing remains disabled; a successful image scan does not publish an image. This runbook does not ask you to run Docker.

## Image pull error

The workflow's GHCR publish job is disabled, so it has not published an image. Manifest owner and tag values are placeholders. Do not treat an image reference as evidence that the image exists. For an image selected through a separately approved process, verify its immutable reference and registry access before diagnosing pull behavior.

## Pod not starting

For an already-existing, separately authorized cluster, use read-only inspection and redact output before sharing it:

```bash
kubectl describe pod -n cloudops <pod-name>
kubectl logs -n cloudops <pod-name> --tail=100
```

Do not include environment variables or unfiltered logs in a report. These diagnostics do not authorize a deployment or change the current K3s/Calico installation refusal.

## Helm lint or rendering failure

Helm checks are local and do not contact a Kubernetes cluster:

```bash
helm lint helm/cloudops
helm template cloudops helm/cloudops
```

Review the failing template and `helm/cloudops/values.yaml` / `values.schema.json`. The NetworkPolicy must remain disabled by default and must fail closed when required selectors are missing. Successful rendering is static evidence only.

## NetworkPolicy blocks traffic

The standalone `k8s/networkpolicy.yaml` selects the CloudOps pods and denies all ingress; it has no allow rules. The Helm policy is disabled by default. Do not guess ingress-controller or Prometheus selectors and do not enable or apply a policy based on local rendering. SEC-002 remains open and CNI enforcement has not been runtime-verified.

Only for an already existing cluster with separate authorization, safe read-only inspection can begin with:

```bash
kubectl get pods -n cloudops
kubectl describe pod -n cloudops <pod-name>
kubectl get networkpolicy -n cloudops
```

Confirm the target context before any cluster access. These commands do not prove policy enforcement. Do not use `kubectl exec` as a substitute for a controlled connectivity test.

## K3s or Calico installation is blocked

The K3s bootstrap script explicitly refuses installation. The Calico script has a guarded `--apply` mode after its local input checks, but Calico installation remains NO-GO and is not authorized for this project state; do not run `--apply` or attempt a fallback CNI. The remaining blockers include separately approved artifact checksums, immutable image references, host prerequisites, cluster identity, runtime CNI readiness, recovery planning, and SEC-002. See [Calico installation status](calico-installation.md). No cloud or cluster resources are established by this repository documentation.

## Terraform formatting or deployment questions

The repository has Terraform formatting checks, but no infrastructure was provisioned as part of this project workflow. A formatting check is local and does not initialize providers:

```bash
terraform fmt -check -recursive terraform
```

Terraform `plan` or `apply` can inspect or create billable resources and is outside this runbook. An EC2 user-data failure does not automatically terminate or remove the instance. Review [deployment prerequisites](deployment.md) and cost guidance before any separately authorized infrastructure work.
