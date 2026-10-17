#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf '%s\n' \
    "Usage: $0 --validate-only | --apply" \
    "Requires CALICO_ARTIFACT_DIR, KUBE_CONTEXT, APPROVED_CRD_SHA256, and APPROVED_OPERATOR_SHA256." >&2
}

fail() {
  printf 'Calico bootstrap: %s\n' "$1" >&2
  exit 1
}

if [[ $# -ne 1 || ( "$1" != '--validate-only' && "$1" != '--apply' ) ]]; then
  usage
  exit 2
fi
MODE=$1

: "${CALICO_ARTIFACT_DIR:?CALICO_ARTIFACT_DIR is required}"
: "${KUBE_CONTEXT:?KUBE_CONTEXT is required; the current context is never implicit}"
: "${APPROVED_CRD_SHA256:?APPROVED_CRD_SHA256 must be independently approved}"
: "${APPROVED_OPERATOR_SHA256:?APPROVED_OPERATOR_SHA256 must be independently approved}"

if [[ ! "$APPROVED_CRD_SHA256" =~ ^[[:xdigit:]]{64}$ ]]; then
  fail 'APPROVED_CRD_SHA256 must contain exactly 64 hexadecimal characters'
fi
if [[ ! "$APPROVED_OPERATOR_SHA256" =~ ^[[:xdigit:]]{64}$ ]]; then
  fail 'APPROVED_OPERATOR_SHA256 must contain exactly 64 hexadecimal characters'
fi

if [[ -L "$CALICO_ARTIFACT_DIR" || ! -d "$CALICO_ARTIFACT_DIR" ]]; then
  fail 'artifact directory must exist as a real directory, not a symlink'
fi
CALICO_ARTIFACT_DIR=$(cd "$CALICO_ARTIFACT_DIR" && pwd -P) || fail 'could not resolve artifact directory'

CRD_FILE="$CALICO_ARTIFACT_DIR/v3_projectcalico_org.yaml"
OPERATOR_FILE="$CALICO_ARTIFACT_DIR/tigera-operator.yaml"

shopt -s dotglob nullglob
artifact_entries=("$CALICO_ARTIFACT_DIR"/*)
if [[ ${#artifact_entries[@]} -ne 2 ]]; then
  fail 'artifact directory must contain exactly the two expected manifest files'
fi
for artifact_entry in "${artifact_entries[@]}"; do
  if [[ -L "$artifact_entry" || ! -f "$artifact_entry" || ! -s "$artifact_entry" ]]; then
    fail 'artifact entries must be non-empty regular files and must not be symlinks'
  fi
  case "${artifact_entry##*/}" in
    v3_projectcalico_org.yaml|tigera-operator.yaml) ;;
    *) fail 'artifact directory contains an unexpected entry' ;;
  esac
done
if [[ ! -f "$CRD_FILE" || ! -f "$OPERATOR_FILE" ]]; then
  fail 'both expected manifest filenames are required'
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
INSTALLATION_DIR=$(cd "$SCRIPT_DIR/../k8s/calico" && pwd -P)
INSTALLATION_FILE="$INSTALLATION_DIR/installation.yaml"
if [[ -L "$INSTALLATION_FILE" || ! -f "$INSTALLATION_FILE" || ! -s "$INSTALLATION_FILE" ]]; then
  fail 'the project Calico Installation resource must be a non-empty regular file'
fi

# Apply only private snapshots. This prevents a verified input from being
# replaced between hashing and kubectl reopening the original path.
umask 077
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/cloudops-calico.XXXXXXXX") || fail 'could not create a private validation directory'
chmod 700 "$WORK_DIR" || fail 'could not secure the private validation directory'
cleanup() {
  local status=$?
  trap - EXIT
  if [[ -n "${WORK_DIR:-}" && -d "$WORK_DIR" && ! -L "$WORK_DIR" ]]; then
    rm -rf "$WORK_DIR" || printf '%s\n' 'Calico bootstrap: temporary-file cleanup failed' >&2
  fi
  exit "$status"
}
trap cleanup EXIT

STAGED_CRD_FILE="$WORK_DIR/v3_projectcalico_org.yaml"
STAGED_OPERATOR_FILE="$WORK_DIR/tigera-operator.yaml"
STAGED_INSTALLATION_FILE="$WORK_DIR/installation.yaml"
cp -P "$CRD_FILE" "$STAGED_CRD_FILE" || fail 'could not snapshot the CRD manifest'
cp -P "$OPERATOR_FILE" "$STAGED_OPERATOR_FILE" || fail 'could not snapshot the Operator manifest'
cp -P "$INSTALLATION_FILE" "$STAGED_INSTALLATION_FILE" || fail 'could not snapshot the Installation resource'

for staged_file in "$STAGED_CRD_FILE" "$STAGED_OPERATOR_FILE" "$STAGED_INSTALLATION_FILE"; do
  if [[ -L "$staged_file" || ! -f "$staged_file" || ! -s "$staged_file" ]]; then
    fail 'a staged configuration input is not a non-empty regular file'
  fi
done

if command -v sha256sum >/dev/null 2>&1; then
  SHA256_COMMAND=sha256sum
elif command -v shasum >/dev/null 2>&1; then
  SHA256_COMMAND=shasum
else
  fail 'neither sha256sum nor shasum is available'
fi

sha256_file() {
  if [[ "$SHA256_COMMAND" == 'sha256sum' ]]; then
    digest_output=$(sha256sum "$1") || fail 'could not calculate a manifest SHA-256'
  else
    digest_output=$(shasum -a 256 "$1") || fail 'could not calculate a manifest SHA-256'
  fi
  digest=${digest_output%% *}
  printf '%s' "$digest" | tr '[:upper:]' '[:lower:]'
}

actual_crd_sha256=$(sha256_file "$STAGED_CRD_FILE")
actual_operator_sha256=$(sha256_file "$STAGED_OPERATOR_FILE")
approved_crd_sha256=$(printf '%s' "$APPROVED_CRD_SHA256" | tr '[:upper:]' '[:lower:]')
approved_operator_sha256=$(printf '%s' "$APPROVED_OPERATOR_SHA256" | tr '[:upper:]' '[:lower:]')

if [[ "$actual_crd_sha256" != "$approved_crd_sha256" ]]; then
  fail 'CRD manifest SHA-256 does not match its separately approved value'
fi
if [[ "$actual_operator_sha256" != "$approved_operator_sha256" ]]; then
  fail 'Operator manifest SHA-256 does not match its separately approved value'
fi

if [[ "$MODE" == '--validate-only' ]]; then
  printf '%s\n' 'Calico artifact inputs passed local validation; no Kubernetes command was run.'
  exit 0
fi

: "${KUBECTL_BIN:=kubectl}"
if [[ "$KUBECTL_BIN" == */* ]]; then
  [[ -x "$KUBECTL_BIN" ]] || fail 'KUBECTL_BIN is not executable'
else
  command -v "$KUBECTL_BIN" >/dev/null 2>&1 || fail 'kubectl executable was not found'
fi

# Resolve the explicit context from local kubeconfig. This does not contact
# the cluster; every subsequent cluster command still names the same context.
context_names=$("$KUBECTL_BIN" config get-contexts --output=name) || fail 'could not read configured Kubernetes contexts'
context_found=false
while IFS= read -r configured_context; do
  if [[ "$configured_context" == "$KUBE_CONTEXT" ]]; then
    context_found=true
    break
  fi
done <<< "$context_names"
[[ "$context_found" == true ]] || fail 'KUBE_CONTEXT does not name a configured context'

trap 'status=$?; printf "Calico bootstrap stopped at line %s (exit %s); no automatic rollback was attempted.\n" "$LINENO" "$status" >&2' ERR

"$KUBECTL_BIN" --context "$KUBE_CONTEXT" apply -f "$STAGED_CRD_FILE"
"$KUBECTL_BIN" --context "$KUBE_CONTEXT" wait \
  --for=condition=Established \
  --timeout=120s \
  crd/installations.operator.tigera.io

"$KUBECTL_BIN" --context "$KUBE_CONTEXT" apply -f "$STAGED_OPERATOR_FILE"
"$KUBECTL_BIN" --context "$KUBE_CONTEXT" rollout status \
  --namespace=tigera-operator \
  deployment/tigera-operator \
  --timeout=180s

"$KUBECTL_BIN" --context "$KUBE_CONTEXT" apply -f "$STAGED_INSTALLATION_FILE"
"$KUBECTL_BIN" --context "$KUBE_CONTEXT" wait \
  --for=condition=Available \
  --timeout=300s \
  tigerastatus/calico
"$KUBECTL_BIN" --context "$KUBE_CONTEXT" rollout status \
  --namespace=calico-system \
  daemonset/calico-node \
  --timeout=300s
"$KUBECTL_BIN" --context "$KUBE_CONTEXT" rollout status \
  --namespace=calico-system \
  deployment/calico-kube-controllers \
  --timeout=300s
"$KUBECTL_BIN" --context "$KUBE_CONTEXT" wait \
  --for=condition=Ready \
  --timeout=300s \
  nodes --all

printf '%s\n' 'Calico bootstrap readiness checks completed. Runtime policy and application traffic checks remain necessary.'
