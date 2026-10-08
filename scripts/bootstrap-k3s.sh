#!/usr/bin/env bash
set -euo pipefail
curl -sfL https://get.k3s.io | sh -
sudo kubectl get nodes
