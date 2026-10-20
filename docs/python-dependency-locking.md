# Python Dependency Locking Plan — Not Implemented

This document plans a future dependency-locking change. DEV-030 adds offline checks and documentation only: it does not generate lockfiles, hashes, or change dependency versions. The current Docker build and CI commands remain unchanged. **SEC-002 remains OPEN; K3s/Calico remains NO-GO.**

## Current dependency files

- `requirements-runtime.txt` contains the five direct application requirements: FastAPI, Starlette, Uvicorn with its `standard` extra, `prometheus-client`, and `pydantic-settings`. Each currently uses `==` with an exact version.
- `requirements.txt` repeats those five runtime requirements and adds `httpx`, `pytest`, and `ruff` for tests and CI. Its runtime declarations currently match `requirements-runtime.txt`.
- `pyproject.toml` configures pytest and Ruff; it does not declare project dependencies or a Python requirement.
- The production `Dockerfile` uses the digest-pinned `python:3.13.16-alpine3.24` image and installs `requirements-runtime.txt` with `--only-binary=:all:`.
- `.github/workflows/ci.yml` selects Python `3.13` and installs `requirements.txt` before Ruff and pytest.

These are direct-dependency lists, not complete locks. They do not pin transitive package versions or list expected package hashes. Neither installer enables `pip --require-hashes`. A later resolution can therefore choose different transitive versions or package artifacts while the direct pins remain unchanged. The current offline tests check declaration structure and file wiring; they do not claim that hash verification is enabled.

## Proposed pip-based layout

For a separately reviewed implementation, use direct-input files and ordinary pip-compatible generated lock files:

| File | Purpose |
|---|---|
| `requirements-runtime.in` | Canonical direct runtime requirements, moved from the current runtime list. |
| `requirements-dev.in` | Test and lint requirements plus the runtime input. |
| `requirements-runtime.lock` | Generated full runtime dependency graph with exact versions and SHA-256 hashes. |
| `requirements-dev.lock` | Generated CI/test graph with exact versions and hashes; constrain shared runtime packages to the runtime lock. |

Use a pinned `pip-tools` version only as a lock generator, for example `pip-compile --generate-hashes`. It emits standard requirements syntax; installation remains ordinary pip. Generate and commit the lock outputs from reviewed inputs, not by hand. The runtime and development locks must agree on every shared runtime package version. The CI and Dockerfile path changes belong to DEV-031, not this task.

Install with hash checking enabled:

```sh
python -m pip install --require-hashes -r requirements-dev.lock
```

```dockerfile
RUN pip install --require-hashes --only-binary=:all: --no-cache-dir -r requirements-runtime.lock
```

With `--require-hashes`, pip requires every dependency in the resolved graph to be exactly pinned and hashed; partial coverage is rejected. Include SHA-256 hashes for the package archives allowed on each supported target. A hash confirms that a downloaded artifact matches the approved value in the lock. It does not prove that the original publisher or source was trustworthy. Review the package identity, version, release source, and proposed hashes independently before approving a lock update. See [pip hash-checking guidance](https://pip.pypa.io/en/stable/topics/secure-installs/) and the [`pip-compile` hash-generation option](https://pip-tools.pypa.io/en/stable/reference/pip-compile/).

## Python and platform compatibility

Keep the supported interpreter explicit at Python 3.13. Generate and install locks using the Python minor version used by CI and the production image; record the exact patch version used to generate and validate each lock. CI currently requests Python `3.13`, while the production base pins Python 3.13.16. DEV-031 should confirm that the selected lock-generation and runtime packages support Python 3.13 and that CI and production resolve compatible shared versions.

The production target is Linux amd64 on Alpine, which uses musl rather than glibc. Linux wheels tagged `manylinux` target glibc; Alpine needs compatible `musllinux` wheels or platform-independent wheels. The `--only-binary=:all:` restriction must remain, and the production build must fail if any locked runtime dependency lacks an allowed wheel. See [PEP 656](https://peps.python.org/pep-0656/) for the musllinux platform tags.

A lock resolved only on macOS is insufficient evidence for the production image. macOS selects different wheels and can apply different environment markers than Linux amd64 on musl. Generate or validate runtime hashes in an environment that matches the pinned Python, Linux architecture, and Alpine/musl target. If CI also installs the development lock on Ubuntu, include and review hashes for the allowed Ubuntu artifacts too, or maintain appropriately scoped locks. Confirm shared package versions remain consistent across locks.

## Controlled dependency updates

1. Update only the intended direct requirement in the `.in` input and record why the version is changing.
2. Use the pinned lock generator in a clean, documented Python 3.13 environment to resolve the complete dependency graph and regenerate the affected locks with SHA-256 hashes. Do not copy hashes from an unrelated platform or invent values.
3. Review the direct and transitive package names, versions, source URLs, wheel tags, and hash changes. Confirm every runtime dependency has an approved hash for the production target and every requirement remains pinned.
4. Run hash-required installation and the test suite for CI's platform. Build the production image using the Alpine/musllinux runtime lock and retain binary-only installation. Run the existing image vulnerability scan before treating the update as approved.
5. Keep a focused lockfile diff and update dependency documentation when the supported Python or platform scope changes. Do not silently refresh all dependencies as part of an unrelated code change.

## DEV-031 boundary and rollback

DEV-031 will need to resolve transitive dependencies, obtain genuine artifact hashes, and install those artifacts. These actions require package-index/network access and package downloads. Confirming Alpine compatibility requires a production-platform dependency installation, which requires an image build and its package downloads. Updating the Dockerfile, CI references, tests, and documentation is source work, but offline checks alone cannot prove that the selected wheels install or that the built image passes Trivy.

DEV-030 can complete static requirement parsing, assertions about file wiring, documentation, Ruff, and pytest without package downloads, Docker builds, or cluster access. No resolver, lock, artifact, or image validation is run here.

If a future locked build or security check fails, do not disable `--require-hashes`, remove `--only-binary=:all:`, or publish the image. Keep publication disabled, preserve the failing lock diff and logs, then revert the lock inputs, outputs, Dockerfile, and CI references together to the last reviewed commit. The rollback restores the current unlocked behavior and must not be represented as reproducible; correct the lock in a new reviewed change before retrying.
