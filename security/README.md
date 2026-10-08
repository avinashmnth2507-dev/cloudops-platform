# DevSecOps Controls

## Source
- Gitleaks for secret detection.
- Ruff for static checks.
- pytest for automated tests.

## Container
- Non-root user UID 10001.
- Minimal Python slim image.
- Trivy image scanning.
- No secrets in the image.

## Kubernetes
- Non-root security context.
- `allowPrivilegeEscalation: false`.
- Drop all Linux capabilities.
- RuntimeDefault seccomp profile.
- Read-only root filesystem.
- Resource requests and limits.
- ServiceAccount token automount disabled.
- RBAC with an intentionally empty Role for the application.
- NetworkPolicy.

## AWS
- Dedicated lab identity rather than root credentials.
- Security group restricts SSH and Kubernetes API to `ssh_cidr`.
- EC2 role uses SSM managed instance access.

Before production use, add stronger IAM separation, centralized secrets management, signed images, admission controls, and policy-as-code.
