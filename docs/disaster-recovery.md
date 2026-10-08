# Disaster Recovery

The application and infrastructure are reproducible from Git.

Recovery sequence:

1. Clone the repository.
2. Recreate AWS resources with Terraform.
3. Install k3s.
4. Deploy the Helm chart.
5. Install monitoring/logging.
6. Validate health and metrics.

Persistent application data is intentionally minimized in this stateless demo.
