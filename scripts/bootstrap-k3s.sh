#!/usr/bin/env bash
set -euo pipefail
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=v1.36.5+k3s1 INSTALL_K3S_EXEC="server --cluster-cidr=10.44.0.0/16 --service-cidr=10.43.0.0/16 --cluster-dns=10.43.0.10 --flannel-backend=none --disable-network-policy" sh -s -
sudo kubectl get nodes
