# Deployment

## Current deployment status and safety

No Terraform-managed AWS infrastructure, Kubernetes cluster, Helm release, or monitoring stack has been deployed or activated from this repository. GitHub Actions [run 39468033513](https://github.com/avinashmnth2507-dev/cloudops-platform/actions/runs/39468033513) passed for commit `8e711c8a5338b68fde1bff1ba928088d424c41e9`: test, image build, and Trivy jobs succeeded, while image handoff and GHCR publication were skipped. This run does not cover later documentation edits. GHCR publishing remains disabled and no image is published. The standalone Deployment image is intentionally empty; Helm requires a supplied immutable digest reference. Neither configuration is evidence of an available or approved image. The local app/container inspection and live API results are recorded in the [local verification report](local-verification-report.md). **The infrastructure and cluster commands below are reference examples, not approval to execute them.** Terraform can create billable resources; Kubernetes deployment remains blocked by unverified CNI readiness and open SEC-002. Obtain separate review and authorization before using infrastructure or cluster commands.

## Local

With the existing virtual environment available, run the application manually on loopback and use the bounded demonstration script:

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal, run `scripts/demo-local.sh`. The script does not start or stop the server. See [local demo instructions](local-demo.md).

For offline checks without running the application, use `scripts/verify-local.sh`; it runs local Python, shell, Helm, and Terraform formatting checks when their tools are already available.

The commands below are setup instructions only. This project did not create a virtual environment or install dependencies during the current documentation and demo work:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

## Docker

The following is a setup example; it can build and start a container. It does not establish that an application or Compose container is currently running. Do not use it for read-only runtime verification.

```bash
docker compose up --build
curl http://localhost:8000/health
```

## AWS

**Not approved for execution.** Terraform has not been applied and no AWS resources are reported as deployed for this project. Applying this configuration may incur charges; use it only after a separate infrastructure review and authorization. The copied example selects `t3.micro`, a low-cost placeholder with 1 GiB RAM that does not meet the documented K3s server / Calico single-host baseline. Override `instance_type` with a separately reviewed size before any K3s/Calico deployment; do not treat a larger instance as free. The EC2 resource can still be created if its user-data script exits nonzero: the current script deliberately exits 1 before installing K3s, and that failure does not itself terminate or remove the billable instance.

```bash
cd terraform/environments/dev
cp terraform.tfvars.example terraform.tfvars
# Replace YOUR_PUBLIC_IP with your actual public IPv4 /32.
terraform init
terraform validate
terraform plan
terraform apply
```

## Kubernetes bootstrap configuration

### Capacity and cost

The Terraform default and general `terraform.tfvars.example` remain `t3.micro` to preserve the low-cost generic example; neither is suitable for the intended K3s/Calico host. AWS lists `t3.micro` as 2 vCPU and 1 GiB memory. K3s documents a server baseline of 2 cores and 2 GB RAM, and its server sizing guide lists 2 cores and 4 GB for 0–350 agents under standard workload conditions. Calico's single-host tutorial separately lists 2 CPUs, 2 GB RAM, and 10 GB free disk. These are published prerequisites, not a capacity guarantee for this project's combined Kubernetes, Calico, and application workloads.

The reduced profile's `t3.medium` (2 vCPU, 4 GiB) is a planning candidate that reaches the K3s 4 GB sizing row; the `t3.small` (2 vCPU, 2 GiB) only meets the documented baseline and leaves no meaningful headroom. The full-observability `t3.large` (2 vCPU, 8 GiB) is also an untested estimate. Actual resource use, disk needs, performance, and availability remain unverified. Check the [AWS EC2 instance specifications](https://docs.aws.amazon.com/ec2/latest/instancetypes/gp.html), [K3s requirements](https://docs.k3s.io/installation/requirements), and [Calico single-host prerequisites](https://docs.tigera.io/calico/latest/getting-started/kubernetes/k8s-single-node) before planning a separately authorized environment.

These EC2 choices can incur instance-hour, EBS, public IPv4, data-transfer, and (for burstable T3 instances) CPU-credit charges. Estimate using the selected region, runtime, storage, traffic, credit mode, and account terms before authorization. A user-data failure is not automatic cleanup; stop or terminate a billable instance only through a separately reviewed and authorized action.

The intended K3s release is `v1.36.5+k3s1` on Linux amd64. The offline validation script records the current network intent:

- Pod CIDR: `10.44.0.0/16`
- Service CIDR: `10.43.0.0/16`
- Cluster DNS: `10.43.0.10`
- Flannel: disabled with `--flannel-backend=none`
- K3s embedded NetworkPolicy controller: disabled with `--disable-network-policy`

The script validates local K3s and installer inputs but refuses installation. Terraform EC2 user data now exits before executing an installer. **Neither path installs K3s.** The Terraform AMI filter selects x86_64, but the target AMI and runtime are not deployed or tested. The configured AWS VPC (`10.42.0.0/16`) and public subnet (`10.42.1.0/24`) remain unchanged. The pod and service ranges do not overlap those repository-defined ranges; VPN, peered, and other external CIDRs still require an overlap check.

**This configuration is not ready or approved for deployment.** Disabling Flannel requires a separately installed and working CNI. Calico `v3.33.0` is only a candidate; it is not installed, and Calico bootstrap remains NO-GO. With `--disable-network-policy`, Calico must also provide NetworkPolicy enforcement. Before any separately authorized deployment, resolve K3s artifact and installer provenance, Calico integrity and image pins, CNI installation and readiness, external CIDR overlap, host OS/kernel and networking prerequisites, and EC2 capacity. Until the CNI is installed and verified, pod networking and NetworkPolicy enforcement are unavailable. Keep SEC-002 open and do not enable NetworkPolicy based on configuration alone.

Bundled Traefik, CoreDNS, and Metrics Server remain enabled; this configuration does not pass flags to disable them. Their operation must still be verified after the CNI is ready.

## Offline infrastructure validation

Terraform formatting can be checked locally without initializing providers or contacting AWS:

```bash
terraform fmt -check -recursive terraform
```

This validates formatting only. It does not validate provider behavior, create a plan, confirm account permissions, or provision resources. No AWS resources have been provisioned as part of this project workflow. The K3s bootstrap script explicitly refuses installation. The Calico bootstrap includes a guarded `--apply` path, but Calico installation remains NO-GO and is not authorized in the current project state. Resolve artifact provenance, separately approved checksums, image integrity, host prerequisites, CNI readiness, recovery planning, and SEC-002 blockers before any separately authorized deployment; do not invoke the Calico apply mode before then.

## Cleanup

```bash
terraform destroy
```
