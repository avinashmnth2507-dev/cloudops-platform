# Local Verification Report

- **Verification date:** 2026-10-17
- **Repository HEAD at inspection:** `068f3c8c67e754a19a092c79764a7b24fa40c0c1`
- **Scope:** Read-only Docker inspection, one bounded loopback GET availability probe, offline repository validation, and authenticated read-only GitHub Actions lookup.

## GitHub Actions

GitHub Actions workflow run [39019245360](https://github.com/avinashmnth2507-dev/cloudops-platform/actions/runs/39019245360) completed successfully for the exact HEAD above on a `push` event at `2026-10-17T08:56:33Z`.

| Job | Result | Evidence |
|---|---|---|
| `test` (job ID `117357556081`) | Success | Ruff, pytest, and Gitleaks steps all succeeded. |
| `image` (job ID `117357618801`) | Success | CI image build and Trivy vulnerability scan succeeded. Export/checksum/upload steps were skipped. |
| `publish` (job ID `117357775563`) | Skipped | GHCR publication remains disabled. |

This verifies the workflow for commit `068f3c8c67e754a19a092c79764a7b24fa40c0c1`; it does not verify the later documentation commit or publish an image.

## Offline validation

The existing local verification script passed Ruff, the full pytest suite, shell syntax, Helm lint and default rendering, and Terraform formatting. The full suite reported **139 passed** with one Starlette/AnyIO deprecation warning. Independent Ruff, pytest, Bash syntax, and `git diff --check` reruns also passed. Helm emitted only its informational recommendation to add a chart icon. No dependencies were installed.

These checks validate source and configuration. They do not establish that the application was running or that cluster/cloud components were deployed.

## Compose and container inspection

The Compose file defines only the `app` service, with no `depends_on` services. It declares `build: .`, host port `8000:8000`, a read-only root filesystem, `/tmp` tmpfs, and `no-new-privileges:true`.

The Docker daemon was accessible. The existing container was:

| Property | Observed value |
|---|---|
| Name / ID | `cloudops-platform-full-app-1` / `02e39edf41adfc053f59175127dd86dbfae85a43a00c24fe5f867254c546cc90` |
| State | Exited, exit code `255`; started `2026-10-16T10:23:17Z`, finished `2026-10-17T05:23:34Z` |
| Stored health state | `healthy`, but stale because the container is stopped; it is not a current health result. |
| Image | `cloudops-platform-full-app:latest`, image ID `sha256:f7249e1444419527af0c1515e9261ef5178a6c9b5488997b41d8287c7940224d` |
| Image provenance | Local image was available; `RepoDigests` was empty and no OCI source revision label was present. It cannot be confidently tied to the inspected Git commit. |
| Container identity | `10001:10001`; privileged mode was false. |
| Filesystem and privileges | Read-only root and `no-new-privileges` were set; `/tmp` was tmpfs; no host bind mounts were configured. |
| Capabilities | `CapDrop` was unset, so no Linux capabilities were dropped. |
| Published port | Container port `8000/tcp` mapped to host port `8000` with no specific host IP, which means a wildcard/all-interface binding. |
| Resource limits | Memory and CPU limits were unset (`0`). |
| Healthcheck | Configured by the image for `/health`, but cannot establish health while stopped. |

The container was not started. Its saved port binding would expose the service beyond loopback, and its configuration lacks dropped capabilities. The local image also has no revision metadata proving which source commit it contains. Starting it would therefore not provide a safe, attributable local demonstration. No security settings were changed, and no image was built or pulled.

## Application endpoint results

The bounded, proxy-disabled GET availability probe to `http://127.0.0.1:8000/` was refused by the local port: HTTP `000`, zero response bytes, no content type, and no redirect.

| Endpoint | Result |
|---|---|
| `/` | Availability probe failed to connect; no HTTP response. |
| `/health` | Not requested; app unavailable. |
| `/ready` | Not requested; app unavailable. |
| `/api/v1/status` | Not requested; app unavailable. |
| `/api/v1/info` | Not requested; app unavailable. |
| `/metrics` | Not requested; live metrics not verified. |

`scripts/demo-local.sh` was not run because the application was unavailable and there was no safe existing container start path. No endpoint response or live Prometheus exposition is claimed. No application logs were read.

## Evidence and limitations

The external portfolio images were visually inspected but not edited, copied, or added to Git. Their contents and limitations are catalogued in the [portfolio evidence index](portfolio-evidence.md). No new application or container screenshot was captured because the service was not running.

No AWS, Terraform, Kubernetes, Helm, K3s, Calico, GHCR, or other infrastructure operation occurred. **SEC-002 remains OPEN. K3s and Calico installation remain NO-GO. GHCR publishing remains disabled.**
