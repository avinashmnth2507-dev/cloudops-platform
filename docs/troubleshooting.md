# Troubleshooting

## Pod not starting

```bash
kubectl describe pod -n cloudops <pod>
kubectl logs -n cloudops <pod>
```

## Image pull errors

Verify the GHCR repository is public or configure an imagePullSecret.

## Readiness failures

```bash
kubectl get endpoints -n cloudops
kubectl exec -n cloudops deploy/cloudops -- wget -qO- http://127.0.0.1:8000/ready
```

## Terraform problems

```bash
terraform fmt -recursive
terraform validate
terraform plan
```
