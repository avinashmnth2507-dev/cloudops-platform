# Deployment

## Current deployment status and safety

No Terraform-managed AWS infrastructure, Kubernetes cluster, Helm release, or monitoring stack has been deployed or activated from this repository. GitHub Actions Run #5 passed CI for commit `f6ba78bcdda1a843e9cb33742826b46e98976f00`, but CI does not publish or deploy the application. GHCR publishing is disabled and the configured image references are placeholders. **The commands below are reference examples, not approval to execute them.** Terraform can create billable resources; Kubernetes deployment also remains blocked by unverified CNI readiness and open SEC-002. Obtain separate review and authorization before using infrastructure or cluster commands.

## Local

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

**Not approved for execution.** Terraform has not been applied and no AWS resources are reported as deployed for this project. Applying this configuration may incur charges; use it only after a separate infrastructure review and authorization.

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

The intended K3s release is `v1.36.5+k3s1` on Linux amd64. The offline validation script records the current network intent:

- Pod CIDR: `10.44.0.0/16`
- Service CIDR: `10.43.0.0/16`
- Cluster DNS: `10.43.0.10`
- Flannel: disabled with `--flannel-backend=none`
- K3s embedded NetworkPolicy controller: disabled with `--disable-network-policy`

The script validates local K3s and installer inputs but refuses installation. Terraform EC2 user data now exits before executing an installer. **Neither path installs K3s.** The Terraform AMI filter selects x86_64, but the target AMI and runtime are not deployed or tested. The configured AWS VPC (`10.42.0.0/16`) and public subnet (`10.42.1.0/24`) remain unchanged. The pod and service ranges do not overlap those repository-defined ranges; VPN, peered, and other external CIDRs still require an overlap check.

**This configuration is not ready or approved for deployment.** Disabling Flannel requires a separately installed and working CNI. Calico `v3.33.0` is only a candidate; it is not installed, and Calico bootstrap remains NO-GO. With `--disable-network-policy`, Calico must also provide NetworkPolicy enforcement. Before any separately authorized deployment, resolve K3s artifact and installer provenance, Calico integrity and image pins, CNI installation and readiness, external CIDR overlap, host OS/kernel and networking prerequisites, and EC2 capacity. Until the CNI is installed and verified, pod networking and NetworkPolicy enforcement are unavailable. Keep SEC-002 open and do not enable NetworkPolicy based on configuration alone.

Bundled Traefik, CoreDNS, and Metrics Server remain enabled; this configuration does not pass flags to disable them. Their operation must still be verified after the CNI is ready.

## Cleanup

```bash
terraform destroy
```
