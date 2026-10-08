# Deployment

## Local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

## Docker

```bash
docker compose up --build
curl http://localhost:8000/health
```

## AWS

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

Both the Terraform EC2 bootstrap and `scripts/bootstrap-k3s.sh` pin k3s to `v1.36.5+k3s1` and configure:

- Pod CIDR: `10.44.0.0/16`
- Service CIDR: `10.43.0.0/16`
- Cluster DNS: `10.43.0.10`
- Flannel: disabled with `--flannel-backend=none`
- k3s embedded NetworkPolicy controller: disabled with `--disable-network-policy`

The configured AWS VPC (`10.42.0.0/16`) and public subnet (`10.42.1.0/24`) are unchanged. The pod and service ranges do not overlap those repository-defined ranges. Any VPN, peered, or other externally routed CIDRs still need to be checked for overlap.

**This configuration is not ready for deployment.** Disabling Flannel requires a separately installed and working CNI. Calico `v3.33.0` is only a candidate; it is not installed or pinned by this project change. With `--disable-network-policy`, Calico must also provide the NetworkPolicy enforcement engine. Before deployment, decide and verify Calico's installation method, version, IP pool and routing/encapsulation mode; check external CIDR overlap, host OS/kernel and networking prerequisites, and EC2 capacity. Until a CNI is installed and verified, pod networking and NetworkPolicy enforcement are unavailable.

Bundled Traefik, CoreDNS, and Metrics Server remain enabled; this configuration does not pass flags to disable them. Their operation must still be verified after the CNI is ready.

## Cleanup

```bash
terraform destroy
```
