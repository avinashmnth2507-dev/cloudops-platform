#!/usr/bin/env bash
set -euo pipefail

readonly K3S_VERSION='v1.36.5+k3s1'
readonly K3S_ARCH='amd64'
# Intended configuration for a future separately reviewed installation. This
# validation/refusal script does not apply these values to a host.
readonly K3S_CLUSTER_CIDR='10.44.0.0/16'
readonly K3S_SERVICE_CIDR='10.43.0.0/16'
readonly K3S_CLUSTER_DNS='10.43.0.10'
readonly K3S_NETWORK_FLAGS='--flannel-backend=none --disable-network-policy'

usage() {
  printf '%s\n' \
    "Usage: $0 --validate-only | --install" \
    "Requires local k3s and install.sh inputs, approved SHA-256 values, and K3S_INSTALLER_COMMIT." >&2
}

fail() {
  printf 'K3s bootstrap: %s\n' "$1" >&2
  exit 1
}

if [[ $# -ne 1 || ( "$1" != '--validate-only' && "$1" != '--install' ) ]]; then
  usage
  exit 2
fi
MODE=$1

: "${K3S_ARTIFACT_DIR:?K3S_ARTIFACT_DIR is required}"
: "${APPROVED_K3S_BINARY_SHA256:?APPROVED_K3S_BINARY_SHA256 must be separately approved}"
: "${APPROVED_K3S_INSTALLER_SHA256:?APPROVED_K3S_INSTALLER_SHA256 must be separately approved}"
: "${K3S_INSTALLER_COMMIT:?K3S_INSTALLER_COMMIT must identify the reviewed immutable source commit}"

if [[ ! "$APPROVED_K3S_BINARY_SHA256" =~ ^[[:xdigit:]]{64}$ ]]; then
  fail 'APPROVED_K3S_BINARY_SHA256 must contain exactly 64 hexadecimal characters'
fi
if [[ ! "$APPROVED_K3S_INSTALLER_SHA256" =~ ^[[:xdigit:]]{64}$ ]]; then
  fail 'APPROVED_K3S_INSTALLER_SHA256 must contain exactly 64 hexadecimal characters'
fi
if [[ ! "$K3S_INSTALLER_COMMIT" =~ ^[[:xdigit:]]{40}$ ]]; then
  fail 'K3S_INSTALLER_COMMIT must contain a full 40-character hexadecimal commit ID'
fi
# This checks only the supplied identifier's format. It does not resolve the
# commit, bind it to install.sh, or authenticate a signer.

if [[ -L "$K3S_ARTIFACT_DIR" || ! -d "$K3S_ARTIFACT_DIR" ]]; then
  fail 'artifact directory must exist as a real directory, not a symlink'
fi
K3S_ARTIFACT_DIR=$(cd "$K3S_ARTIFACT_DIR" && pwd -P) || fail 'could not resolve artifact directory'

if ! command -v uname >/dev/null 2>&1; then
  fail 'uname is required to validate the target platform'
fi
target_os=$(uname -s) || fail 'could not determine target operating system'
target_arch=$(uname -m) || fail 'could not determine target architecture'
if [[ "$target_os" != 'Linux' || "$target_arch" != 'x86_64' ]]; then
  fail "target must be Linux amd64; detected ${target_os}/${target_arch}"
fi
if ! command -v systemctl >/dev/null 2>&1; then
  fail 'systemd systemctl is required on the intended target host'
fi

K3S_BINARY_FILE="$K3S_ARTIFACT_DIR/k3s"
K3S_INSTALLER_FILE="$K3S_ARTIFACT_DIR/install.sh"
shopt -s dotglob nullglob
artifact_entries=("$K3S_ARTIFACT_DIR"/*)
if [[ ${#artifact_entries[@]} -ne 2 ]]; then
  fail 'artifact directory must contain exactly k3s and install.sh'
fi
for artifact_entry in "${artifact_entries[@]}"; do
  if [[ -L "$artifact_entry" || ! -f "$artifact_entry" || ! -s "$artifact_entry" ]]; then
    fail 'artifact entries must be non-empty regular files and must not be symlinks'
  fi
  case "${artifact_entry##*/}" in
    k3s|install.sh) ;;
    *) fail 'artifact directory contains an unexpected entry' ;;
  esac
done

if command -v sha256sum >/dev/null 2>&1; then
  SHA256_COMMAND=sha256sum
elif command -v shasum >/dev/null 2>&1; then
  SHA256_COMMAND=shasum
else
  fail 'neither sha256sum nor shasum is available'
fi

sha256_file() {
  local digest_output digest
  if [[ "$SHA256_COMMAND" == 'sha256sum' ]]; then
    digest_output=$(sha256sum "$1") || fail 'could not calculate an input SHA-256'
  else
    digest_output=$(shasum -a 256 "$1") || fail 'could not calculate an input SHA-256'
  fi
  digest=${digest_output%% *}
  printf '%s' "$digest" | tr '[:upper:]' '[:lower:]'
}

actual_binary_sha256=$(sha256_file "$K3S_BINARY_FILE")
actual_installer_sha256=$(sha256_file "$K3S_INSTALLER_FILE")
approved_binary_sha256=$(printf '%s' "$APPROVED_K3S_BINARY_SHA256" | tr '[:upper:]' '[:lower:]')
approved_installer_sha256=$(printf '%s' "$APPROVED_K3S_INSTALLER_SHA256" | tr '[:upper:]' '[:lower:]')

if [[ "$actual_binary_sha256" != "$approved_binary_sha256" ]]; then
  fail 'K3s binary SHA-256 does not match its separately approved value'
fi
if [[ "$actual_installer_sha256" != "$approved_installer_sha256" ]]; then
  fail 'installer SHA-256 does not match its separately approved value'
fi

if [[ "$MODE" == '--validate-only' ]]; then
  printf 'K3s %s %s local inputs passed integrity validation; no installation was performed.\n' \
    "$K3S_VERSION" "$K3S_ARCH"
  exit 0
fi

fail 'installation is disabled: no complete reviewed installer and service setup route is approved; no installer or systemctl command was executed'
