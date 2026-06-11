#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Deprecated wrapper: use scripts/oci-stop-lab.sh"
exec "${script_dir}/oci-stop-lab.sh" "$@"
