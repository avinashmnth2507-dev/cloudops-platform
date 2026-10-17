#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$REPOSITORY_ROOT"

for required_tool in .venv/bin/ruff .venv/bin/pytest .venv/bin/python; do
  if [[ ! -x "$required_tool" ]]; then
    printf 'Local verification requires existing executable %s; no tools were installed.\n' \
      "$required_tool" >&2
    exit 1
  fi
done

VERIFY_TEMP_ROOT="$(mktemp -d "$REPOSITORY_ROOT/.verify-local.XXXXXXXX")"
cleanup() {
  local exit_code=$?
  trap - EXIT
  if [[ -n "${VERIFY_TEMP_ROOT:-}" && -d "$VERIFY_TEMP_ROOT" && ! -L "$VERIFY_TEMP_ROOT" &&
    "$VERIFY_TEMP_ROOT" == "$REPOSITORY_ROOT"/.verify-local.* ]]; then
    if ! rm -rf "$VERIFY_TEMP_ROOT"; then
      printf 'Could not remove local verification temporary directory: %s\n' \
        "$VERIFY_TEMP_ROOT" >&2
      exit_code=1
    fi
  else
    printf '%s\n' 'Local verification temporary path failed its safety check.' >&2
    exit_code=1
  fi
  exit "$exit_code"
}
trap cleanup EXIT

mkdir -p "$VERIFY_TEMP_ROOT/tmp" "$VERIFY_TEMP_ROOT/helm-cache" \
  "$VERIFY_TEMP_ROOT/helm-config" "$VERIFY_TEMP_ROOT/helm-data" \
  "$VERIFY_TEMP_ROOT/ruff-cache" "$VERIFY_TEMP_ROOT/xdg-cache"
export TMPDIR="$VERIFY_TEMP_ROOT/tmp"
export HELM_CACHE_HOME="$VERIFY_TEMP_ROOT/helm-cache"
export HELM_CONFIG_HOME="$VERIFY_TEMP_ROOT/helm-config"
export HELM_DATA_HOME="$VERIFY_TEMP_ROOT/helm-data"
export RUFF_CACHE_DIR="$VERIFY_TEMP_ROOT/ruff-cache"
export XDG_CACHE_HOME="$VERIFY_TEMP_ROOT/xdg-cache"
export PYTHONDONTWRITEBYTECODE=1

# Test-only, syntactically valid reference at a reserved invalid registry domain.
# It is used only for offline chart lint/render checks; it is not a real image.
HELM_TEST_IMAGE_REFERENCE='registry.example.invalid/cloudops-platform@sha256:0000000000000000000000000000000000000000000000000000000000000000'

printf '%s\n' 'Running Ruff...'
.venv/bin/ruff check .

printf '%s\n' 'Running pytest...'
.venv/bin/pytest -q -p no:cacheprovider --basetemp "$VERIFY_TEMP_ROOT/pytest"

printf '%s\n' 'Checking bootstrap and developer shell syntax...'
for script in scripts/bootstrap-calico.sh scripts/bootstrap-k3s.sh scripts/verify-local.sh; do
  bash -n "$script"
done

if command -v helm >/dev/null 2>&1; then
  printf '%s\n' 'Running local Helm lint and template rendering with the test-only digest fixture...'
  helm lint helm/cloudops --set-string "image.reference=$HELM_TEST_IMAGE_REFERENCE"
  helm template cloudops helm/cloudops \
    --set-string "image.reference=$HELM_TEST_IMAGE_REFERENCE" >/dev/null
else
  printf '%s\n' 'SKIP: Helm CLI is unavailable; install nothing for this check.'
fi

if command -v terraform >/dev/null 2>&1; then
  printf '%s\n' 'Checking Terraform formatting without initialization...'
  terraform fmt -check -recursive terraform
else
  printf '%s\n' 'SKIP: Terraform CLI is unavailable; install nothing for this check.'
fi

printf '%s\n' 'Local verification completed.'
