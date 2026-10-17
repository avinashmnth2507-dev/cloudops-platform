# Calico Artifact and Installation Verification

**Research date:** 2026-10-16
**Status:** Research only. No Calico artifacts were downloaded, installed, or applied. The bootstrap, Terraform, Kubernetes, Helm, and CI files were not changed. No cluster runtime verification has been performed.

## Summary

The exact upstream releases exist: k3s `v1.36.5+k3s1`, Calico `v3.33.0`, and Tigera Operator `v1.44.0`. Calico 3.33 documents Kubernetes 1.36 as tested and includes a K3s installation guide. The Tigera Operator 1.44.0 release identifies Calico 3.33.0. This is upstream support evidence for the Kubernetes minor-version pairing and the Calico/operator pairing; the sources reviewed do not provide a certification entry for the exact k3s patch `v1.36.5+k3s1`.

**Recommendation: NO-GO for implementing or executing the bootstrap yet.** The K3s/Calico CNI paths and forwarding fields are now specified at the static configuration level in the research addendum below. Establish reviewable hashes for the exact raw manifests and image digests, validate host prerequisites, and later runtime-verify the CNI paths and forwarding behavior before deployment. The project continues to disable Flannel and k3s's policy controller, so no pod CNI or policy enforcement is available until Calico has been installed and verified. SEC-002 remains open.

## Repository evidence

The repository is on `main` at `6362d0e791cca2b6bd1bf8528622b745df3fe383`. No tracked or staged changes were present at preflight. The only untracked files were the existing `Dockerfile.distroless`, `Dockerfile.sec027`, and `Dockerfile.sec029c` candidate files; they were left untouched.

The inspected local configuration shows:

- `scripts/bootstrap-k3s.sh` and `terraform/modules/ec2/main.tf` set k3s to `v1.36.5+k3s1`, pod CIDR `10.44.0.0/16`, service CIDR `10.43.0.0/16`, `--flannel-backend=none`, and `--disable-network-policy`.
- Those bootstrap paths install k3s only. They do not install Calico CRDs, the Tigera Operator, or an `Installation` resource.
- `k8s/calico/installation.yaml` selects Calico CNI, disables BGP, configures `10.44.0.0/16` with VXLAN and outgoing NAT, and now explicitly sets the documented K3s CNI directories and `containerIPForwarding: Enabled`. These are configuration values, not runtime evidence.
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
| CRD Helm chart archive, `crd.projectcalico.org.v1-v3.33.0.tgz` | Calico `v3.33.0`; attached to the [official release](https://github.com/projectcalico/calico/releases/tag/v3.33.0). | GitHub lists SHA-256 `bbb9643633609941ef2a00b400798b2967a348d55ad8d1e20bd9f61c3ec3c73f`. This hash is for the chart archive only. | This archive is for the legacy `crd.projectcalico.org/v1` chart. It is not the chart or checksum for the native `projectcalico.org/v3` raw manifest selected by Calico's Kubernetes 1.36+ installation flow, and must not be substituted for that manifest. |
| Tigera Operator manifest, `tigera-operator.yaml` | Calico `v3.33.0`; [raw release-tag manifest](https://raw.githubusercontent.com/projectcalico/calico/v3.33.0/manifests/tigera-operator.yaml). It references `quay.io/tigera/operator:v1.44.0`. | Same GitHub signed-tag/verified-commit evidence for the Calico source. No standalone SHA-256 for this raw YAML was found in the evidence reviewed. | Verify signed release source and compute/store a reviewed file hash before bootstrap use. The Operator Deployment sets `hostNetwork: true` and its ServiceAccount is bound to cluster-scoped RBAC roles. Its namespace has Pod Security enforcement labeled `privileged`, but the Operator container has no explicit `securityContext.privileged: true` setting in this manifest. Calico networking components rendered from the Installation may have separate privilege requirements; review those rendered resources before deployment. |
| Calico `Installation` schema | Included in the v3.33.0 CRD manifest above; documented in the [Tigera Operator API reference](https://docs.tigera.io/calico/latest/reference/installation/api/). | Same source integrity as the CRD manifest. | The project resource now specifies the supported CNI paths and IP-forwarding field. Validate it against the pinned CRD before applying and verify the generated CNI config at runtime. |
| Installation custom-resource example | [Official v3.33.0 example](https://raw.githubusercontent.com/projectcalico/calico/v3.33.0/manifests/custom-resources.yaml). | Same release-tag provenance; no separate file checksum found. | Its sample pool is `192.168.0.0/16`; do not use that value for this project. Retain the reviewed project CIDR `10.44.0.0/16` after checking all routed networks. |
| Operator and Calico component images | Official version references: [Calico component versions](https://docs.tigera.io/calico/latest/reference/component-versions), [image options](https://docs.tigera.io/calico/latest/operations/image-options/alternate-registry), and [Calico 3.33 upgrade notes](https://docs.tigera.io/calico/latest/operations/upgrading/upgrade-notes). The tagged Operator manifest specifies `quay.io/tigera/operator:v1.44.0`; documented Calico image tags are `v3.33.0`. | No immutable per-image digest was verified in this research. The official [ImageSet guide](https://docs.tigera.io/calico/latest/operations/image-options/imageset) describes digest pinning, but its sample values are examples, not evidence for this installation. | Only the Operator image is explicit in the static Operator manifest. The Operator renders Calico workloads and selects images according to the Installation and enabled features. Calico 3.33 consolidated many former component images into `calico/calico`; do not reuse pre-3.33 image lists. Resolve the exact rendered image set and pin reviewed digests before deployment. |

The official ImageSet guide obtains the effective image list by running the versioned Operator image and obtains digests from registry image metadata. Neither operation was performed because this task prohibits container operations and image downloads. The guide's sample digests are placeholders and must not be copied. The raw custom-resource manifest also has no separately verified checksum in the evidence reviewed.

### Fail-closed integrity approach

1. Pin the exact official release URLs and versions; never substitute another k3s or Calico version automatically.
2. For GitHub-hosted YAML, verify the release tag signature against a trusted, independently established key, confirm the exact file is present in that tagged commit, and review it before computing and recording its SHA-256. GitHub's “Verified” badge is useful upstream evidence, but was not independently validated in this audit.
3. The previously cited `crd.projectcalico.org.v1` chart checksum is not applicable to the native v3 CRD manifest selected for Kubernetes 1.36+. For the selected native-v3 path, verify the signed release source, review the exact manifest, and record a separately reviewed SHA-256 for that file. Do not transfer a chart checksum to a raw manifest.
4. Resolve the Operator's full image list for this exact Installation and pin registry digests, preferably using an `ImageSet`. Store the reviewed version/digest mapping in source control. Never infer digests from tags or copy example hashes.
5. Make every fetch, signature/hash check, schema check, apply, and readiness wait fail closed. A missing artifact, checksum, registry digest, or readiness condition must stop installation. There should be no alternate-CNI or version fallback.

## Compatibility and networking prerequisites

| Area | Verified documentation | Project implication |
|---|---|---|
| K3s custom CNI flags | K3s says a custom CNI should use `--flannel-backend=none` and recommends `--disable-network-policy` to avoid policy-controller conflicts. | Existing bootstrap flags match the documented pattern. With Flannel and the embedded controller disabled, Calico must become healthy before any workload networking or policy enforcement is relied on. |
| CNI directories | [K3s documents](https://docs.k3s.io/networking/multus-ipams) its CNI binary directory as `/var/lib/rancher/k3s/data/cni` and its example config directory as `/var/lib/rancher/k3s/agent/etc/cni/net.d`. The [v3.33.0 Tigera schema](https://raw.githubusercontent.com/projectcalico/calico/v3.33.0/manifests/v3_projectcalico_org.yaml) supports `cni.binDir` and `cni.confDir` and defaults to generic provider paths. | The proposed explicit K3s path overrides are specified in the addendum. Confirm effective paths and CNI operation on the target runtime before deployment; no symlink or successful CNI installation is assumed. |
| CNI IP forwarding | K3s's [custom CNI guidance](https://docs.k3s.io/networking/basic-network-options) requires generated Calico CNI configuration to allow container IP forwarding. The v3.33.0 schema exposes `calicoNetwork.containerIPForwarding`, default `Disabled`. | The addendum specifies `containerIPForwarding: Enabled`. Confirm generated CNI configuration and host forwarding behavior during runtime validation. |
| Kernel and host | [Calico requirements](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements) specify Linux kernel 5.10+ and required networking dependencies; nodes must permit management of Calico interfaces. | The actual target kernel, netfilter/iptables, conntrack/IP-set and VXLAN support, IP forwarding, privileges, and filesystem paths are not verified by repository source. The Docker Desktop Linux VM also needs its own host-kernel and resource validation; the Mac host kernel is not the Kubernetes node kernel. |
| VXLAN | Calico requires VXLAN support for the selected mode. Calico documents bidirectional UDP 4789 between nodes for VXLAN. | One node does not exercise inter-node VXLAN traffic. For any multi-node expansion, allow UDP 4789 only between node identities/security groups and check MTU. No such runtime validation has occurred. |
| CIDRs | k3s uses pod `10.44.0.0/16` and service `10.43.0.0/16`; Calico pool is `10.44.0.0/16`; repository documentation lists VPC `10.42.0.0/16`. | The pod/service/VPC ranges are pairwise distinct as listed. Check VPN, peered, host, and external routes before installation. Preserve the configured CIDRs unless a network review approves a coordinated change. |
| Single node and capacity | Calico's K3s quickstart explicitly describes a single-node test/development setup and directs production installations to its multi-node guide. | A single-node run can validate CNI, DNS, local pod/service traffic, and policy behavior, but cannot establish availability, inter-node VXLAN, or production capacity. The project's small-instance and 8 GB laptop constraints require resource budgeting; do not add the full monitoring stack during initial CNI validation. |

The Calico Operator defaults are provider-sensitive in some areas; its API does not document a K3s-specific provider value. The addendum reconciles the documented paths at the configuration level with explicit supported fields. This does not claim the quickstart's generated resources or these overrides have been runtime-tested.

## Proposed installation and readiness sequence

The first three Calico steps follow the official K3s quickstart for Kubernetes 1.36+: CRDs, Operator, then the `Installation` custom resource. The bounded timeouts below are proposed operational limits, not timeout values mandated by upstream.

1. **Preflight k3s host and release.** Verify the target is supported Linux/amd64 with kernel 5.10+, required netfilter, conntrack, IP-set and VXLAN support, usable IP forwarding, sufficient CPU/memory/disk, and the effective CNI directories. Verify the pinned k3s release artifact and its integrity before installation. Keep the documented pod/service CIDRs and both CNI-disabling flags. Fail if any check is inconclusive; do not fall back to Flannel.
2. **Install CRDs.** Verify the chosen v3.33.0 CRD artifact before applying it. Wait up to 120 seconds for `installations.operator.tigera.io` (and required Calico CRDs) to report `Established`; stop on timeout or API/schema error.
3. **Install the Tigera Operator.** Verify the v3.33.0 Operator manifest and pin the Operator image digest. Apply it only after CRDs are established. Wait up to 180 seconds for the Operator deployment to become available; stop on pull, RBAC, or readiness errors.
4. **Validate and apply Installation.** Validate `k8s/calico/installation.yaml` against the pinned CRD. Preserve the pod CIDR and VXLAN selection. Use the explicit K3s CNI path overrides and `containerIPForwarding: Enabled` specified in the addendum. Do not apply if the effective runtime paths differ from those values or schema validation fails.
5. **Wait for Calico components.** Wait up to 300 seconds for `TigeraStatus/calico` to show `Available=True`, `Progressing=False`, and `Degraded=False`; also require the single-node `calico-node` DaemonSet to have all desired pods ready. Stop on timeout; do not retry indefinitely.
6. **Wait for node readiness.** After Calico is healthy, wait up to 180 seconds for the Kubernetes node to be `Ready`. Waiting before CNI installation can fail simply because no CNI is present; waiting after the Calico phase makes the condition meaningful.
7. **Verify networking and DNS.** Use a small isolated test namespace and short-lived test pods to check pod-to-pod traffic, Service routing, CoreDNS name resolution, and outbound behavior required by the application. Bound each probe and fail on unexpected results. Do not install application or monitoring workloads during this baseline test.
8. **Verify policy enforcement.** In a disposable test namespace, prove both an explicitly allowed flow and a denied flow with a temporary NetworkPolicy. Verify Calico reports healthy policy components. Keep the application NetworkPolicy disabled until actual ingress-controller and Prometheus identities and required traffic are known; keep SEC-002 open until the policy review and runtime tests pass.

The K3s quickstart uses unbounded `watch` examples for sample pods and node readiness. A bootstrap should instead use explicit deadlines and emit the failed resource/status on timeout. A timeout must leave a clear failed run, not silently proceed.

## Remaining blockers

| Blocker | Minimum resolution | Runtime evidence eventually required? |
|---|---|---|
| CNI path overrides and forwarding are configured but not runtime-verified. | Validate the rendered configuration and effective host paths/sysctls after an authorized installation. | Yes: inspect actual node paths, generated configuration, and pod/service traffic. |
| Raw CRD and Operator manifests have no published per-file SHA-256 identified in this audit. | Independently verify the signed Calico release source, review the exact files, and record reviewed hashes for those exact bytes. Do not use the legacy v1 chart checksum as a substitute for the native v3 manifest. | No cluster needed for artifact verification; runtime validation still follows. |
| Required image set and immutable digests are unknown. | Resolve the exact image list for this Installation; pin registry digests in Operator/`ImageSet` configuration. | Registry metadata validation is needed; a cluster is needed to confirm the Operator uses the intended ImageSet. |
| Bootstrap fetches the mutable `get.k3s.io` installer script directly. | Pin/review the installer content or use an approved verified k3s binary/install artifact; retain the exact release version and checksums. | Installation test is needed after source integrity is settled. |
| Target host/kernel, CNI modules, forwarding, network ranges, and resource headroom are not runtime-verified. | Collect host/route/resource evidence and confirm the intended UDP 4789 path for any multi-node deployment. | Yes. |
| No CNI or NetworkPolicy enforcement has been installed and tested. | Complete bounded component, node, DNS, pod-network, and allow/deny policy checks before application deployment. | Yes; this is the final SEC-002 deployment gate. |

## Decision

**NO-GO for DEV-003B-04B bootstrap implementation at this point.** The release versions are valid and their documented compatibility is promising; the Installation resource now contains the CNI path and forwarding corrections specified in the addendum, but their behavior requires runtime verification. Image digests, raw manifest integrity records, and target host prerequisites also remain outstanding. Complete static artifact/schema validation before planning separately authorized, isolated runtime validation. No AWS deployment is recommended at this stage.

## DEV-003B-04A-04 Research Addendum — K3s CNI Paths and IP Forwarding

**Research date:** 2026-10-17

**Scope:** Resolve the directory and forwarding configuration questions for the existing K3s/Calico candidate. This is documentation-only research; no bootstrap or infrastructure was modified, and no runtime installation was tested.

### K3s CNI directories

The repository pins K3s `v1.36.5+k3s1`, does not set a custom `--data-dir`, and uses the default K3s data root. For this K3s generation, the official K3s documentation gives these paths:

| Purpose | K3s path with the repository's default data directory | Evidence |
|---|---|---|
| CNI binaries | `/var/lib/rancher/k3s/data/cni` | K3s documents `$DATA_DIR/data/cni`, with `/var/lib/rancher/k3s/data/cni` as the default. Since October 2024, this stable path replaces the older release-hash-specific `data/$HASH/bin` path. |
| CNI configuration | `/var/lib/rancher/k3s/agent/etc/cni/net.d` | K3s deployment examples use this directory for CNI configuration. The effective runtime path should still be checked from the target K3s/containerd configuration during later runtime validation. |

Sources: [K3s Multus and IPAM documentation](https://docs.k3s.io/networking/multus-ipams), [K3s server options (`--data-dir`)](https://docs.k3s.io/cli/server), and [K3s agent options (`--data-dir`)](https://docs.k3s.io/cli/agent). If `--data-dir` is changed, the K3s-managed paths are rooted under that data directory and the Calico values must be adjusted to match. Older K3s releases used a hash-specific binary directory; the pinned 2026 release is after the documented October 2024 path change.

The [v3.33.0 CRD schema](https://raw.githubusercontent.com/projectcalico/calico/v3.33.0/manifests/v3_projectcalico_org.yaml) explicitly supports `spec.cni.binDir` and `spec.cni.confDir`; the [Tigera Operator API reference](https://docs.tigera.io/calico/latest/reference/installation/api/) describes those fields as the CNI binary and config paths. With the existing `cni.type: Calico` and default `installMode: All`, these values direct the operator's CNI installation to the runtime's directories. The schema states that the paths must match the container runtime; absent a provider-specific override, its defaults are `/opt/cni/bin` and `/etc/cni/net.d`. The schema does not document a K3s provider-specific default. The [Calico 3.33 K3s quickstart](https://docs.tigera.io/calico/latest/getting-started/kubernetes/k3s/quickstart) confirms a supported K3s installation flow but does not show explicit path overrides. Calico's [general system requirements](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements) also state the generic Kubernetes CNI directories. Those generic defaults do not match the K3s paths above, so the project should explicitly set both supported Installation fields to the K3s runtime paths instead of relying on defaults or an assumed symlink.

K3s documentation reviewed does not describe separate CNI directories for server and agent modes. The repository installs a single server node. A custom `--data-dir` or containerd configuration can change the effective paths, so a future implementation must derive or verify the target runtime paths rather than hard-code the default paths for every installation.

The proposed additive `Installation` fragment is:

```yaml
spec:
  cni:
    type: Calico
    binDir: /var/lib/rancher/k3s/data/cni
    confDir: /var/lib/rancher/k3s/agent/etc/cni/net.d
```

This is a configuration recommendation, not a claim that the operator's generated host mounts or the CNI plugin have been runtime-verified. Before applying it in a future authorized test, confirm the effective K3s/containerd paths on the target node and confirm that the pinned v3.33.0 operator writes the binaries and config into those paths. Do not add a `KubernetesProvider: K3s` value; the inspected API/schema does not document that provider value.

### Container and host IP forwarding

The v3.33.0 CRD schema supports `spec.calicoNetwork.containerIPForwarding`; it controls forwarding for containers in the generated CNI configuration and defaults to `Disabled`. K3s's [custom CNI guidance](https://docs.k3s.io/networking/basic-network-options) explicitly says the Calico CNI configuration should set `container_settings.allow_ip_forwarding` to `true`. Therefore the project Installation should explicitly set:

```yaml
spec:
  calicoNetwork:
    containerIPForwarding: Enabled
```

This container-level CNI setting is separate from host forwarding. Calico's [Felix `IPForwarding` documentation](https://docs.tigera.io/calico/latest/reference/felix/configuration) says Felix manages host sysctls for IP forwarding, that workload networking requires it, and that the default is `Enabled`. Calico's [IPv4 host requirements](https://docs.tigera.io/calico/latest/networking/ipam/ipv6) identify `net.ipv4.conf.all.forwarding=1` as the required host state for IPv4 forwarding. The host must permit Calico/Felix to establish that state. No additional host sysctl override is justified by the repository evidence; check the effective setting and Felix behavior at runtime rather than assuming the host satisfies it.

The combined proposed additions, shown separately from the existing pool and BGP settings, are:

```yaml
spec:
  cni:
    type: Calico
    binDir: /var/lib/rancher/k3s/data/cni
    confDir: /var/lib/rancher/k3s/agent/etc/cni/net.d
  calicoNetwork:
    containerIPForwarding: Enabled
```

### Compatibility and future validation

- The pinned K3s release embeds Kubernetes `1.36.5`; Calico 3.33 lists Kubernetes 1.36 as tested and publishes a K3s quickstart. The Tigera Operator v1.44.0 / Calico v3.33.0 pairing is documented in the release evidence above. This is version-level documentation evidence, not runtime testing of this exact K3s patch and host.
- The existing pod CIDR `10.44.0.0/16` matches the Calico pool; the service CIDR `10.43.0.0/16` is distinct. VXLAN remains the configured encapsulation. The K3s custom-CNI flags `--flannel-backend=none` and `--disable-network-policy` match K3s guidance for an externally managed CNI/policy engine. These settings do not establish that Calico has been installed or is enforcing policy.
- In later runtime validation, inspect the effective containerd CNI binary/config paths and the generated Calico conflist in the actual configured CNI directory. Confirm `container_settings.allow_ip_forwarding` is `true`, and confirm the host forwarding sysctl state and Calico component readiness. Then test pod/service/DNS connectivity and both permitted and denied traffic in a disposable namespace with explicit NetworkPolicies. Keep the existing application policy unchanged and do not disable or broadly bypass policy enforcement for testing.

### Resolution status

**The two configuration corrections are sufficiently specified for a future manifest/bootstrap implementation:** set the supported `binDir` and `confDir` fields to the K3s runtime paths, and set the supported `containerIPForwarding` field to `Enabled`. Static evidence supports the field names, defaults, and proposed values. Runtime validation remains required for effective host paths, generated CNI configuration, host sysctl state, pod networking, and policy enforcement.

This addendum updates only the earlier CNI-directory and container-forwarding findings: both corrections are now sufficiently specified at the static configuration level. The report's overall **NO-GO** for bootstrap implementation or execution remains because artifact integrity records, immutable image digests, target host prerequisites, and runtime validation remain outstanding. SEC-002 remains open.

## DEV-003B-04A-07 Research Addendum — Release Artifacts and Image References

**Research date:** 2026-10-17

**Scope:** Verify the release-linked files and image references for the planned K3s/Calico installation. No artifact or image was downloaded, no command or installer was executed, and no cluster operation was performed. The findings below supplement the earlier addenda; the overall bootstrap decision remains **NO-GO**.

### Preflight and intended installation path

The repository preflight was `main` at `6557a06aa681c627c333119728d43f2a6560f2cc`, with no staged or modified tracked files. `Dockerfile.distroless`, `Dockerfile.sec027`, and `Dockerfile.sec029c` were present as untracked candidates and were left untouched.

The inspected bootstrap script and Terraform EC2 bootstrap install only K3s; neither fetches nor installs Calico. For Kubernetes 1.36, the official Calico 3.33 quickstart selects the native v3 CRD manifest, then the Tigera Operator manifest, then an `Installation` custom resource. This repository supplies its own `k8s/calico/installation.yaml`, so the upstream `custom-resources.yaml` is an example and is not part of the intended installation. The upstream quickstart documents that order and the exact manifest paths: [Calico quickstart](https://docs.tigera.io/calico/latest/getting-started/kubernetes/quickstart).

| Artifact or reference | Exact source/reference | Use in this project and integrity evidence |
|---|---|---|
| K3s installer script | [`https://get.k3s.io`](https://get.k3s.io) | The script in the existing bootstrap uses this moving URL with `INSTALL_K3S_VERSION` set. The release pin constrains the selected K3s version, but does not pin or verify the installer script contents. No versioned script checksum or signature was established in this review. **Pin status:** not safely pinned as written. |
| K3s binary | [`k3s` release asset for `v1.36.5+k3s1`](https://github.com/k3s-io/k3s/releases/download/v1.36.5%2Bk3s1/k3s) | The official [K3s release asset listing](https://github.com/k3s-io/k3s/releases/expanded_assets/v1.36.5%2Bk3s1) lists SHA-256 `d73847bcd3c5fccef0115b372e2f9a91f3032dc84bbf71518a4617565294d313` for the `k3s` binary. This hash applies to that binary only. Select the matching release asset and checksum for the target architecture. **Pin status:** can be pinned after target architecture is fixed and the downloaded binary is checked against this release evidence. |
| K3s release checksum list | [`sha256sum-amd64.txt` for `v1.36.5+k3s1`](https://github.com/k3s-io/k3s/releases/download/v1.36.5%2Bk3s1/sha256sum-amd64.txt) | The exact official release asset exists. The release installer source uses an architecture-specific checksum list to verify the binary. This research did not retrieve or inspect the file contents; the binary hash above was read from the official GitHub release asset listing. **Pin status:** not ready until the matching architecture's list contents are reviewed, or the binary is pinned against the independently reviewed asset SHA-256. |
| Native v3 Calico CRDs | [`v3_projectcalico_org.yaml` at Calico `v3.33.0`](https://raw.githubusercontent.com/projectcalico/calico/v3.33.0/manifests/v3_projectcalico_org.yaml) | Required by the documented Kubernetes 1.36+ installation path. The Calico `v3.33.0` release page reports a GitHub-verified signed tag/commit, but no standalone published SHA-256 for this raw YAML was found. **Pin status:** can be pinned only after independently validating the signed source, reviewing the exact file, and recording a separately reviewed hash. |
| Tigera Operator manifest | [`tigera-operator.yaml` at Calico `v3.33.0`](https://raw.githubusercontent.com/projectcalico/calico/v3.33.0/manifests/tigera-operator.yaml) | Required by the documented manifest path. It explicitly references `quay.io/tigera/operator:v1.44.0`. The source tag has the same GitHub-verified signature evidence; no standalone SHA-256 for this raw YAML was found. **Pin status:** same conditional source-verification and file-hash requirement as the CRD manifest. |
| Project Installation resource | [`k8s/calico/installation.yaml`](../k8s/calico/installation.yaml) | Local project configuration; it is not an upstream download. It configures Calico CNI and contains the previously reviewed CIDR, VXLAN, CNI directory, forwarding, and BGP settings. Its correctness still requires validation against the pinned schema and later runtime verification. **Pin status:** pin to a reviewed repository commit and validate against the verified CRD. |
| Upstream custom-resource example | [`custom-resources.yaml` at Calico `v3.33.0`](https://raw.githubusercontent.com/projectcalico/calico/v3.33.0/manifests/custom-resources.yaml) | Not required by this project's path because the local Installation resource is used. No standalone file checksum was found. Do not apply the upstream sample as a substitute for the project resource. **Pin status:** not applicable to the intended installation. |
| Optional Helm artifacts | [Official Calico Helm chart repository](https://docs.tigera.io/calico/charts); chart references `projectcalico/tigera-operator` and, for the native v3 CRDs, `projectcalico.org.v3`, version `v3.33.0` | The repository bootstrap does not invoke Helm; this is an alternative installation path, not an additional requirement for the manifest path. The Calico release also names `tigera-operator-v3.33.0.tgz` and the tech-preview `projectcalico.org.v3-v3.33.0.tgz`. No artifact-specific checksum for these exact chart packages was verified in the sources reviewed. The previously listed `crd.projectcalico.org.v1-v3.33.0.tgz` SHA-256 (`bbb9643633609941ef2a00b400798b2967a348d55ad8d1e20bd9f61c3ec3c73f`) is for that legacy v1 chart archive only; it is not evidence for the native v3 manifest or chart. **Pin status:** not applicable unless the project deliberately selects the Helm route; then pin and verify the exact package separately. |

The release source evidence is [Calico `v3.33.0`](https://github.com/projectcalico/calico/releases/tag/v3.33.0), [Tigera Operator `v1.44.0`](https://github.com/tigera/operator/releases/tag/v1.44.0), and [K3s `v1.36.5+k3s1`](https://github.com/k3s-io/k3s/releases/tag/v1.36.5%2Bk3s1). GitHub marks the Calico tag/commit and Operator release commit as verified signatures in its release pages. This is upstream signature evidence, not an independent local verification of signer identity or file bytes. The K3s release page and asset listing establish its release and binary hash; no signed tag or artifact provenance record was independently established here.

### Container image references

The [Calico 3.33 component-version table](https://docs.tigera.io/calico/latest/reference/component-versions), [official registry guidance](https://docs.tigera.io/calico/latest/operations/image-options/alternate-registry), and [3.33 upgrade notes](https://docs.tigera.io/calico/latest/operations/upgrading/upgrade-notes) establish versioned image references and the 3.33 image consolidation. The raw Operator manifest is the only inspected static workload manifest that fixes an image reference directly.

| Image reference | Evidence and applicability | Immutable digest |
|---|---|---|
| `quay.io/tigera/operator:v1.44.0` | Explicit in the release-tagged Operator Deployment. Its environment also specifies init-image version `v1.44.0`, but the static manifest does not enumerate every image later rendered by the Operator. | No digest independently verified for this release and registry. |
| `quay.io/calico/calico:v3.33.0` | Listed by Tigera's 3.33 registry guidance. The 3.33 upgrade notes say many former component images (including separate CNI and kube-controller images) are consolidated into the combined `calico/calico` image. | No digest independently verified. |
| `quay.io/calico/node:v3.33.0` | Listed by Tigera's 3.33 registry guidance and component-version documentation; it remains a separate published image. It is expected for node networking, but the exact rendered workload image set was not inspected from an Operator execution. | No digest independently verified. |
| `quay.io/calico/whisker:v3.33.0`, `quay.io/calico/envoy-gateway:v3.33.0`, `quay.io/calico/envoy-proxy:v3.33.0`, `quay.io/calico/envoy-ratelimit:v3.33.0` | Tigera's image guidance lists these release-tagged images for feature-enabled deployments. The local Installation file does not by itself prove that these optional API, flow-visibility, or gateway components are enabled or required. | No digest independently verified. |

Do not infer that the Operator manifest's single explicit image is the full set. The Operator creates the CNI and networking workloads from the `Installation` and enabled features, so the exact init-container and workload references must be captured from the pinned Operator's effective image list and/or reviewed rendered resources. Calico's [ImageSet guide](https://docs.tigera.io/calico/latest/operations/image-options/imageset) explains digest pinning and lists `--print-images=list` as a way to obtain the effective list. Its sample digest strings are placeholders, and the guide also contains a generic image-list example that should not be copied without reconciling it against the v3.33 single-image release notes. No image was pulled or inspected for this research. No immutable Calico or Operator image digest is verified here.

### Integrity procedure and remaining unknowns

For a future implementation, use a reviewed, fail-closed inventory:

1. Pin the exact K3s, Calico, and Operator versions and architecture. Prefer the versioned K3s binary asset with its matching official release checksum; verify the binary before installation. Either pin and verify the installer script separately or avoid executing the mutable `get.k3s.io` script by using a reviewed installation procedure for the verified binary.
2. For each raw Calico manifest, resolve the release tag to its full commit, verify the signed tag/commit against a trusted key whose fingerprint is established independently, and confirm each file comes from that commit. Review the YAML, then record a locally computed SHA-256 for the exact bytes as a separately reviewed project pin. A local hash is a project-controlled integrity pin; it must not be described as an upstream-published checksum.
3. If choosing Helm instead, pin the exact chart name and version and verify the checksum against that exact package from trusted, versioned repository metadata or the release asset. Do not transfer the legacy v1 chart hash to the native v3 chart, a raw manifest, or another archive.
4. Resolve the actual image set for this exact Installation and Operator release. Verify registry digests for the exact registry references and platform, record them in reviewed configuration (for example, an appropriately populated `ImageSet`), and fail if any expected digest or reference is unavailable or differs. Do not use tags alone as an immutable pin and do not copy documentation example digests.
5. At bootstrap time, verify all files and image pins before applying anything. Missing, mismatched, or unverifiable inputs must stop the run; there must be no remote `kubectl apply` of unverified YAML and no silent version, registry, or CNI fallback.

Still unresolved are the full pinned commit SHAs and local verification of the signed Calico/Operator sources; standalone hashes for the exact raw Calico manifests; whether an upstream checksum or signature exists for each exact Helm package; the effective image set and immutable digests for the project's Installation; and a pinned integrity mechanism for the K3s installer script if that script remains in use. Runtime CNI/network-policy validation and target-host prerequisites remain separate blockers described above. No exact k3s/Calico runtime pairing has been tested.

### Decision

**NO-GO for implementing or executing the Calico bootstrap.** The official releases and version pairing are established, and the exact K3s binary SHA-256 is visible in the official release asset listing. However, the manifest-path raw files still lack separately verified file hashes, the current installer script is mutable, and the exact Operator-rendered image set and immutable image digests have not been established. The legacy v1 CRD chart checksum does not close the native-v3 manifest integrity gap. Resolve those static pins and review them before implementation; later authorized runtime validation is still required. SEC-002 remains open and no infrastructure has been deployed.

## DEV-003B-04A-09 — Offline Verification of the Calico v3.33.0 Manifests

The two expected manifest files for the planned Kubernetes 1.36+ manifest installation are:

| Local filename | Versioned upstream source | Purpose and version relationship |
|---|---|---|
| `v3_projectcalico_org.yaml` | [Calico `v3.33.0` CRD manifest](https://raw.githubusercontent.com/projectcalico/calico/v3.33.0/manifests/v3_projectcalico_org.yaml) | Native `projectcalico.org/v3` CRDs for Calico `v3.33.0`. |
| `tigera-operator.yaml` | [Calico `v3.33.0` Tigera Operator manifest](https://raw.githubusercontent.com/projectcalico/calico/v3.33.0/manifests/tigera-operator.yaml) | Operator manifest distributed with the Calico `v3.33.0` release; it references `quay.io/tigera/operator:v1.44.0`, the Operator version listed for Calico 3.33. |

The [official Calico quickstart](https://docs.tigera.io/calico/latest/getting-started/kubernetes/quickstart) names these exact URLs and uses the native v3 CRD manifest for Kubernetes 1.36 or later, followed by the Tigera Operator manifest. The URLs are pinned to the Calico `v3.33.0` Git tag rather than a mutable branch. This release-tag association identifies the intended source location; a Git tag by itself does not prove artifact authenticity. The Operator version relationship is also listed in the [Calico 3.33 component versions](https://docs.tigera.io/calico/latest/reference/component-versions).

### Required review and approval

Before future bootstrap use, obtain the two files through an independently reviewed acquisition process and place only those exact files in a dedicated local directory. For each file, reviewers must validate the release source and relevant signature/provenance evidence using a trusted key or other independently established trust path, inspect the exact bytes, and separately approve a SHA-256 value. Record the filename, full source commit SHA, approved hash, review date, approver, and evidence. These are **reviewed project-local pins**, not upstream-published checksums; no checksum is supplied or fabricated here. Do not approve a value solely because it was calculated from a file fetched from the same unauthenticated source.

### Local fail-closed check

After both files and their separately approved hashes are available locally, run the following in Bash on macOS. Replace both checksum placeholders only with values from the approved review record. The block makes no network requests and does not execute, install, or apply either manifest. It rejects missing files, symlinks, missing or malformed checksum values, mismatches, and any extra directory entry (including hidden entries).

```bash
set -euo pipefail

artifact_dir="./calico-v3.33.0-reviewed"
crd_file="$artifact_dir/v3_projectcalico_org.yaml"
operator_file="$artifact_dir/tigera-operator.yaml"
expected_crd_sha256="REPLACE_WITH_SEPARATELY_APPROVED_SHA256"
expected_operator_sha256="REPLACE_WITH_SEPARATELY_APPROVED_SHA256"

[[ -d "$artifact_dir" && ! -L "$artifact_dir" ]] || {
  printf '%s\n' "Missing or invalid artifact directory" >&2
  exit 1
}
[[ -f "$crd_file" && ! -L "$crd_file" ]] || {
  printf '%s\n' "Missing or invalid CRD manifest" >&2
  exit 1
}
[[ -f "$operator_file" && ! -L "$operator_file" ]] || {
  printf '%s\n' "Missing or invalid Operator manifest" >&2
  exit 1
}

shopt -s dotglob nullglob
inputs=("$artifact_dir"/*)
[[ ${#inputs[@]} -eq 2 ]] || {
  printf '%s\n' "Unexpected or missing manifest inputs" >&2
  exit 1
}
for input in "${inputs[@]}"; do
  case "$input" in
    "$crd_file"|"$operator_file") ;;
    *) printf '%s\n' "Unexpected manifest input: ${input##*/}" >&2; exit 1 ;;
  esac
done

check_sha256() {
  local file="$1" expected="$2" actual
  [[ "$expected" =~ ^[[:xdigit:]]{64}$ ]] || {
    printf '%s\n' "Missing or malformed approved SHA-256 for ${file##*/}" >&2
    return 1
  }
  expected=$(printf '%s' "$expected" | tr '[:upper:]' '[:lower:]')
  actual=$(shasum -a 256 "$file" | awk '{ print tolower($1) }')
  [[ "$actual" == "$expected" ]] || {
    printf '%s\n' "SHA-256 mismatch for ${file##*/}" >&2
    return 1
  }
}

check_sha256 "$crd_file" "$expected_crd_sha256"
check_sha256 "$operator_file" "$expected_operator_sha256"
printf '%s\n' "Both reviewed manifest hashes match"
```

The directory comparison requires exactly the two named inputs; it does not accept another manifest as an implicit substitute. A successful local comparison confirms that the files match the approved local values, not that the approval process or upstream signer was trustworthy. Keep installation blocked unless the source/signature review and both independent approvals are complete. The previously documented image digest, host prerequisite, CNI, and runtime-validation blockers remain unresolved, so this procedure does not change the overall **NO-GO** bootstrap recommendation. SEC-002 remains open.
