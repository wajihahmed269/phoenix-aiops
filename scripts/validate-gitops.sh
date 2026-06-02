#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "GitOps files:"
find "${repo_root}/gitops" -maxdepth 4 -type f | sort

if command -v python3 >/dev/null 2>&1; then
  echo
  echo "Checking YAML syntax with Python..."
  python3 - <<'PY' "${repo_root}/gitops"
import pathlib
import sys

try:
    import yaml
except ImportError:
    print("PyYAML is not installed; skipping Python YAML syntax check.")
    raise SystemExit(0)

root = pathlib.Path(sys.argv[1])
failed = False
for path in sorted(root.rglob("*.yaml")):
    try:
        with path.open("r", encoding="utf-8") as handle:
            list(yaml.safe_load_all(handle))
    except Exception as exc:
        failed = True
        print(f"YAML error in {path}: {exc}")

if failed:
    raise SystemExit(1)

print("YAML syntax check passed.")
PY
else
  echo
  echo "python3 not found; skipping YAML syntax check."
fi

if command -v kubectl >/dev/null 2>&1; then
  echo
  echo "Rendering Kustomize output with kubectl..."
  kubectl kustomize "${repo_root}/gitops/apps/bankapp" >/dev/null
  kubectl kustomize "${repo_root}/gitops/environments/dev" >/dev/null
  echo "Kustomize render passed."

  if [ "${ENABLE_KUBECTL_DRY_RUN:-0}" = "1" ]; then
    echo
    echo "Running opt-in client-side dry run for BankApp manifests..."
    kubectl apply --dry-run=client --validate=false -k "${repo_root}/gitops/apps/bankapp" >/dev/null
    echo "kubectl client-side dry run passed."
  else
    echo
    echo "Skipping kubectl apply dry run; set ENABLE_KUBECTL_DRY_RUN=1 to run it against your active context."
  fi
else
  echo
  echo "kubectl not found; skipping Kustomize render and client-side dry run."
fi

if command -v shellcheck >/dev/null 2>&1; then
  echo
  echo "Running shellcheck..."
  shellcheck "${repo_root}/scripts/install-helm.sh" "${repo_root}/scripts/validate-gitops.sh"
  echo "shellcheck passed."
else
  echo
  echo "shellcheck not found; skipping shell script lint."
fi
