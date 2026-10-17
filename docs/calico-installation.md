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

The Installation configures the CNI binary directory as `/var/lib/rancher/k3s/data/cni`, the CNI configuration directory as `/var/lib/rancher/k3s/agent/etc/cni/net.d`, and `containerIPForwarding: Enabled`. These paths match the documented K3s defaults used by the current bootstrap, which does not set a custom `--data-dir`. If the K3s data directory or containerd CNI paths change, update these values to match the effective runtime configuration. These are prepared settings only: after an authorized installation, verify the effective containerd paths and generated Calico CNI config, including `container_settings.allow_ip_forwarding: true`. Container forwarding is separate from host forwarding; verify the host sysctl and Felix behavior as described in the runtime prerequisites below. No Calico installation or runtime verification is claimed here.

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

## Offline-input bootstrap implementation

[`scripts/bootstrap-calico.sh`](../scripts/bootstrap-calico.sh) is a fail-closed implementation for a future, explicitly authorized run. It has not been run against a cluster and is not deployment approval. Its `--validate-only` mode checks local inputs without invoking `kubectl`; `--apply` is the only mode that issues Kubernetes commands and always supplies an explicit `KUBE_CONTEXT`.

The artifact directory must contain exactly these two non-empty regular files, with no symlinks, hidden entries, or additional files:

- `v3_projectcalico_org.yaml` — the native Calico v3 CRDs.
- `tigera-operator.yaml` — the Tigera Operator manifest.

Both files must come from the reviewed Calico `v3.33.0` source and provenance process documented in [`calico-artifact-verification.md`](calico-artifact-verification.md). The script requires separately approved SHA-256 values in `APPROVED_CRD_SHA256` and `APPROVED_OPERATOR_SHA256`; each must be exactly 64 hexadecimal characters. Values are external inputs, not embedded in the script. The candidate hashes recorded in the research report are not approved values and must not be copied into these variables without the required independent review. The source tag or a matching Git blob alone does not authenticate the signer.

After the approved manifest files and values have been supplied, the local, non-cluster validation form is:

```bash
export CALICO_ARTIFACT_DIR="/path/to/reviewed-calico-v3.33.0"
export APPROVED_CRD_SHA256="<independently-approved-64-hex-value>"
export APPROVED_OPERATOR_SHA256="<independently-approved-64-hex-value>"
export KUBE_CONTEXT="<explicit-reviewed-context>"
bash scripts/bootstrap-calico.sh --validate-only
```

Replace the placeholders only from an approved review record; the example values are deliberately invalid. The script computes each file's SHA-256 locally using `sha256sum` or macOS `shasum -a 256`, compares both values, and rejects missing, malformed, or mismatched inputs before any Kubernetes command. It performs no downloads. No checksum should be approved solely because it was calculated from a file fetched from the same source.

The future installation order is CRD manifest apply, bounded wait for `installations.operator.tigera.io` to become established, Operator manifest apply, bounded Operator Deployment rollout check, then the repository's `Installation` resource. Readiness then requires the Calico status, `calico-node` DaemonSet, `calico-kube-controllers` Deployment, and all Kubernetes nodes to report ready within fixed timeouts. Before apply mode, the script resolves the explicitly supplied context from local kubeconfig; each subsequent cluster command uses that same context. The script does not switch to Flannel or another CNI.

In apply mode, the two manifests and local Installation resource are copied into a mode-700 temporary directory. The approved hashes are checked against the copied upstream manifest bytes, and only these private snapshots are passed to `kubectl`. This avoids reopening mutable source paths after verification. The local Installation resource has no separate approved hash; its trust depends on the reviewed repository commit and checkout integrity. The context lookup confirms that the requested name exists in the active local kubeconfig, but does not authenticate the cluster identity. Verify the intended target independently before any separately authorized apply. This flow does not defend against a compromised host, shell, `kubectl`, kubeconfig, or a malicious but separately approved manifest; source review and checksum approval remain essential.

## Failure and partial-install recovery

Artifact, file-type, and checksum failures stop before `kubectl` is invoked. In apply mode, a read-only local kubeconfig context lookup happens after those integrity checks and before any cluster-changing command. Apply or readiness failures stop the script with a failure message and bounded command timeout. The script deliberately does not delete resources or attempt automatic rollback: after CRDs, the Operator, or the Installation resource have been accepted, an interrupted run can leave a partial cluster state.

For any failed authorized run, pause further changes. Preserve the cluster state and inspect the explicit target context's CRD establishment, Operator Deployment, Tigera status, Calico DaemonSet and controller Deployment, node conditions, events, and relevant component logs. Redact credentials and sensitive data. Compare the observed state with the pinned manifests and Installation resource, then obtain authorization for a narrowly scoped recovery action. Do not remove CRDs or switch CNI as an automatic recovery step. A rerun is not automatically safe until the partial state and version compatibility have been reviewed.

The command-level waits do not prove DNS, pod-to-pod or pod-to-service connectivity, VXLAN behavior, forwarding, or NetworkPolicy enforcement. Those require separate, bounded runtime checks on an authorized single-node test cluster. Verify CoreDNS and bundled K3s services, generated CNI configuration and forwarding, and permitted/denied test traffic before enabling the CloudOps policy. Keep the policy disabled until actual ingress-controller and monitoring identities are established.

## K3s offline integrity validation and installation refusal

[`scripts/bootstrap-k3s.sh`](../scripts/bootstrap-k3s.sh) now has a local validation mode and an intentionally disabled installation mode. It pins the intended release to `v1.36.5+k3s1` and validates Linux `x86_64` (amd64), the only current Terraform EC2 architecture. It preserves the intended pod CIDR `10.44.0.0/16`, service CIDR `10.43.0.0/16`, cluster DNS `10.43.0.10`, `--flannel-backend=none`, and `--disable-network-policy` as configuration intent; this script does not apply those settings or install K3s.

For `--validate-only`, `K3S_ARTIFACT_DIR` must contain exactly two non-empty regular files, without symlinks or extra entries:

- `k3s` — the K3s `v1.36.5+k3s1` Linux amd64 binary.
- `install.sh` — the exact reviewed installer script from a versioned, immutable K3s source commit.

The caller must supply `APPROVED_K3S_BINARY_SHA256`, `APPROVED_K3S_INSTALLER_SHA256`, and `K3S_INSTALLER_COMMIT`. Both hashes must be separately reviewed 64-character hexadecimal values for their respective exact files, and the source commit must be a full 40-character hex ID. Do not reuse a checksum across files or copy the candidate K3s binary value in the research report into the approval input without separate approval. A commit ID and a matching local SHA-256 do not by themselves authenticate the signer or establish the source-to-file relationship; record the immutable upstream URL, commit, artifact name, target architecture, provenance evidence, reviewer, and approval for each value.

Example local validation on the intended Linux amd64/systemd host:

```bash
export K3S_ARTIFACT_DIR="/path/to/reviewed-k3s-v1.36.5-amd64"
export APPROVED_K3S_BINARY_SHA256="<separately-approved-64-hex-value>"
export APPROVED_K3S_INSTALLER_SHA256="<separately-approved-64-hex-value>"
export K3S_INSTALLER_COMMIT="<reviewed-full-40-hex-commit>"
bash scripts/bootstrap-k3s.sh --validate-only
```

These placeholders are not approval values. Validation fails for a missing or malformed checksum, missing artifact, extra or symlinked entry, checksum mismatch, non-Linux or non-amd64 host, or unavailable `systemctl`. No downloads occur. Synthetic test files can exercise this gate but are not K3s artifacts and provide no deployment evidence.

Even if every local input passes, `bash scripts/bootstrap-k3s.sh --install` exits with an explicit refusal. It does not execute `install.sh`, `k3s`, `systemctl`, `curl`, or any other installation command. The K3s EC2 `user_data` in [`terraform/modules/ec2/main.tf`](../terraform/modules/ec2/main.tf) also fails closed before executing any installer. The mutable `https://get.k3s.io` pipe-to-shell route has been removed from both paths; there is no automatic release, architecture, or CNI fallback.

The official [K3s `v1.36.5+k3s1` release](https://github.com/k3s-io/k3s/releases/tag/v1.36.5%2Bk3s1) lists release-specific binaries and checksum assets. The repository's earlier research records a release-list SHA-256 for the `k3s` binary only; it does not authenticate the installer, checksum metadata, systemd unit, or bundled container images. The [version-pinned installer source](https://github.com/k3s-io/k3s/blob/v1.36.5%2Bk3s1/install.sh) documents a skip-download option, but its source is over a thousand lines and includes additional platform/service and download behavior. That option alone does not prove the script is a safe service-only installer. The official [air-gap installation guide](https://docs.k3s.io/installation/airgap) likewise describes a locally supplied installer but does not establish this project's complete provenance and service setup chain. No installation route is therefore enabled.

Before a future separately authorized implementation, review a complete installer or direct-binary/service design, including all downloaded dependencies, K3s server flags, systemd unit and environment-file contents, ownership, filesystem paths, service lifecycle, upgrade, and partial-failure recovery. Verify the exact release binary and every additional artifact independently; a K3s binary checksum does not authenticate an installer or bundled components. Target-host OS/kernel, systemd and root privileges, CPU, memory, disk, container runtime, firewall, forwarding, Calico prerequisites, and CNI paths still require validation; the current validator checks only Linux/amd64 and that `systemctl` is discoverable. If a future authorized installation fails partway, do not rerun or remove K3s state automatically; inspect cloud-init/service state and obtain a scoped recovery review first.

K3s installation remains **NO-GO**. Validation proves only that local synthetic or reviewed files match supplied values and that the host platform prerequisite check passed. It does not verify artifact provenance, installer safety, cluster readiness, or Calico operation. Any eventual installation requires separate authorization for the exact target and actions.

## Operator and Calico image integrity

The pinned Operator manifest names `quay.io/tigera/operator:v1.44.0`, which is a release tag, not an immutable digest. Calico's [component-version reference](https://docs.tigera.io/calico/latest/reference/component-versions) pairs that Operator tag with Calico `v3.33.0`. The official [ImageSet instructions](https://docs.tigera.io/calico/latest/operations/image-options/imageset) describe digest-based image pinning and obtaining the effective image list from the Operator with `--print-images=list`. That requires running the Operator image and checking image registry metadata; neither action was performed here. The guide's example digests are illustrative and must not be copied.

The Calico `v3.33` [upgrade notes](https://docs.tigera.io/calico/latest/operations/upgrading/upgrade-notes) describe a consolidation of many components into `calico/calico`; older per-component image lists must not be assumed. For this project's basic Installation, the likely image categories include the Operator, node/networking and CNI workloads, and Kubernetes controllers. Optional flow-visibility, API, gateway, or other feature images depend on the effective Operator configuration. These categories are not a complete verified image inventory. The Operator-generated references, platform-specific or index digest choice, and approved immutable digests remain unresolved; the offline Calico bootstrap script does not pin or verify images and therefore cannot be treated as deployment-ready.

## Requirements before any runtime installation

Calico bootstrap remains **NO-GO**, and SEC-002 remains **OPEN**. Before requesting a separate installation authorization, all of the following are required:

1. Independent provenance review of the pinned Calico source and formal approval of both manifest SHA-256 values. The existing candidate values remain unapproved.
2. A reviewed K3s installation design with architecture-specific binary integrity approval and no unverified mutable installer execution.
3. A pinned and reviewed Operator and Calico component image inventory. The manifest names `quay.io/tigera/operator:v1.44.0`, but no immutable digest is approved; Operator-generated image references and digests are not fully established.
4. Target-host checks for Linux kernel, CPU, memory, disk, netfilter/iptables, conntrack, IP-set, VXLAN, host IP forwarding, privileges, effective containerd CNI paths, and CIDR overlap.
5. A reviewed target context, partial-install recovery plan, and explicit authorization for the exact cluster and actions.
6. Runtime validation of Calico/CNI readiness, node readiness, DNS, pod and service traffic, forwarding, and NetworkPolicy enforcement before application deployment or policy enablement.

Static shell checks and stubbed tests can validate input gates and command ordering only. They do not verify artifact trust, Kubernetes API compatibility, operator-generated images, host prerequisites, or runtime networking. This documentation and the script do not authorize installation or change the overall bootstrap **NO-GO** decision.
