# Calico installation configuration

**Status: review configuration only. Calico has not been installed, and this document is not deployment approval.**

## Candidate compatibility and operator resources

The proposed k3s release is `v1.36.5+k3s1` (Kubernetes 1.36.5). Calico Open Source `v3.33.0` documents Kubernetes 1.36 as tested and provides a K3s installation guide. This supports the Kubernetes minor-version pairing; it does not verify this exact k3s build, host, or AWS network at runtime.

For Kubernetes 1.36 and later, the Calico 3.33 K3s guide specifies this order:

1. Install the Calico CRDs from the v3.33.0 `v3_projectcalico_org.yaml` release artifact.
2. Install the Tigera Operator from the v3.33.0 `tigera-operator.yaml` release artifact. That tagged manifest uses operator image `quay.io/tigera/operator:v1.44.0`.
3. Apply [`k8s/calico/installation.yaml`](../k8s/calico/installation.yaml) after the operator CRD is available.
4. Wait for Calico components and node networking to become ready before relying on CoreDNS, Traefik, Metrics Server, application pods, or NetworkPolicy enforcement.

Official release references:

- [Calico 3.33 K3s installation guide](https://docs.tigera.io/calico/latest/getting-started/kubernetes/k3s/quickstart)
- [v3.33.0 CRD manifest](https://raw.githubusercontent.com/projectcalico/calico/v3.33.0/manifests/v3_projectcalico_org.yaml)
- [v3.33.0 Tigera Operator manifest](https://raw.githubusercontent.com/projectcalico/calico/v3.33.0/manifests/tigera-operator.yaml)
- [Tigera Operator API](https://docs.tigera.io/calico/latest/reference/installation/api/)

These are version references, not a cryptographic integrity check. Before an installation is approved, verify the release source and checksums or signatures, and review/pin container image digests where supported. No external manifests, checksums, or image digests are vendored in this repository. The operator and CRD installation must remain a separate, explicitly version-pinned step; this repository file contains only the Calico `Installation` custom resource.

## Proposed network pool and routing mode

The `Installation` resource explicitly selects the Calico CNI, disables Calico BGP, and defines the IPv4 workload pool as `10.44.0.0/16`, matching the configured k3s `--cluster-cidr`. The pool is distinct from the repository's VPC CIDR `10.42.0.0/16` and k3s service CIDR `10.43.0.0/16`. VPN, peered-VPC, and other externally routed CIDRs still need an overlap check.

The proposed encapsulation is explicitly `VXLAN` (all inter-node workload traffic), rather than relying on Calico's default IP-in-IP mode. BGP is disabled because VXLAN pools do not require BGP. `natOutgoing: Enabled` is explicit so workload egress outside the Calico pool is source-NATed; assess whether preserving pod source addresses to any VPC-connected services is required before deployment.

### Alternatives and AWS implications

- **Native routing, no encapsulation:** Lowest packet overhead, but AWS must route workload addresses. Calico's AWS guidance says native Calico routing within a VPC subnet requires EC2 source/destination checks disabled. Cross-subnet routing also needs a deliberate route-distribution design. The current Terraform does not set `source_dest_check = false`, and its EC2 role only attaches the SSM managed-instance policy; it does not grant Calico permission to change the check. This mode would require separate infrastructure and routing review.
- **VXLAN:** Chosen for this single-node baseline because an overlay carries pod traffic without asking VPC routes to carry the pod CIDR and avoids BGP route distribution. It adds encapsulation and packet-processing overhead and requires path-MTU validation. VXLAN itself adds no AWS managed networking resource; any data-transfer charges depend on actual traffic and placement and are not estimated here. For multiple nodes, allow bidirectional UDP `4789` between node security groups. The current security group has no such ingress rule; its egress rule is unrestricted. A single-node cluster has no remote-node VXLAN peer, but expansion requires a private, node-to-node rule.
- **IP-in-IP:** Has less per-packet header overhead than VXLAN, but AWS security groups must allow IP protocol `4` between nodes. Calico's AWS guidance calls for IP-in-IP and outgoing NAT across different VPC subnets, and its AWS FAQ warns that security groups block incoming IP-in-IP by default. This adds protocol-specific firewall requirements and is not selected here.

Calico's general overlay guidance describes VXLAN for underlays that cannot route workload IPs, while its AWS-specific guide describes IP-in-IP for cross-subnet/VPC traffic. The current project defines one public subnet and a single-node target, not a multi-subnet topology. Therefore VXLAN is a proposal for this configuration, not verified AWS multi-subnet compatibility. Revisit the mode before adding nodes in another subnet. No source/destination-check, security-group, route-table, IAM, or EC2 changes are included here.

## Host and runtime prerequisites

Calico 3.33 requires Linux kernel 5.10 or later, required netfilter/iptables and IP-set/conntrack support, and VXLAN support for this mode. The nodes must permit Calico to manage its interfaces and run its required privileged networking components. Calico requires host IP forwarding; Felix's documented `IPForwarding` default is `Enabled`, but verify the effective setting and host behavior after installation.

Terraform currently selects the most recent matching Ubuntu 24.04 AMI, so the exact deployed AMI, kernel, modules, firewall, and interface behavior are not pinned by this repository. Check them on the intended host before installation. The example EC2 size is `t3.micro`; Calico's single-host tutorial lists 2 CPUs, 2 GB RAM, and 10 GB free disk as its tutorial prerequisites. Treat capacity as an unresolved constraint, especially with the planned monitoring stack.

The k3s bootstrap already disables Flannel with `--flannel-backend=none` and its embedded NetworkPolicy controller with `--disable-network-policy`. Calico must therefore be installed and healthy before pod networking or Kubernetes NetworkPolicies can be relied on. This configuration does not disable bundled Traefik, CoreDNS, or Metrics Server. Confirm their readiness after Calico becomes healthy. Keep the CloudOps NetworkPolicy disabled until the CNI is verified and actual Traefik/Prometheus identities are known.

## Checks before deployment

- Confirm the exact host kernel, required modules, IP forwarding, privileged-container support, and CNI directories on the selected Ubuntu AMI.
- Confirm the pod pool does not overlap any VPC, service, VPN, peered, or external route range.
- Review release signatures/checksums and immutable image digests for the operator, CRDs, and Calico components.
- Decide whether the target remains single-subnet or will span subnets. For expansion, review UDP 4789 security-group scope and AWS source/destination-check behavior with the selected routing mode.
- Install the version-pinned CRDs and operator, then apply the Installation resource; verify Calico status, CNI health, node readiness, CoreDNS, Traefik, and Metrics Server before deploying the application.
- Test permitted and denied pod traffic in an authorized cluster before enabling either standalone or Helm NetworkPolicy.
