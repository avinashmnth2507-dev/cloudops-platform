# Architecture and Implementation Status

CloudOps Platform is a portfolio project centered on a small FastAPI service. This page separates components implemented locally from configuration prepared for a future deployment. **No AWS infrastructure or Kubernetes cluster has been deployed from this repository.**

## Implemented locally

- FastAPI endpoints for application metadata, health, readiness, status, runtime information, and Prometheus metrics; structured JSON request events are written to stdout.
- The local pytest suite has 17 passing tests, including coverage for all six application endpoints, metrics, request logging, and instrumentation-failure handling.
- Dockerfile and Docker Compose configuration.
- GitHub Actions Run #5 passed on commit `f6ba78bcdda1a843e9cb33742826b46e98976f00`, including the test job and the main-branch image build and strict scan. The GHCR publish job exists but is disabled; no image was published.

The latest local Ruff and pytest checks passed (17 tests); local Python is 3.14 and the workflow uses Python 3.13. CI success verifies the workflow checks for that commit; it does not verify a currently running Compose container or deploy cloud or cluster infrastructure.

## Prepared configuration — not deployed

- Terraform describes a VPC, public subnet, security group, IAM role, and EC2 instance.
- k3s bootstrap settings and a Calico `Installation` custom resource are present.
- Kubernetes manifests and the CloudOps Helm chart describe the application, service, ingress, autoscaling, monitoring, and policy settings.
- Prometheus/Grafana values and a dashboard JSON are present. They do not establish an installed monitoring stack or automatic dashboard provisioning.
- Loki values and documentation are present; a complete log collection pipeline is not demonstrated.

## Planned deployment architecture

The diagram shows the intended flow, not a deployed system. Dashed edges indicate proposed or disabled steps.

```mermaid
flowchart TB
  subgraph local["Implemented locally"]
    app["FastAPI application and JSON request events"] --> tests["Local pytest regression suite"]
    repo["Git repository"] --> workflow["GitHub Actions<br/>Run #5 passed"]
    workflow --> validation["Pull request: Ruff, tests, Gitleaks"]
    workflow --> scan["Main push: build image and scan with Trivy"]
    scan --> localimage["Image in CI runner only"]
  end

  ghcr["GHCR image<br/>publishing disabled; no image published"]
  localimage -. "planned; disabled" .-> ghcr

  subgraph prepared["Prepared configuration — not applied"]
    terraform["Terraform configuration"]
    calico["Calico Installation configuration"]
    manifests["Kubernetes manifests and Helm chart"]
    monitoring["Prometheus and Grafana values"]
    loki["Loki values and documentation"]
  end

  subgraph future["Planned runtime — not verified"]
    aws["AWS VPC, subnet, and EC2"] --> k3s["k3s"]
    k3s --> cloudops["CloudOps application"]
    k3s --> prom["Prometheus and Grafana"]
    k3s --> lokiworkload["Loki and log collection"]
  end

  terraform -. "future deployment" .-> aws
  calico -. "separate install and readiness required" .-> k3s
  manifests -. "future deployment" .-> cloudops
  monitoring -. "future install" .-> prom
  loki -. "future integration" .-> lokiworkload
```

Run #5 passed for commit `f6ba78bcdda1a843e9cb33742826b46e98976f00`. On main pushes, the workflow builds and scans an image after tests succeed. A publish job is present but guarded by an always-false condition, so it does not log in to GHCR or publish the image. Kubernetes and Helm image references still contain placeholders and are not deployable as written.

## Deployment prerequisites and limits

- **AWS:** No infrastructure has been deployed. The Terraform configuration includes public HTTP ingress and may incur EC2, EBS, public IPv4, data-transfer, and CPU-credit charges.
- **k3s and Calico:** The bootstrap disables Flannel and k3s's embedded NetworkPolicy controller. A separately installed and healthy Calico CNI is required before relying on pod networking. Runtime compatibility and enforcement are unverified. See [Calico preparation](calico-installation.md) and [deployment prerequisites](deployment.md).
- **NetworkPolicy:** SEC-002 remains open. The standalone policy denies application ingress, while Helm NetworkPolicy is disabled by default. Do not enable or apply a policy until source workload identities and CNI enforcement have been verified. See [Kubernetes security notes](kubernetes.md).
- **Ingress:** The configured application Ingress is HTTP-only; TLS is deferred. Terraform permits public TCP 80. Review exposure before any future deployment.
- **Autoscaling:** HPA configuration exists, but a working Metrics API and runtime scaling have not been verified.
- **Monitoring:** Prometheus/Grafana are configured but not installed. Scraping, persistent storage, dashboard provisioning, and node capacity remain unverified. See [monitoring status](monitoring.md) and the [resource budget](monitoring-resource-budget.md).

## Related documentation

- [Project overview and local development](../README.md)
- [Security controls](security.md)
- [Development capacity profiles](development-profiles.md)
