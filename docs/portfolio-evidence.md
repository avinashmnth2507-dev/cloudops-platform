# Portfolio Evidence Index

Evidence must be genuine, tied to the relevant source commit where possible, and labeled with its limitations. Do not present static configuration as a deployment or a historical screenshot as proof of the current revision.

## Current verified records

| Evidence | Date | Relevant commit | Validation method | What it demonstrates | Limitations |
|---|---|---|---|---|---|
| [GitHub Actions run 39019245360](https://github.com/avinashmnth2507-dev/cloudops-platform/actions/runs/39019245360) | 2026-10-17 08:56 UTC | `068f3c8c67e754a19a092c79764a7b24fa40c0c1` | Read-only authenticated `gh run list` and `gh run view` lookup | Test and image jobs succeeded; build and Trivy steps passed. | Export/checksum/upload steps and GHCR `publish` job were skipped. This is not a result for a later docs commit. |
| [Local verification report](local-verification-report.md) | 2026-10-17 | Repository HEAD `068f3c8c67e754a19a092c79764a7b24fa40c0c1` | Read-only Docker inspection, bounded loopback availability GET, offline tests and static checks | Records the stopped container, runtime configuration, CI record, and unavailable app endpoint. | The application was not started; no live API or metrics evidence was collected. |
| Local offline validation | 2026-10-17 | Repository HEAD `068f3c8c67e754a19a092c79764a7b24fa40c0c1` | `scripts/verify-local.sh`, Ruff, full pytest, shell syntax, Helm lint/render, Terraform formatting | 139 tests passed; local static and chart checks passed. | Local validation does not prove a currently running container or deployed cloud/cluster component. |

## Existing local screenshots

The six images below reside in an external local portfolio folder and are not tracked in Git. The first five are the protected screenshot set; the observability-named sixth image is an additional local asset. They were visually inspected but not edited, renamed, copied, or staged. Listed dates are filesystem modification times, **not independently verified capture dates**.

| Filename | Visible content | File mtime (local +0530) | Relevant commit shown | Inspection and limitations |
|---|---|---|---|---|
| `01-cloudops-architecture.png` | Diagram separating local implementation, prepared configuration, and planned runtime. It includes an older “Five local tests” label. | 2026-10-12 11:08 | Not visible | Visual inspection only. The diagram is architecture intent, not deployment evidence; its test-count label is stale. |
| `02-cloudops-fastapi-api.png` | FastAPI/Swagger operation list for the six routes. | 2026-10-12 11:12 | Not visible | Visual inspection only. It shows endpoint documentation, not successful responses or runtime health. |
| `03-cloudops-github-actions.png` | GitHub Actions Run #4 screen showing success for the test and image jobs, publish skipped, and commit prefix `195b35b`. | 2026-10-12 12:10 | `195b35b46208bac2e99d00ed63af35b6030be5a5` | Visual screenshot review; abbreviated SHA resolved against local Git history. Historical CI evidence, not the current run. |
| `04-cloudops-docker.png` | Docker Desktop local image inventory, including multiple tags. | 2026-10-12 12:19 | Not visible | Visual inspection only. It does not prove which source revision an image contains or that a service is currently running. |
| `05-cloudops-tests.png` | Terminal output showing five tests passing under Python 3.14.8. | 2026-10-12 12:21 | Not visible | Visual inspection only. This is a historical, stale test count. The image shows a local username and project path; redact or replace it before public use. |
| `06-cloudops-observability.png` | Despite its filename, this is a GitHub Actions Run #5 screen for commit prefix `f6ba78b`; test and image jobs passed and publish was skipped. It does not show metrics or dashboards. | 2026-10-16 14:29 | `f6ba78bcdda1a843e9cb33742826b46e98976f00` | Visual screenshot review. Historical CI evidence only; it is not observability runtime evidence. |

No new screenshot was captured in this batch. The local app was unavailable, and the existing stopped container was not started because its port mapping is all-interface and capability drops are absent. Do not upload the existing images unchanged as current-run evidence; confirm dates and remove local identifiers first.

## Evidence to collect later

| Evidence area | Method | What it can establish | Limits |
|---|---|---|---|
| Application API | Run `scripts/demo-local.sh` only after an already reviewed local start path is available. | Six local endpoints returned expected statuses and formats at that time. | Does not prove the image's source revision or deployment. |
| Metrics | Record the demo's `/metrics` pass and a minimal redacted metric-family summary. | App returned parseable counter and histogram exposition locally. | Does not prove Prometheus scraping, persistence, or dashboard operation. |
| Container runtime | Read-only inspect a running container after secure loopback binding and capability settings are reviewed. | Runtime identity, filesystem, privilege, ports, health, and resource values. | Static configuration or a stopped container is not runtime behavior. |
| CI | Link the run for the exact commit and record job conclusions. | CI tested that source revision. | A workflow pass does not publish or deploy. GHCR remains disabled. |
| Helm and Terraform | Local `helm lint`, `helm template`, and `terraform fmt -check` output. | Static chart rendering and Terraform formatting. | No cluster acceptance or AWS infrastructure is established. |
| Architecture | Current architecture diagram and checklist. | Intended design and status distinctions. | A diagram is not deployment evidence. |

Never publish `.env` files, credentials, kubeconfig, Terraform state, unredacted logs, or screenshots containing local account identifiers. Do not create screenshots for deployments that did not occur.
