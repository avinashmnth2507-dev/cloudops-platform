# Architecture

```text
Developer
   |
   v
GitHub Repository
   |
   v
GitHub Actions ---- Gitleaks / Tests / Trivy
   |
   v
GHCR Container Image
   |
   v
Terraform
   |
   v
AWS VPC -> Public Subnet -> EC2
                              |
                              v
                             k3s
                              |
             +----------------+----------------+
             |                |                |
          CloudOps        Prometheus          Loki
             |                |                |
             +----------------+----------------+
                              |
                           Grafana
```

The design deliberately uses one EC2 host with k3s rather than EKS to keep the learning environment inexpensive.
