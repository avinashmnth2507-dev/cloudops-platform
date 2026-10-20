# Python Dependency Locking Plan — Not Implemented

Dependency locking is not yet implemented. Production and CI continue using their existing requirements files.

The canonical `.in` inputs added for future lock generation do not change installation behavior. No dependency lockfiles, resolved transitive versions, or package hashes have been generated. **SEC-002 remains OPEN; K3s/Calico remains NO-GO.**

## Current dependency files

| File | Current or planned purpose |
|---|---|
| `requirements-runtime.in` | Canonical direct runtime declarations for a future runtime lock. |
| `requirements-dev.in` | Canonical development declarations; includes `requirements-runtime.in` plus the existing test and lint dependencies. |
| `requirements-runtime.txt` | Active production dependency input used by the Dockerfile. |
| `requirements.txt` | Active combined development/CI dependency input used by GitHub Actions. |
| `requirements-runtime-alpine-py313-amd64.lock` | Proposed full runtime lock for the production platform; not created. |
| `requirements-dev-ubuntu-py313.lock` | Proposed full development lock for CI; not created. |

The canonical runtime input currently contains:

```text
fastapi==0.133.0
starlette==1.3.1
uvicorn[standard]==0.36.0
prometheus-client==0.23.1
pydantic-settings==2.11.0
```

The canonical development input contains:

```text
-r requirements-runtime.in
httpx==0.28.1
pytest==8.4.2
ruff==0.13.2
```

The two active `.txt` files remain unchanged. The production Dockerfile installs `requirements-runtime.txt` with `--only-binary=:all:`. CI selects Python `3.13` on `ubuntu-latest` and installs `requirements.txt`. The runtime declarations in the current active files match. These active inputs pin direct dependencies only; they do not lock transitive versions or require package hashes.

## Proposed platform-specific locks

Use separate pip requirements-format lockfiles:

- `requirements-runtime-alpine-py313-amd64.lock` for Python `3.13.16`, Linux amd64, Alpine `3.24`, and musl, matching the production Docker base image.
- `requirements-dev-ubuntu-py313.lock` for the Ubuntu CI environment and Python `3.13`. Before implementation, pin CI to a reviewed Python patch version compatible with production and a stable Ubuntu runner release, or explicitly validate the chosen versions.

Do not assume one lock can safely cover Alpine and Ubuntu. A shared file can theoretically carry hashes for artifacts from multiple platforms, but marker-dependent dependency graphs and distinct musl/glibc wheels must be accounted for. Generate and validate each lock on its target platform, then compare the shared runtime package versions. If a package cannot use the same version on both targets, review and document that difference before adopting the locks.

Use a reviewed, pinned `pip-tools` version only as the lock generator. Generate the complete graph and hashes in matching Linux environments, for example:

```sh
pip-compile --generate-hashes --output-file requirements-runtime-alpine-py313-amd64.lock requirements-runtime.in
pip-compile --generate-hashes --output-file requirements-dev-ubuntu-py313.lock requirements-dev.in
```

These commands are future instructions only; they were not run for this change. The generator version and exact Python/platform environment must be recorded when locks are created. Do not generate either lock from macOS and treat it as production evidence.

Install a generated lock with hash enforcement:

```sh
python -m pip install --require-hashes -r requirements-dev-ubuntu-py313.lock
```

The future production install should retain the existing binary-only constraint and add hash checking:

```dockerfile
RUN pip install --require-hashes --only-binary=:all: --no-cache-dir -r requirements-runtime-alpine-py313-amd64.lock
```

`--require-hashes` requires exact pins and hashes throughout the dependency graph. Review that every transitive package is present, every allowed artifact has a genuine SHA-256 hash, and no unpinned dependency or extra index/source directive remains. Hashes show that an artifact matches its approved hash; they do not establish that the original package publisher is trustworthy. Review package identity, version, provenance, and artifact selection independently. See [pip hash-checking guidance](https://pip.pypa.io/en/stable/topics/secure-installs/) and the [`pip-compile` hash option](https://pip-tools.readthedocs.io/en/stable/).

## Compatibility and verification

Production uses the digest-pinned Python `3.13.16` Alpine `3.24` base image for Linux amd64. Alpine uses musl; CI runs on Ubuntu, which uses glibc. Linux `manylinux` wheels target glibc, while Alpine requires compatible `musllinux` wheels or platform-independent wheels. Keep `--only-binary=:all:` in production so a missing compatible wheel fails the build instead of silently compiling a source distribution. See [PEP 656](https://peps.python.org/pep-0656/) for musllinux tags.

MacOS dependency resolution is insufficient for the production lock: macOS selects different wheel artifacts and can evaluate environment markers differently. Generate or verify the runtime lock using the exact production Python, Linux architecture, Alpine/musl base, and package installer behavior. Verify that every selected runtime artifact is a compatible wheel and that its SHA-256 is included. Verify the development lock separately on the pinned Ubuntu/Python target. Compare shared runtime versions across both outputs and retain the generator and platform details with the review evidence.

The offline tests can verify direct input declarations, exact current versions, safe requirement syntax, and that Docker and CI still use their existing files. They cannot prove transitive resolution, wheel availability, artifact hashes, or installation success. Those require package metadata/artifact access and target-platform installation.

## Controlled update and rollback

1. Change only the intended direct dependency declaration and record the reason.
2. In the matching target environments, run the reviewed and pinned lock generator to resolve all transitive dependencies and generate SHA-256 hashes. Do not handwrite or copy hashes from another platform.
3. Review package names, direct and transitive versions, environment markers, wheel tags, artifact sources, and all hash additions/removals. Confirm the shared runtime versions agree where expected.
4. Install the development lock with `--require-hashes` on CI’s Ubuntu/Python target. Build the production image using the Alpine runtime lock while retaining `--only-binary=:all:`. Run the existing tests and image vulnerability scan.
5. Update Dockerfile and CI lock references only after the locks pass target-specific validation. Preserve the current `.txt` install path until that change is reviewed and validated.

Package-index access and downloads are required to resolve dependencies and obtain package artifacts. Production compatibility validation requires a Docker build using the pinned Alpine base and downloaded wheels. These actions need separate authorization; they are not part of this documentation and input-preparation change.

If a future locked installation or image build fails, keep the failure logs and lock diff, do not disable `--require-hashes` or `--only-binary=:all:`, and do not publish an image. Revert the lock inputs, generated locks, Dockerfile, CI references, and related tests together to the last reviewed state. The rollback restores the existing unlocked behavior and must not be described as reproducible; correct and revalidate the locks in a new reviewed change.
