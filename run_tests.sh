#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is required to run the tests. Install uv and try again." >&2
    exit 127
fi

exec uv run --group dev python -m pytest "$@"
