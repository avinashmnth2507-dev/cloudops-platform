# Development capacity profiles

These examples separate two intended EC2 capacity choices while reusing the existing Terraform environment and modules. They only set existing root-module inputs; they do not define a second infrastructure stack, install monitoring, or activate Kubernetes components. The instance sizes are planning estimates, not tested capacity guarantees.

Both examples retain the existing `ap-south-1` region and `cloudops` project name. Replace `YOUR_PUBLIC_IP/32` with the administrator's approved public IPv4 CIDR before using either example. This is a placeholder, not a credential. The root module requires `ssh_cidr` and uses it for SSH and Kubernetes API ingress.

## Reduced development

[`terraform/environments/dev/profiles/reduced.tfvars.example`](../terraform/environments/dev/profiles/reduced.tfvars.example) selects `t3.medium` for the intended reduced set:

- k3s control plane and node services
- Calico, CoreDNS, Traefik, and Metrics Server
- CloudOps application
- No Prometheus/Grafana observability stack

This file changes only the EC2 instance type input. It does not install Calico or otherwise select which software is installed. The current k3s bootstrap disables Flannel and k3s's embedded NetworkPolicy controller, so a separately installed and healthy CNI remains a deployment prerequisite.

## Full observability

[`terraform/environments/dev/profiles/full.tfvars.example`](../terraform/environments/dev/profiles/full.tfvars.example) selects `t3.large` for the reduced set plus the intended Prometheus, Grafana, Prometheus Operator, kube-state-metrics, and node-exporter components.

This is a capacity profile only. It does not install or enable monitoring; both profiles require a separate, explicitly authorized monitoring deployment. The monitoring documentation specifies chart version 91.8.2, and `monitoring/prometheus-values.yaml` defines explicit ServiceMonitor selectors, but this profile does not install the chart. Effective rendered selectors, dashboard provisioning, and runtime discovery remain unverified. See [`docs/monitoring-resource-budget.md`](monitoring-resource-budget.md) and [`docs/monitoring.md`](monitoring.md).

## Capacity evidence and limits

The application Deployment and Helm defaults request `50m` CPU and `64Mi` memory per pod, with limits of `250m` and `256Mi`. Both HPA configurations target two to four replicas. At the four-replica maximum, the application requests total `200m` CPU and `256Mi` memory; its configured limits total `1` CPU and `1Gi` memory. This is only the application's declared budget and excludes Kubernetes, the CNI, and other services.

Starting requests and limits are now configured for Prometheus, Grafana, Prometheus Operator, kube-state-metrics, and node-exporter in `monitoring/prometheus-values.yaml`. These are configuration estimates, not measured usage or a capacity guarantee; the complete stack has not been load-tested. k3s, Calico, the operating system, chart sidecars, and other workloads also consume CPU, memory, and disk. Prometheus retention is three days, but the current `20 GB` encrypted gp3 root disk does not establish sufficient Prometheus storage, persistence, or durability. Storage class, volume capacity, actual disk usage, and behavior remain unresolved. See [`docs/monitoring-resource-budget.md`](monitoring-resource-budget.md) for the component budgets and excluded workloads.

The EC2 module currently configures an encrypted `20 GB` gp3 root volume and exposes no Terraform input to resize it. These profiles do not change that volume. Confirm available space for container images, logs, and any separately configured persistent monitoring data before deployment.

Both proposed instance types are burstable T3 candidates. Terraform does not set an EC2 CPU-credit specification. Verify the selected credit mode and any surplus-credit charges for the intended workload; sustained Prometheus and control-plane load can consume CPU continuously. The EC2 subnet maps public IPv4 addresses on launch, so include current public IPv4 pricing, instance hours, gp3 storage, data transfer, and applicable CPU-credit charges in a region-specific estimate. The default region is `ap-south-1`; verify current prices and account-specific credits or allowances before any deployment.

Neither profile is a validated capacity guarantee. The full stack's effective resource requests, storage needs, and runtime usage have not been measured. Prefer local testing where practical to avoid AWS charges.

## Deployment blockers

Before either profile is used for an infrastructure deployment, resolve and verify the existing project prerequisites: approve exact k3s and Calico versions and artifact integrity; verify host OS/kernel and Calico readiness; check pod/service/VPC ranges against external routes; confirm administrator access and security-group exposure; and replace the application image placeholder with an available immutable image reference. Before full observability, verify the documented chart 91.8.2 against an approved local chart artifact, validate its effective selectors, decide and verify persistent storage, and measure resource use. Keep NetworkPolicy disabled until the actual ingress-controller and Prometheus identities and CNI enforcement are verified. SEC-002 remains open.

These files are examples for review. No infrastructure, cluster components, monitoring stack, or NetworkPolicy is provisioned or activated by them.
