#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"

if [[ -x "$REPOSITORY_ROOT/.venv/bin/python" ]]; then
  PYTHON="$REPOSITORY_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
else
  printf '%s\n' 'FAIL: an existing Python 3 environment is required; no dependencies were installed.' >&2
  exit 127
fi

if [[ ! -r "$REPOSITORY_ROOT/scripts/demo_local.py" ]] || ! "$PYTHON" -c \
  'from prometheus_client.parser import text_string_to_metric_families' >/dev/null 2>&1; then
  printf '%s\n' 'FAIL: demo helper or existing prometheus-client dependency is unavailable.' >&2
  exit 127
fi

exec "$PYTHON" "$REPOSITORY_ROOT/scripts/demo_local.py" "$@"
