# Cost Control

The design avoids EKS, NAT Gateway, RDS and other persistent managed services.

Use a single small EC2 instance for the lab. Destroy the environment when finished:

```bash
terraform destroy
```

Always review AWS Billing / Free Tier before creating resources and verify the current eligibility for your account.
