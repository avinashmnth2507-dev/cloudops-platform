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

## DEV-011 Compose security update and runtime decision

On 2026-10-17, the Compose `app` service configuration was changed to publish `127.0.0.1:8000:8000` and drop all Linux capabilities. The existing non-root image user, read-only root filesystem, `/tmp` tmpfs, `no-new-privileges`, image healthcheck, and production Dockerfile were preserved. The service has no `depends_on` or declared volumes; Compose does not configure CPU or memory limits. Static `docker compose config --quiet` passed, and rendered configuration showed host IP `127.0.0.1`, target port `8000`, and `cap_drop: ALL`. The expanded offline Compose test file reports seven passing focused tests; the full suite reports 140 passing tests. `scripts/verify-local.sh`, explicit Ruff and pytest runs, shell syntax checks, Helm lint/default rendering, Terraform formatting, and `git diff --check` passed. These checks confirm configuration assertions only, not runtime behavior.

Read-only inspection matched the existing stopped container's Compose labels to project `cloudops-platform-full` and service `app`. Its ID remains `02e39edf41adfc053f59175127dd86dbfae85a43a00c24fe5f867254c546cc90`; its state is exited with code `255`. It references local image ID `sha256:f7249e1444419527af0c1515e9261ef5178a6c9b5488997b41d8287c7940224d`, tagged `cloudops-platform-full-app:latest`, created `2026-10-16T10:22:55Z`. The image metadata reports Linux amd64, user `10001:10001`, and the expected Uvicorn command and `/health` image healthcheck.

The image has no repository digest and no OCI source-revision label. Its available metadata therefore does not establish which source revision produced it. A label-filtered `docker ps` listing and `docker history` did not return within the bounded inspection window and were interrupted; no build history was established. The old container's stored settings still have wildcard host port binding and no dropped capabilities, so it was not started. **No container recreation was performed:** image provenance/suitability and a reliable container listing were insufficiently established for the requested demonstration. No image was built or pulled, and no container, network, volume, or image was mutated.

Because the app remained stopped, `/health`, `/ready`, `/api/v1/status`, `/api/v1/info`, and `/metrics` were not requested, `scripts/demo-local.sh` was not run, and no live endpoint, metrics, or healthy-runtime result is claimed. The prior loopback availability probe to `/` remained refused. The Compose security corrections are statically validated but not runtime-verified.

## DEV-012 build eligibility and runtime decision

On 2026-10-17, the repository was still on `main` at `e81c86b41c2354ea0e58e51bf3a8e3335b73afc5`. The three uncommitted DEV-011 changes remained limited to `docker-compose.yml`, `tests/test_compose_config.py`, and this report; the three candidate Dockerfiles remained untracked. No files were staged.

The Docker Engine responded to a read-only `docker info` query and reported Linux `x86_64`, four CPUs, and 5,172,776,960 bytes of memory. The production Dockerfile requests Linux amd64 and pins `python:3.13.16-alpine3.24` by digest. A read-only inspection of that exact pinned base image did not return within ten seconds and was interrupted. Its local availability is therefore **unverified**. The existing app image is not evidence that this specific base image is cached.

The Dockerfile runs `pip install --only-binary=:all: --no-cache-dir -r requirements-runtime.txt` for the pinned FastAPI, Starlette, Uvicorn, Prometheus, and Pydantic Settings dependencies. The repository provides no wheelhouse or other offline package inputs. With `--network=none`, a cache miss at that install step would fail; the relevant local base-image and build-cache state could not be verified safely because Docker inspection was unreliable. No build was attempted, and no DEV-012 image tag, image ID, OCI revision label, or build provenance was created. The source tree was dirty, so even a build labeled with HEAD would also have needed to identify the included uncommitted DEV-011 changes.

Because the required offline build inputs were not established, the conditional build authorization was not exercised. The stopped `app` container was not recreated, and no local endpoint or live metrics check was run. The prior container and image remain unchanged; the corrected loopback binding and capability drop have only been verified in the rendered Compose configuration and automated tests. No Docker image was pulled, built, or pushed, and no container, network, volume, or image was changed. The local verification script, Ruff, the full 140-test suite, Bash syntax checks, Compose static configuration, Helm lint/default rendering, Terraform formatting, and diff checks passed. **SEC-002 remains OPEN; K3s and Calico installation remain NO-GO; GHCR publishing remains disabled.**

## DEV-013 Docker diagnostics and stop decision

On 2026-10-17, repository preflight matched the expected `main` HEAD `e81c86b41c2354ea0e58e51bf3a8e3335b73afc5`. The only modified tracked files were `docker-compose.yml`, `tests/test_compose_config.py`, and this report; no files were staged. The three candidate Dockerfiles remained the only untracked repository files.

The Docker CLI could not access the daemon from the restricted shell. With the authorized elevated read-only query, `docker info --format 'Server={{.ServerVersion}} CPUs={{.NCPU}} MemoryBytes={{.MemTotal}} OSType={{.OSType}} Architecture={{.Architecture}} Root={{.DockerRootDir}}'` returned Engine `24.0.6`, Linux `x86_64`, four CPUs, 5,172,776,960 bytes of memory, and root `/var/lib/docker`. However, the bounded project/service-filtered command `docker ps -a --filter label=com.docker.compose.project=cloudops-platform-full --filter label=com.docker.compose.service=app --no-trunc --format '{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}'` produced no output within five seconds and was interrupted (exit `255`).

Because the container listing hung, DEV-013A's Docker responsiveness and container-identity prerequisite did not pass. Current container state, dependency relationships, mounts, disk availability, exact pinned base-image availability, and local application-image inventory were not independently confirmed in this batch. The prior inspection recorded the app container as stopped, but that is not a fresh DEV-013 confirmation. Docker diagnostics stopped at the failed listing; no further Docker commands were run.

DEV-013B was not started: no image was built, pulled, tagged, or pushed; no container was replaced; and no endpoint or metrics request was made. No Docker resource was intentionally changed. The DEV-011 loopback and `cap_drop: ALL` changes remain statically covered by the existing Compose tests and previous rendered-config validation, but they have not been applied to a running container. **DEV-013 live demonstration remains blocked pending a reliable Docker inspection session. SEC-002 remains OPEN; K3s/Calico remain NO-GO; GHCR publishing remains disabled.**

## DEV-015 secure build and live local verification

On 2026-10-18, preflight confirmed branch `main` at `e81c86b41c2354ea0e58e51bf3a8e3335b73afc5`. Before the build, the worktree had the existing uncommitted edits in `docker-compose.yml`, `tests/test_compose_config.py`, and this report, plus untracked `Dockerfile.distroless`, `Dockerfile.sec027`, and `Dockerfile.sec029c`. The source revision and dirty state were added as image labels; the file list recorded at build time is included in the image metadata. No files were staged. The pre-existing external screenshots were not edited, copied, or removed.

Docker Engine 24.0.6 responded to `docker info`, `docker ps -a`, `docker image ls`, the pinned-image inspection, and `docker system df`; no inspection command hung. It reported Linux `x86_64`, four CPUs, and 5,172,789,248 bytes of memory. The Docker image store initially did not contain `python:3.13.16-alpine3.24@sha256:ba27df8b6499cc3756cff167690f3fcb5321faa1703b3a914df5f4fdadb32f05`. The host data volume had 36 GiB available on a 113 GiB filesystem. Initial Docker usage reported 2.251 GB of images and 142.1 MB of build cache. The build used `--pull` for the exact pinned digest; the runtime dependency installation layer was already cached.

The production `Dockerfile` built successfully for Linux amd64 as `cloudops-platform:dev-015-20261018-e81c86b`. The resulting image ID is `sha256:58a5833b4ca8876b2f197ebd5fa7eec66fbc6ebed00ea26102d8c0cbbc02b0c5`. Inspection verified architecture `amd64`, image user `10001:10001`, command `uvicorn app.main:app --host 0.0.0.0 --port 8000`, and the existing `/health` image healthcheck. The image labels include the expected Git revision, `working-tree=dirty`, and the six pre-build uncommitted paths. No dependency upgrade or unrelated tool installation was performed, and no image was pushed.

Before recreation, the stopped container ID `02e39edf41adfc053f59175127dd86dbfae85a43a00c24fe5f867254c546cc90` was reconfirmed as Compose project `cloudops-platform-full`, service `app`, with an empty `depends_on` label, no mounts, no binds or `volumes_from`, and no other Compose service. The existing project network had no attached containers. The temporary Compose override selected the new local image; `docker compose config --quiet` passed, and its rendered configuration retained `127.0.0.1:8000:8000`, `cap_drop: ALL`, read-only root, `/tmp` tmpfs, and `no-new-privileges:true`. The `app` service was recreated with `--no-deps --no-build --pull never --force-recreate`; no dependency was started, and the existing `minikube` container remained stopped and unchanged.

The new app container ID is `1cb0488e277784cc697d7caf709352dc79a39bbdeceae5d8806b71794fa24a0d`. Runtime inspection reported `running` and `healthy`, image ID `sha256:58a5833b4ca8876b2f197ebd5fa7eec66fbc6ebed00ea26102d8c0cbbc02b0c5`, user `10001:10001`, read-only root filesystem, `CapDrop: ALL`, and `no-new-privileges:true`. The only published mapping is `127.0.0.1:8000` to container port 8000. There are no mounts; `/tmp` is configured as tmpfs. The configured healthcheck passed.

The first `scripts/demo-local.sh` invocation from the restricted shell could not access loopback. Rerunning that same loopback-only script with approved local access completed with six passes and zero failures:

| Endpoint | Result |
|---|---|
| `/` | HTTP 200, `application/json` |
| `/health` | HTTP 200, `application/json` |
| `/ready` | HTTP 200, `application/json` |
| `/api/v1/status` | HTTP 200, `application/json` |
| `/api/v1/info` | HTTP 200, `application/json` |
| `/metrics` | HTTP 200, Prometheus text exposition (`text/plain`) |

A parsed post-demo scrape confirmed `cloudops_http_requests_total` has incremented `GET`/`200` samples for all six routes. The observed values were 1 for `/`, `/ready`, `/api/v1/status`, `/api/v1/info`, and `/metrics`, and 4 for `/health` (including image healthcheck requests). The exposition also contained the request-duration histogram required by the demo helper. This verifies application metrics and request instrumentation only; no Prometheus server or Grafana dashboard was started or is claimed.

After the live demonstration, `scripts/verify-local.sh` passed Ruff, the full suite (**140 passed**, one Starlette/AnyIO deprecation warning), shell syntax checks, Helm lint and default rendering, and Terraform formatting without initialization. Helm reported only its informational chart-icon recommendation. No AWS, Kubernetes, Helm deployment, Terraform initialization or operation, K3s/Calico installation, GHCR publication, or other infrastructure action occurred. **SEC-002 remains OPEN; K3s/Calico remain NO-GO; GHCR publishing remains disabled.**
