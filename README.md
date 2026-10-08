# CloudOps Platform

> Production-style DevOps platform demonstrating the software delivery lifecycle from source code to cloud infrastructure, Kubernetes, observability and DevSecOps.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-green)
![Docker](https://img.shields.io/badge/Docker-container-blue)
![Kubernetes](https://img.shields.io/badge/Kubernetes-k3s-326ce5)
![Terraform](https://img.shields.io/badge/Terraform-IaC-7b42bc)
![Prometheus](https://img.shields.io/badge/Prometheus-monitoring-e6522c)
![Grafana](https://img.shields.io/badge/Grafana-observability-orange)

## Project Description

CloudOps Platform is a portfolio-grade DevOps project built around a small FastAPI service. The application is intentionally simple so that the engineering focus stays on containerization, CI, infrastructure as code, Kubernetes, Helm, monitoring, logging, security and reproducible operations.

The target workflow is:

```text
Repository
   -> Docker
   -> GitHub Actions
   -> GHCR
   -> Terraform
   -> AWS EC2
   -> k3s
   -> Kubernetes
   -> Helm
   -> Prometheus + Grafana
   -> Loki
   -> DevSecOps
```

## Modules

1. Repository + application
2. Docker
3. GitHub Actions CI
4. Terraform + AWS
5. Kubernetes
6. Helm
7. Prometheus + Grafana
8. Loki logging
9. DevSecOps
10. Documentation, tests and cleanup

## Application

| Endpoint | Purpose |
|---|---|
| `/` | Application metadata |
| `/health` | Liveness check |
| `/ready` | Readiness check |
| `/api/v1/status` | Service status |
| `/api/v1/info` | Runtime information |
| `/metrics` | Prometheus metrics |

## Local Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
ruff check .
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` for the FastAPI API documentation.

## Docker

```bash
docker build -t cloudops-platform:local .
docker run --rm -p 8000:8000 cloudops-platform:local
```

or:

```bash
docker compose up --build
```

## CI/CD

GitHub Actions runs:

- linting
- unit tests
- Gitleaks
- On pushes to `main`, after the test job succeeds, the CI runner builds the image locally.
- Trivy scans that local image.
- The workflow does not log in to a registry or publish the image.

For a public GitHub repository, standard GitHub-hosted runner usage is generally available without the private-repository Actions minute model.

## AWS Architecture

The low-cost lab uses one EC2 instance running k3s instead of EKS.

```text
AWS VPC
 |
 +-- Public Subnet
       |
       +-- EC2
             |
             +-- k3s
                  |
                  +-- CloudOps
                  +-- Prometheus
                  +-- Grafana
                  +-- Loki
```

Terraform is under `terraform/environments/dev`.

Before applying Terraform, copy `terraform.tfvars.example` to `terraform.tfvars` and set your public IP as `/32`.

## Kubernetes

Raw manifests are under `k8s/`.

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
```

Replace `YOUR_GITHUB_OWNER` in the deployment image before applying.

**NetworkPolicy warning:** `k8s/networkpolicy.yaml` selects the CloudOps pods in namespace `cloudops` and denies all ingress to them. Applying it blocks the Traefik application route and Prometheus `/metrics` scraping on TCP `8000` until narrowly scoped allow rules are added for verified workload identities. The repository does not establish the actual Traefik or Prometheus namespace and pod labels, or prove that the installed CNI enforces NetworkPolicy. Keep the Helm NetworkPolicy disabled until those details and required traffic paths are verified. Local Helm linting and rendering do not prove runtime enforcement or Prometheus discovery.

## Helm

```bash
helm lint helm/cloudops
helm upgrade --install cloudops helm/cloudops --namespace cloudops --create-namespace
```

## Monitoring

Install kube-prometheus-stack:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  -f monitoring/prometheus-values.yaml
```

The application exposes Prometheus-compatible metrics at `/metrics`.

## Logging

The logging directory contains a low-cost Loki configuration and deployment notes. Chart values should always be checked against the exact Loki chart version selected at deployment time.

## Security

The project demonstrates:

- Gitleaks
- Trivy
- non-root Docker image
- read-only Kubernetes root filesystem
- dropped Linux capabilities
- seccomp RuntimeDefault
- disabled privilege escalation
- resource limits
- RBAC
- NetworkPolicy
- restricted AWS SSH/API ingress
- no credentials committed to Git

## Repository Structure

```text
app/                  FastAPI application
 tests/               automated tests
.github/workflows/    CI automation
terraform/            AWS infrastructure
k8s/                  Kubernetes manifests
helm/                 Helm chart
monitoring/           Prometheus/Grafana configuration
logging/              Loki documentation/configuration
security/             security controls
scripts/              operational scripts
docs/                 engineering documentation
screenshots/          real portfolio evidence
```

## Credentials

Never commit AWS keys, GitHub tokens, passwords, private keys, kubeconfig files or real `.env` files.

Authenticate the local CLI instead:

```bash
aws sts get-caller-identity
gh auth status
```

Codex can use the authenticated CLI environment without receiving the credentials themselves.

## Cost Control

This project deliberately avoids EKS, NAT Gateway, RDS and unnecessary managed services. Use a small EC2 lab and destroy it after practice:

```bash
cd terraform/environments/dev
terraform destroy
```

Review the current AWS Free Tier / account billing terms before deployment.

## Portfolio Evidence

Capture real screenshots during implementation and store them in `screenshots/`. Never fabricate evidence.

Recommended screenshots:

1. application
2. Docker container
3. GitHub Actions
4. Terraform
5. AWS EC2
6. Kubernetes
7. Helm
8. Prometheus
9. Grafana
10. Loki logs
11. Trivy
12. Gitleaks

## License

MIT
