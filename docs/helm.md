# Helm

`helm lint` is a local chart check and does not deploy anything. No Kubernetes cluster or Helm release has been deployed from this repository. GHCR publishing is disabled, so no image has been published by this workflow; the chart's image reference is a placeholder until publishing is explicitly enabled and completed or an immutable image is separately selected. **Do not run the deployment commands below without separate approval.** Deployment also requires a verified CNI and review of the open SEC-002 NetworkPolicy issue.

```bash
helm lint helm/cloudops
helm upgrade --install cloudops helm/cloudops --namespace cloudops --create-namespace
kubectl get all -n cloudops
```

For a future, separately authorized deployment, set the image repository and immutable tag with `--set` only after confirming that the referenced GHCR image has actually been published and is accessible. A GHCR reference alone does not mean an image exists.
