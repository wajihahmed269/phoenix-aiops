#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
KUBECONFIG_PATH="${KUBECONFIG_PATH:-$HOME/.kube/phoenix-k3s-oci.yaml}"

echo "Phoenix-Ops K8sGPT advisor validation"
echo "Using kubeconfig: ${KUBECONFIG_PATH}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required."
  exit 1
fi

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required."
  exit 1
fi

if [[ ! -r "${KUBECONFIG_PATH}" ]]; then
  echo "Kubeconfig is not readable: ${KUBECONFIG_PATH}"
  exit 1
fi

echo
echo "Binary presence:"
if command -v k8sgpt >/dev/null 2>&1; then
  echo "k8sgpt: present"
else
  echo "k8sgpt: missing"
fi

echo
echo "OCI tunnel and kubeconfig reachability:"
if kubectl --kubeconfig "${KUBECONFIG_PATH}" cluster-info >/dev/null 2>&1; then
  echo "kubectl cluster-info: reachable"
else
  echo "kubectl cluster-info: unreachable"
fi

echo
echo "Collector bounded execution and JSON handling:"
PYTHONPATH="${ROOT_DIR}/services/ai-remediation" \
python3 - <<'PY'
from app.collectors.k8sgpt import collect_namespace_advisories
from app.config.loader import load_config

config = load_config()
config["feature_flags"]["enable_k8sgpt_collector"] = True
result = collect_namespace_advisories(config, ["bankapp"])
print(result["bankapp"])

config["k8sgpt"]["binary"] = "/definitely/missing/k8sgpt"
fallback = collect_namespace_advisories(config, ["bankapp"])
print(fallback["bankapp"])
PY
