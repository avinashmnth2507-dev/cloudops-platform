# Security

Security is layered across source, container, Kubernetes and AWS.

Never commit real secrets. Use environment variables, Kubernetes Secrets, or a dedicated secrets manager for real deployments.

For the AWS lab, restrict SSH and Kubernetes API access to your own public IP using `ssh_cidr`.
