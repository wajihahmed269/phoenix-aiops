#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Deprecated wrapper: use scripts/oci-status-lab.sh"
exec "${script_dir}/oci-status-lab.sh" "$@"
