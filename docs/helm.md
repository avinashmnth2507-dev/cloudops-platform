# Helm

```bash
helm lint helm/cloudops
helm upgrade --install cloudops helm/cloudops --namespace cloudops --create-namespace
kubectl get all -n cloudops
```

Set the image repository and tag with `--set` when deploying a specific GHCR image.
