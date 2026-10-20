# Manual GHCR Publication Design — Not Active

This document describes a future release process. It does not enable publication, authorize a release, or assert that a CloudOps image exists in GHCR. The active workflow has no `workflow_dispatch` trigger; its image handoff steps and `publish` job remain guarded by `if: false`. Keep GHCR publishing disabled until a separate review approves an implementation and the repository controls below are configured. **SEC-002 remains OPEN; K3s/Calico remains NO-GO.**

## Current CI boundaries

The current `.github/workflows/ci.yml` runs the `test` job on pushes to `main` and pull requests. It installs the project requirements, runs Ruff and pytest, then runs Gitleaks with comments, artifact upload, and summary disabled. GitHub Actions are pinned to full commit SHAs. The workflow grants `contents: read` globally and scopes the test and image jobs to `contents: read`.

For a push to `main`, the `image` job requires `test` to succeed. It checks out the source, builds the default production `Dockerfile` from context `.`, loads the image into the runner as `cloudops-platform:<commit SHA>`, and runs Trivy with `CRITICAL,HIGH` severities and `exit-code: 1`.

The build job has three disabled handoff steps: export the scanned image, calculate a SHA-256 checksum of the tar archive, and upload the archive plus checksum. The `publish` job depends on both `test` and `image`, but its condition also ends with `false`. Its currently dormant steps would download and verify the archive, load and tag the same image as `ghcr.io/<lowercase-owner>/cloudops-platform:sha-<commit SHA>`, authenticate using `GITHUB_TOKEN`, push, parse the registry digest, expose it as a job output, and print the digest-qualified image reference in the run summary. There are no separate image publication scripts.

The archive checksum protects the handoff bytes; it is not the OCI image digest and does not establish source authenticity or build provenance. The current workflow does not explicitly generate or persist an SBOM or provenance for the published digest, and it does not sign or verify a published image. The publish job and artifact handoff have not run, so no registry digest or image artifact is established.

## Repository controls required before activation

Configure and verify these settings manually; this audit does not establish their current state:

1. Protect `main` with required pull request review and required CI checks, including the test and image security gates. Restrict bypass and force-push permissions, and require review for workflow and release-policy changes.
2. Create a protected GitHub environment such as `ghcr-publication`, restrict deployments to `main`, and require designated reviewers. Enable prevention of self-review where available. If required reviewers are unavailable for the repository plan or visibility, do not treat a comment or workflow input as equivalent approval; define and verify an alternate release approval control first.
3. Confirm GHCR package ownership, visibility, and repository access settings. Start with the package private and restrict access to the repository and approved consumers; do not make it public until digest and supply-chain evidence have been verified and a separate release approval is recorded. Permit the repository `GITHUB_TOKEN` to publish only to the intended package. Do not create or store a personal access token for this flow.
4. Restrict who can manually dispatch the future release workflow and review which users can approve its protected environment.

## Proposed manual release flow

Implement this only in a separately reviewed future change. Prefer a dedicated release workflow triggered only by `workflow_dispatch`; leave the ordinary push and pull request CI workflow unable to publish.

1. The operator selects the protected `main` workflow ref and supplies one reviewed source commit SHA as a required input. Reject malformed or abbreviated values; accept only a full 40-character hexadecimal SHA.
2. Resolve the commit from this repository, verify it is reachable from protected `main`, check out that exact SHA, and assert that `git rev-parse HEAD` equals the input. Reject commits from unmerged pull requests, unreviewed refs, or any mismatch. Never silently substitute the current branch head.
3. Run Ruff, pytest, and Gitleaks against that exact checkout. Build the production Dockerfile once, tag the local image with the exact commit SHA, and require the configured Trivy HIGH/CRITICAL gate to pass. A publish job must depend on every required check and must independently verify the source SHA recorded by its prerequisite jobs.
4. Scan the built image, export that same image, calculate a strong archive checksum, and hand it between jobs within the same workflow run. Verify the checksum before loading it. Do not rebuild or substitute an image in the publish job.
5. Require approval through the protected environment before the publish job starts. Make its condition require `workflow_dispatch`, the protected `main` workflow ref, the validated requested SHA, and successful prerequisite jobs. Ordinary pushes and pull requests must never satisfy the publish condition.
6. Give test and build jobs only `contents: read`. Give the publish job only `contents: read` and `packages: write`; use the repository-scoped `GITHUB_TOKEN` with `docker login --password-stdin`. Do not use a broad PAT. Add `id-token: write` or `attestations: write` only to the job that needs them for signing or attestations.
7. Push the exact scanned archive under a commit-specific tag, capture the registry's returned digest, validate its `sha256:<64 hex>` form, and resolve the tag from GHCR to confirm it points to that same digest. Record the source SHA, workflow run URL, scan result, SBOM/provenance references, and `ghcr.io/<owner>/<image>@sha256:<digest>` in the run summary. Treat the tag as mutable and use the digest-qualified reference for all later consumers.
8. Generate and attach the supply-chain evidence below to the final digest. Keep the package private while doing this. Mark the image approved for future consumption only after the signature/attestation identity and digest have been verified. If post-push evidence generation or verification fails, report the package as unapproved, keep it restricted, and do not use it for deployment.

## Supply-chain controls

| Control | Required for the first approved publication | Later improvement |
|---|---|---|
| Dependency integrity | Platform-specific runtime and development locks now pin direct and transitive packages with SHA-256 hashes. Docker and CI install those locks with `--require-hashes`; production also requires binary wheels. Target-specific Alpine amd64/Python 3.13.16 and Ubuntu 24.04/Python 3.13.16 installs were verified. Hashes prove consistency with approved values, not publisher authenticity. | Review lock refreshes and transitive changes, and retain scheduled vulnerability review. |
| SBOM | Generate an SBOM from the exact image that passed Trivy and bind it to the final registry digest. Retain it as a registry-attached artifact or a clearly linked, access-controlled workflow artifact. Confirm the chosen exporter survives the image handoff; do not assume `docker save` preserves BuildKit attestations. | Add continuous SBOM refresh and dependency monitoring. |
| Build provenance | Create provenance linking the image digest to the full source SHA, production Dockerfile, pinned base image digest, dependency inputs, workflow identity, and run. Verify the provenance subject equals the GHCR digest. | Enforce provenance verification in future deployment or admission policy. |
| Image signature | Sign the final digest using a short-lived GitHub OIDC identity scoped to the approved workflow, then verify the signature against the expected repository, workflow, ref, and digest before declaring the image approved. Avoid long-lived signing keys. | Enforce signature verification at cluster admission after a separately authorized cluster deployment is considered. |
| Registry digest | Capture the digest returned by GHCR and independently resolve the pushed tag to confirm the same manifest digest. Publish and consume only `image@sha256:<digest>`; a `sha-<commit>` tag alone is not immutable. | Add multi-architecture manifest verification if multi-platform images are introduced. |

SBOM, provenance, and signature tooling should be chosen together with the artifact transport so each item identifies the exact final digest. A successful source scan or archive checksum alone does not prove the published image's identity.

## Activation checklist

- The repository and environment approval settings above have been verified.
- The source SHA is reviewed, protected, and checked out exactly.
- Test, Gitleaks, image build, and Trivy checks all pass for that SHA.
- The image handed off to publishing is byte-for-byte the image that was scanned.
- Dependency hashes, SBOM, and provenance are present and tied to the final digest.
- The digest is resolved from GHCR, signed, verified, and recorded before the image is treated as approved.
- Pull requests and ordinary pushes cannot reach the publish job.

Until these conditions are implemented and separately approved, publication remains disabled. This design does not resolve SEC-002 or authorize Kubernetes deployment; keep SEC-002 OPEN and K3s/Calico NO-GO.
