# Troubleshooting

These are reference diagnostics for an already deployed, separately authorized Kubernetes or Terraform environment. This repository does not establish that such an environment currently exists. Do not run infrastructure or cluster commands until the target environment and authorization are confirmed.

## Pod not starting

```bash
kubectl describe pod -n cloudops <pod>
kubectl logs -n cloudops <pod>
```

## Image pull errors

GHCR publishing is disabled in this repository's workflow, so the workflow has not published an image. Treat owner and tag values in the manifests as placeholders. Before troubleshooting a pull, confirm that the selected immutable image has actually been published and that its visibility or `imagePullSecret` matches the cluster's access requirements.

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
