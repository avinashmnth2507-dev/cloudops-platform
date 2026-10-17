# Portfolio Evidence Plan

Use genuine evidence tied to a recorded commit and date. A screenshot can show one moment; pair it with source, test, or job references where available. Do not fabricate results or present configuration as deployed infrastructure.

| Evidence area | Evidence to collect | What it can establish | Limits |
|---|---|---|---|
| Application API | A successful `scripts/demo-local.sh` summary while a person has manually started the app; optionally capture each endpoint in the browser. | The six local endpoints responded with the expected status and formats at capture time. | Does not identify an image or prove a deployment. Do not include response bodies containing environment data. |
| Metrics endpoint | The demo's `/metrics` pass plus a redacted view of the required metric families. | The app exposed parseable request-counter and latency-histogram samples locally. | Does not prove Prometheus discovery, scraping, persistence, or dashboards. |
| CI test job | GitHub Actions page for the exact commit, showing Ruff, pytest, and Gitleaks job results. Record the run URL and SHA in the evidence notes. | CI checked that workflow's source revision. | Run #17's association is owner-reported here and has not been independently checked. Run #5 is historical for an older commit. |
| CI image build and scan | The exact commit's image-job summary for build and strict Trivy scan, with the scanned commit/SHA visible. | The image was built in the CI runner and scanned under that workflow. | Does not mean the image was published. GHCR publishing remains disabled. |
| Compose security | Source excerpts from `docker-compose.yml`, `Dockerfile`, `.dockerignore`, and passing `tests/test_compose_config.py` / `tests/test_container_security.py`. | The configured Compose and image safeguards were statically inspected by tests. | Does not prove that a current container is running or has those settings at runtime. The existing `04-cloudops-docker.png` is historical unless its date and image are checked. |
| Helm | Output from local `helm lint` and `helm template`, with chart revision recorded. | Local chart syntax, schema validation, and rendered defaults. | Does not prove API-server acceptance, cluster compatibility, or runtime policy enforcement. |
| Terraform | Output from `terraform fmt -check -recursive terraform`. | Formatting of the checked-out Terraform files. | Does not validate a plan or prove resources exist. No AWS resources have been provisioned by this workflow. |
| Architecture | The current architecture diagram and completion checklist, with all configured/blocked states labeled. | The intended architecture and implementation boundaries. | A diagram is not deployment evidence. |

## Existing local screenshot references

The following image files were found by filename in the external local folder `~/Desktop/cloudops platform pics/`. They are not tracked in this repository and were not opened, copied, or modified during this task. Confirm their contents and provenance before using them to support claims about a particular commit:

- `01-cloudops-architecture.png`
- `02-cloudops-fastapi-api.png`
- `03-cloudops-github-actions.png`
- `04-cloudops-docker.png`
- `05-cloudops-tests.png`
- `06-cloudops-observability.png`

The first five are the screenshot set previously referenced for preservation; the observability image is an additional local asset. All remain external and unchanged. The repository's [`screenshots.md`](screenshots.md) remains the guidance for adding only genuine, reviewed evidence to the project.

## Evidence handling

- Record the exact commit SHA for source, CI, and test evidence.
- Redact tokens, cookies, private addresses where appropriate, and any sensitive log fields.
- Do not capture or publish local `.env` files, credentials, kubeconfig, Terraform state, or unredacted environment dumps.
- Keep historical screenshots labeled as historical unless verified against the current implementation.
- Do not create screenshots for an AWS, Kubernetes, Helm, monitoring, or Calico deployment that did not occur.
