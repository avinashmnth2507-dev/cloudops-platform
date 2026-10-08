# CloudOps Platform

> A DevOps portfolio project built around a small FastAPI service and supporting delivery, infrastructure, Kubernetes, and observability configuration.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-green)
![Docker](https://img.shields.io/badge/Docker-container-blue)
![Kubernetes](https://img.shields.io/badge/Kubernetes-k3s-326ce5)
![Terraform](https://img.shields.io/badge/Terraform-IaC-7b42bc)
![Prometheus](https://img.shields.io/badge/Prometheus-monitoring-e6522c)
![Grafana](https://img.shields.io/badge/Grafana-observability-orange)

## Current Implementation Status

> **This is a local portfolio project, not a production deployment. No AWS infrastructure or Kubernetes cluster has been deployed from this repository.**

| Status | Components |
|---|---|
| Implemented and locally tested | FastAPI root metadata, health, readiness, status, and metrics endpoints. The current suite has five tests covering these paths. |
| Implemented, test gap | `/api/v1/info` is implemented but does not yet have a dedicated test. |
| Prepared, not deployed | Docker and Compose configuration; GitHub Actions workflow; Terraform environment and development profiles; Kubernetes manifests; Helm chart; k3s and Calico configuration; Prometheus and Grafana values. |
| Planned or not verified | AWS and Kubernetes runtime behavior; Calico readiness and policy enforcement; HPA metrics behavior; Prometheus discovery and scraping; Grafana installation and dashboard provisioning; Loki log collection. |

AWS infrastructure has not been deployed. Kubernetes and Calico runtime behavior have not been verified. Prometheus and Grafana have not been installed. GHCR image publishing is disabled. **SEC-002 remains open:** the standalone NetworkPolicy denies application ingress, and the actual ingress-controller and Prometheus identities and CNI enforcement are not verified.

The latest local-only checks passed: five tests, Ruff, dependency consistency, Terraform formatting, and Helm lint. The local Python environment was 3.14 while CI is configured for 3.13. GitHub-hosted CI has not yet been executed. Helm lint reported only that a chart icon is recommended.

## Project Description

CloudOps Platform demonstrates a small application surrounded by DevOps tooling. The application is intentionally simple so the project can focus on containerization, CI, infrastructure as code, Kubernetes, Helm, monitoring, logging, and security practices. See the [architecture overview](docs/architecture.md) and [deployment status and prerequisites](docs/deployment.md).

The target deployment architecture is a proposal. The [architecture page](docs/architecture.md) distinguishes local implementation, prepared configuration, and components that remain planned.

## Project Components

The repository contains the application, Docker configuration, GitHub Actions workflow, Terraform modules, Kubernetes manifests, a Helm chart, Prometheus/Grafana configuration, Loki values, security examples, tests, and supporting documentation. These files represent a mix of locally tested code and deployment preparation; they do not mean the cloud or cluster components are running.

## Application

| Endpoint | Purpose |
|---|---|
| `/` | Application metadata |
| `/health` | Liveness check |
| `/ready` | Readiness check |
| `/api/v1/status` | Service status |
| `/api/v1/info` | Runtime information |
| `/metrics` | Prometheus metrics |

The current tests cover five endpoints; `/api/v1/info` is implemented but does not yet have a dedicated test.

## Local Development

From the repository root, create and activate a virtual environment, then install the pinned top-level dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
ruff check .
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` while the local development server is running to view FastAPI's API documentation.

## Docker

The repository includes a non-root runtime image and a Compose configuration. These commands are local examples; they have not been run as part of the current documentation review.

```bash
docker build -t cloudops-platform:local .
docker run --rm -p 8000:8000 cloudops-platform:local
```

Or use the Compose configuration:

```bash
docker compose up --build
```

## GitHub Actions

The workflow is configured but has not yet run on GitHub:

- Pull requests run dependency installation, Ruff, pytest, and Gitleaks.
- Pushes to `main` run those checks and then build the image in the CI runner and scan it with Trivy for HIGH and CRITICAL vulnerabilities.
- GHCR publication is explicitly disabled. The workflow does not currently log in to a registry or publish an image.
- The workflow has no AWS, Kubernetes, or infrastructure deployment job.

The most recent test run used local Python 3.14; the workflow selects Python 3.13. The first GitHub run will be the first verification of that CI environment. A previous local Trivy report found HIGH OS-package vulnerabilities; it is historical evidence, not a current scan, and the configured CI policy may fail if findings remain.

## Deployment Readiness

> **Do not run the infrastructure or cluster examples below yet.** The Terraform bootstrap disables Flannel and k3s's embedded NetworkPolicy controller, but this repository does not install Calico automatically. Calico's version and host/runtime compatibility still require verification. The application image reference is a placeholder, the ingress is HTTP-only, and SEC-002 remains open. Review the [deployment prerequisites](docs/deployment.md), [Calico preparation](docs/calico-installation.md), [Kubernetes security notes](docs/kubernetes.md), and [monitoring prerequisites](docs/monitoring.md) before any separately authorized deployment.

## AWS Infrastructure

Terraform configuration is under `terraform/environments/dev`. The examples use a public subnet and include public HTTP ingress. SSH and the Kubernetes API are restricted by the `ssh_cidr` input. These files describe infrastructure; no AWS resources have been created.

For a future, separately reviewed deployment, copy `terraform/environments/dev/terraform.tfvars.example` to a local `terraform.tfvars` and replace the SSH CIDR placeholder with an authorized address. Do not commit the local file. See [development profiles](docs/development-profiles.md) for estimates, not capacity guarantees.

## Kubernetes

Raw manifests are under `k8s/`; the application Helm chart is under `helm/cloudops`. The example image currently contains `YOUR_GITHUB_OWNER` and the mutable `latest` tag. It cannot be treated as a published deployable image. GHCR publishing remains disabled.

The following are **future reference examples only, not approved to execute now**. The default-deny standalone NetworkPolicy is intentionally omitted from the apply list because it blocks application ingress and Prometheus scraping until verified, narrowly scoped allow rules are designed. Do not apply it unchanged.

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
```

See the [Kubernetes security notes](docs/kubernetes.md) for the policy behavior and environment checks required before deployment.

## Helm

The chart defaults Ingress, ServiceMonitor, and NetworkPolicy to disabled; HPA is enabled and requires a working Metrics API. For a local, non-deploying chart check, run `helm lint helm/cloudops` from the repository root. Linting does not install the chart or verify cluster behavior. See the [Helm guide](docs/helm.md).

## Monitoring

Monitoring values are prepared but Prometheus and Grafana have not been installed. The local dashboard JSON is not evidence of automatic Grafana provisioning. Persistent Prometheus storage and deployment capacity are unresolved.

The command below is a **documentation-only example for a future, separately authorized deployment; do not execute it now**. It pins kube-prometheus-stack chart version `91.8.2` and retains the documented release, namespace, and values file:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --version 91.8.2 \
  --namespace monitoring --create-namespace \
  -f monitoring/prometheus-values.yaml
```

The Grafana admin Secret must be provisioned separately through an approved secret-management process. No credential value is stored in this repository. See [monitoring status and selectors](docs/monitoring.md) and the [resource budget](docs/monitoring-resource-budget.md).

## Logging

The `logging/` directory contains Loki values and documentation. A complete log-collection deployment has not been demonstrated; chart values must be reviewed against the exact Loki chart selected for any future installation.

## Security

The repository contains Gitleaks and Trivy CI configuration, a non-root Docker image, Kubernetes security contexts, resource settings, RBAC examples, and NetworkPolicy configuration. Their presence does not establish production operation or runtime enforcement. The [security documentation](docs/security.md) and [Kubernetes policy notes](docs/kubernetes.md) describe the current limits. SEC-002 remains open.

## Repository Structure

```text
app/                  FastAPI application
tests/                automated tests
.github/workflows/    CI configuration
terraform/            AWS infrastructure configuration and examples
k8s/                  Kubernetes and Calico configuration
helm/                 CloudOps Helm chart
monitoring/           Prometheus/Grafana configuration
logging/              Loki values and documentation
security/             security documentation
scripts/              operational scripts
docs/                 project documentation
```

## Credentials

Never commit AWS keys, GitHub tokens, passwords, private keys, kubeconfig files, Terraform state, or real `.env` files. Use local ignored files or an approved secret-management process. `.env.example` and `k8s/secret.example.yaml` are templates, not production credentials.

## Cost Control

The proposed lab avoids EKS, NAT Gateway, RDS, and other managed services. EC2, EBS, public IPv4, data transfer, and CPU-credit use can still incur charges. Review current account pricing and credits before a future deployment. Cleanup instructions are in [cost-control documentation](docs/cost-control.md); destroy commands must only be used for resources you intentionally created and intend to remove.

## Portfolio Evidence

Capture genuine screenshots after implementing and verifying components. No runtime screenshots are currently tracked. Never fabricate deployment evidence; see [portfolio evidence notes](docs/screenshots.md).

## License

The repository includes an MIT `LICENSE` file. Confirm you have the rights to publish all project content and any future screenshots or third-party assets.
