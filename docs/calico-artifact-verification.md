# Calico Artifact and Installation Verification

**Research date:** 2026-10-16
**Status:** Research only. No Calico artifacts were downloaded, installed, or applied. The bootstrap, Terraform, Kubernetes, Helm, and CI files were not changed. No cluster runtime verification has been performed.

## Summary

The exact upstream releases exist: k3s `v1.36.5+k3s1`, Calico `v3.33.0`, and Tigera Operator `v1.44.0`. Calico 3.33 documents Kubernetes 1.36 as tested and includes a K3s installation guide. The Tigera Operator 1.44.0 release identifies Calico 3.33.0. This is upstream support evidence for the Kubernetes minor-version pairing and the Calico/operator pairing; the sources reviewed do not provide a certification entry for the exact k3s patch `v1.36.5+k3s1`.

**Recommendation: NO-GO for implementing or executing the bootstrap yet.** Resolve the K3s/Calico CNI path mapping, enable the forwarding behavior K3s documents, establish reviewable hashes for the exact raw manifests and image digests, and validate host prerequisites first. The project continues to disable Flannel and k3s's policy controller, so no pod CNI or policy enforcement is available until Calico has been installed and verified. SEC-002 remains open.

## Repository evidence

The repository is on `main` at `6362d0e791cca2b6bd1bf8528622b745df3fe383`. No tracked or staged changes were present at preflight. The only untracked files were the existing `Dockerfile.distroless`, `Dockerfile.sec027`, and `Dockerfile.sec029c` candidate files; they were left untouched.

The inspected local configuration shows:

- `scripts/bootstrap-k3s.sh` and `terraform/modules/ec2/main.tf` set k3s to `v1.36.5+k3s1`, pod CIDR `10.44.0.0/16`, service CIDR `10.43.0.0/16`, `--flannel-backend=none`, and `--disable-network-policy`.
- Those bootstrap paths install k3s only. They do not install Calico CRDs, the Tigera Operator, or an `Installation` resource.
- `k8s/calico/installation.yaml` selects Calico CNI, disables BGP, and configures `10.44.0.0/16` with VXLAN and outgoing NAT. It does not set CNI binary/config directories or `containerIPForwarding`.
- `docs/calico-installation.md` describes the intended order and prerequisites, but explicitly has no artifact integrity data and does not claim a runtime deployment.

The configured pod CIDR matches the Calico IP pool. The pod CIDR and service CIDR do not overlap each other. The repository also documents VPC CIDR `10.42.0.0/16`; VPN, peered-VPC, host, and other externally routed ranges still need an overlap check.

## Upstream release verification

| Component | Finding | Evidence and limit |
|---|---|---|
| k3s `v1.36.5+k3s1` | Exact stable release exists; it embeds Kubernetes `v1.36.5` and containerd `v2.3.4-k3s1.36`. | [Official k3s release](https://github.com/k3s-io/k3s/releases/tag/v1.36.5%2Bk3s1). This establishes the release and embedded versions, not host compatibility or installation success. |
| Calico `v3.33.0` | Exact release exists. GitHub reports a signed tag and a verified commit signature. | [Official Calico release](https://github.com/projectcalico/calico/releases/tag/v3.33.0). The signature was not independently verified locally. |
| Tigera Operator `v1.44.0` | Exact release exists and identifies Calico `v3.33.0`. | [Official Tigera Operator release](https://github.com/tigera/operator/releases/tag/v1.44.0). This supports the version pairing; it does not establish image digests. |
| Kubernetes compatibility | Calico 3.33 lists Kubernetes 1.36 among the versions it tests and provides a K3s-specific quickstart. | [Calico system requirements](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements) and [Calico on K3s quickstart](https://docs.tigera.io/calico/latest/getting-started/kubernetes/k3s/quickstart). No source reviewed explicitly names the exact k3s patch release as a certified pair. |

Conclusion: the proposed versions are not invented, and the documented Kubernetes minor and operator release line up. Treat the exact k3s build pairing as **version-level supported but patch-level not independently certified by the sources reviewed**. Runtime testing remains necessary.

## Artifact inventory and integrity

| Artifact | Version and official source | Integrity evidence found | Status / concern |
|---|---|---|---|
| Calico CRD manifest, `v3_projectcalico_org.yaml` | Calico `v3.33.0`; [raw release-tag manifest](https://raw.githubusercontent.com/projectcalico/calico/v3.33.0/manifests/v3_projectcalico_org.yaml). The manifest includes the `Installation` CRD schema. | The source is under the Calico release tag. GitHub reports the `v3.33.0` tag/commit signature as verified. No standalone SHA-256 for this raw YAML was found in the release evidence reviewed. | Integrity can be established by independently verifying the signed release tag against a trusted key, comparing the file to the tagged Git object, and recording a locally computed SHA-256 after review. That verification has not been done here. |
| CRD Helm chart archive, `crd.projectcalico.org.v1-v3.33.0.tgz` | Calico `v3.33.0`; attached to the [official release](https://github.com/projectcalico/calico/releases/tag/v3.33.0). | GitHub lists SHA-256 `bbb9643633609941ef2a00b400798b2967a348d55ad8d1e20bd9f61c3ec3c73f`. This hash is for the chart archive only. | This is usable integrity evidence only if the future design chooses and verifies that exact archive. It is not the checksum for the raw CRD YAML manifest. |
| Tigera Operator manifest, `tigera-operator.yaml` | Calico `v3.33.0`; [raw release-tag manifest](https://raw.githubusercontent.com/projectcalico/calico/v3.33.0/manifests/tigera-operator.yaml). It references `quay.io/tigera/operator:v1.44.0`. | Same GitHub signed-tag/verified-commit evidence for the Calico source. No standalone SHA-256 for this raw YAML was found in the evidence reviewed. | Verify signed release source and compute/store a reviewed file hash before bootstrap use. The Operator Deployment sets `hostNetwork: true` and its ServiceAccount is bound to cluster-scoped RBAC roles. Its namespace has Pod Security enforcement labeled `privileged`, but the Operator container has no explicit `securityContext.privileged: true` setting in this manifest. Calico networking components rendered from the Installation may have separate privilege requirements; review those rendered resources before deployment. |
| Calico `Installation` schema | Included in the v3.33.0 CRD manifest above; documented in the [Tigera Operator API reference](https://docs.tigera.io/calico/latest/reference/installation/api/). | Same source integrity as the CRD manifest. | Validate the repository's custom resource against the exact pinned CRD/schema before applying it. The project's existing resource has no explicit CNI paths or IP-forwarding setting. |
| Installation custom-resource example | [Official v3.33.0 example](https://raw.githubusercontent.com/projectcalico/calico/v3.33.0/manifests/custom-resources.yaml). | Same release-tag provenance; no separate file checksum found. | Its sample pool is `192.168.0.0/16`; do not use that value for this project. Retain the reviewed project CIDR `10.44.0.0/16` after checking all routed networks. |
| Operator and Calico component images | Official version references: [Calico component versions](https://docs.tigera.io/calico/latest/reference/component-versions), [image options](https://docs.tigera.io/calico/latest/operations/image-options/alternate-registry), and [Calico 3.33 upgrade notes](https://docs.tigera.io/calico/latest/operations/upgrading/upgrade-notes). Release-tag manifest specifies operator `quay.io/tigera/operator:v1.44.0`; Calico components use the `v3.33.0` release line. | No immutable per-image digest was verified in this research. The official [ImageSet guide](https://docs.tigera.io/calico/latest/operations/image-options/imageset) recommends pinning images by registry digest. | For the current default CNI mode (`All`), the component image set must include the operator and the Calico images used for node/CNI and upstream CNI plugins. Calico 3.33 consolidates many components into `calico/calico` and publishes some images separately; do not reuse older image lists. Obtain the exact effective list for this Installation and pin verified digests before deployment. |

The official ImageSet guide obtains the effective image list by running the versioned Operator image and obtains digests from registry image metadata. Neither operation was performed because this task prohibits container operations and image downloads. The guide's sample digests are placeholders and must not be copied. The raw custom-resource manifest also has no separately verified checksum in the evidence reviewed.

### Fail-closed integrity approach

1. Pin the exact official release URLs and versions; never substitute another k3s or Calico version automatically.
2. For GitHub-hosted YAML, verify the release tag signature against a trusted, independently established key, confirm the exact file is present in that tagged commit, and review it before computing and recording its SHA-256. GitHub's “Verified” badge is useful upstream evidence, but was not independently validated in this audit.
3. Alternatively, if using the official CRD chart archive, compare it against the published archive SHA-256 above and separately validate that its rendered CRDs match the intended Kubernetes 1.36 installation path.
4. Resolve the Operator's full image list for this exact Installation and pin registry digests, preferably using an `ImageSet`. Store the reviewed version/digest mapping in source control. Never infer digests from tags or copy example hashes.
5. Make every fetch, signature/hash check, schema check, apply, and readiness wait fail closed. A missing artifact, checksum, registry digest, or readiness condition must stop installation. There should be no alternate-CNI or version fallback.

## Compatibility and networking prerequisites

| Area | Verified documentation | Project implication |
|---|---|---|
| K3s custom CNI flags | K3s says a custom CNI should use `--flannel-backend=none` and recommends `--disable-network-policy` to avoid policy-controller conflicts. | Existing bootstrap flags match the documented pattern. With Flannel and the embedded controller disabled, Calico must become healthy before any workload networking or policy enforcement is relied on. |
| CNI directories | [K3s documents](https://docs.k3s.io/networking/multus-ipams) its CNI binary directory as `/var/lib/rancher/k3s/data/cni` and config directory as `/var/lib/rancher/k3s/agent/etc/cni/net.d`. The [Tigera Operator API](https://docs.tigera.io/calico/latest/reference/installation/api/) defaults to `/opt/cni/bin` and `/etc/cni/net.d` for other providers. | This is an unresolved path mismatch in the sources/configuration reviewed. The Calico K3s quickstart establishes a supported K3s installation path, but the current project resource does not explicitly reconcile these paths. Confirm whether this exact K3s release exposes compatible paths or configure the Operator to the actual K3s paths before implementing bootstrap logic. Do not assume a symlink. |
| CNI IP forwarding | K3s's [custom CNI guidance](https://docs.k3s.io/networking/basic-network-options) says the generated Calico CNI configuration should set `container_settings.allow_ip_forwarding: true`. The Tigera API exposes `calicoNetwork.containerIPForwarding`, whose default is `Disabled`. | The project's `Installation` omits this field, so the documented default is disabled. Correct the resource after confirming the v3.33 CRD behavior; verify the generated CNI config has forwarding enabled. |
| Kernel and host | [Calico requirements](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements) specify Linux kernel 5.10+ and required networking dependencies; nodes must permit management of Calico interfaces. | The actual target kernel, netfilter/iptables, conntrack/IP-set and VXLAN support, IP forwarding, privileges, and filesystem paths are not verified by repository source. The Docker Desktop Linux VM also needs its own host-kernel and resource validation; the Mac host kernel is not the Kubernetes node kernel. |
| VXLAN | Calico requires VXLAN support for the selected mode. Calico documents bidirectional UDP 4789 between nodes for VXLAN. | One node does not exercise inter-node VXLAN traffic. For any multi-node expansion, allow UDP 4789 only between node identities/security groups and check MTU. No such runtime validation has occurred. |
| CIDRs | k3s uses pod `10.44.0.0/16` and service `10.43.0.0/16`; Calico pool is `10.44.0.0/16`; repository documentation lists VPC `10.42.0.0/16`. | The pod/service/VPC ranges are pairwise distinct as listed. Check VPN, peered, host, and external routes before installation. Preserve the configured CIDRs unless a network review approves a coordinated change. |
| Single node and capacity | Calico's K3s quickstart explicitly describes a single-node test/development setup and directs production installations to its multi-node guide. | A single-node run can validate CNI, DNS, local pod/service traffic, and policy behavior, but cannot establish availability, inter-node VXLAN, or production capacity. The project's small-instance and 8 GB laptop constraints require resource budgeting; do not add the full monitoring stack during initial CNI validation. |

The Calico Operator defaults are provider-sensitive in some areas; its API does not document a K3s-specific provider value. This does not negate Calico's K3s quickstart, but means the quickstart, K3s path documentation, and the project's Operator resource need to be reconciled explicitly before claiming a reproducible install.

## Proposed installation and readiness sequence

The first three Calico steps follow the official K3s quickstart for Kubernetes 1.36+: CRDs, Operator, then the `Installation` custom resource. The bounded timeouts below are proposed operational limits, not timeout values mandated by upstream.

1. **Preflight k3s host and release.** Verify the target is supported Linux/amd64 with kernel 5.10+, required netfilter, conntrack, IP-set and VXLAN support, usable IP forwarding, sufficient CPU/memory/disk, and correct CNI directories. Verify the pinned k3s release artifact and its integrity before installation. Keep the documented pod/service CIDRs and both CNI-disabling flags. Fail if any check is inconclusive; do not fall back to Flannel.
2. **Install CRDs.** Verify the chosen v3.33.0 CRD artifact before applying it. Wait up to 120 seconds for `installations.operator.tigera.io` (and required Calico CRDs) to report `Established`; stop on timeout or API/schema error.
3. **Install the Tigera Operator.** Verify the v3.33.0 Operator manifest and pin the Operator image digest. Apply it only after CRDs are established. Wait up to 180 seconds for the Operator deployment to become available; stop on pull, RBAC, or readiness errors.
4. **Validate and apply Installation.** Validate `k8s/calico/installation.yaml` against the pinned CRD. Preserve the pod CIDR and VXLAN selection. Resolve and explicitly configure the K3s CNI paths and enable the documented CNI container IP forwarding behavior before applying. Do not apply if either remains unknown.
5. **Wait for Calico components.** Wait up to 300 seconds for `TigeraStatus/calico` to show `Available=True`, `Progressing=False`, and `Degraded=False`; also require the single-node `calico-node` DaemonSet to have all desired pods ready. Stop on timeout; do not retry indefinitely.
6. **Wait for node readiness.** After Calico is healthy, wait up to 180 seconds for the Kubernetes node to be `Ready`. Waiting before CNI installation can fail simply because no CNI is present; waiting after the Calico phase makes the condition meaningful.
7. **Verify networking and DNS.** Use a small isolated test namespace and short-lived test pods to check pod-to-pod traffic, Service routing, CoreDNS name resolution, and outbound behavior required by the application. Bound each probe and fail on unexpected results. Do not install application or monitoring workloads during this baseline test.
8. **Verify policy enforcement.** In a disposable test namespace, prove both an explicitly allowed flow and a denied flow with a temporary NetworkPolicy. Verify Calico reports healthy policy components. Keep the application NetworkPolicy disabled until actual ingress-controller and Prometheus identities and required traffic are known; keep SEC-002 open until the policy review and runtime tests pass.

The K3s quickstart uses unbounded `watch` examples for sample pods and node readiness. A bootstrap should instead use explicit deadlines and emit the failed resource/status on timeout. A timeout must leave a clear failed run, not silently proceed.

## Remaining blockers

| Blocker | Minimum resolution | Runtime evidence eventually required? |
|---|---|---|
| CNI path mapping is unresolved between K3s documentation and Tigera defaults. | Confirm path behavior for pinned k3s and explicitly configure the Operator `binDir`/`confDir` or document verified path compatibility. | Yes: inspect the actual node paths and prove CNI invocation works. |
| CNI container IP forwarding is omitted; Tigera API default is `Disabled`, while K3s says Calico CNI config should allow forwarding. | Set the supported v3.33 Installation field to `Enabled`; validate rendered CNI configuration and host forwarding. | Yes: verify generated config and pod/service traffic. |
| Raw CRD and Operator manifests have no published per-file SHA-256 identified in this audit. | Independently verify the signed Calico release source, review exact files, and record their hashes; alternatively use a verified official CRD chart archive where appropriate. | No cluster needed for artifact verification; runtime validation still follows. |
| Required image set and immutable digests are unknown. | Resolve the exact image list for this Installation; pin registry digests in Operator/`ImageSet` configuration. | Registry metadata validation is needed; a cluster is needed to confirm the Operator uses the intended ImageSet. |
| Bootstrap fetches the mutable `get.k3s.io` installer script directly. | Pin/review the installer content or use an approved verified k3s binary/install artifact; retain the exact release version and checksums. | Installation test is needed after source integrity is settled. |
| Target host/kernel, CNI modules, forwarding, network ranges, and resource headroom are not runtime-verified. | Collect host/route/resource evidence and confirm the intended UDP 4789 path for any multi-node deployment. | Yes. |
| No CNI or NetworkPolicy enforcement has been installed and tested. | Complete bounded component, node, DNS, pod-network, and allow/deny policy checks before application deployment. | Yes; this is the final SEC-002 deployment gate. |

## Decision

**NO-GO for DEV-003B-04B bootstrap implementation at this point.** The release versions are valid and their documented compatibility is promising, but the current resource has a concrete forwarding mismatch and unresolved CNI directory behavior. Image digests and raw manifest integrity records are also absent. The next development task should first resolve and document the K3s CNI paths and forwarding fields against the exact pinned CRD, then add reviewed artifact hashes and image digests. Only after static validation should a separately authorized, isolated runtime validation be planned. No AWS deployment is recommended at this stage.
