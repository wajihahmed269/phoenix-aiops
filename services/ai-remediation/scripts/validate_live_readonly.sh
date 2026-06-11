#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
KUBECONFIG_PATH="${KUBECONFIG_PATH:-$HOME/.kube/phoenix-k3s-oci.yaml}"
export ALERT_DRY_RUN="${ALERT_DRY_RUN:-true}"

echo "Phoenix-Ops AI remediation live read-only validation"
echo "Using kubeconfig: ${KUBECONFIG_PATH}"
echo "Notification mode override: ALERT_DRY_RUN=${ALERT_DRY_RUN}"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required."
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required."
  exit 1
fi

echo
echo "Cluster reachability:"
kubectl --kubeconfig "${KUBECONFIG_PATH}" get nodes -o wide

echo
echo "If Prometheus and Loki are not already reachable on 127.0.0.1:9090 and 127.0.0.1:3100,"
echo "start these manual port-forwards in separate terminals before continuing:"
echo "  kubectl --kubeconfig ${KUBECONFIG_PATH} -n observability port-forward svc/prometheus 9090:9090"
echo "  kubectl --kubeconfig ${KUBECONFIG_PATH} -n observability port-forward svc/loki 3100:3100"

echo
echo "Starting local service on 127.0.0.1:8081"
python3 "${ROOT_DIR}/services/ai-remediation/app/main.py" >/tmp/ai-remediation-validate.log 2>&1 &
SERVER_PID=$!
trap 'kill "${SERVER_PID}" >/dev/null 2>&1 || true' EXIT
sleep 1

echo
echo "Health:"
curl -s http://127.0.0.1:8081/healthz
echo
echo
echo "Poll once:"
curl -s -X POST http://127.0.0.1:8081/v1/poll-once
echo
echo
echo "Recommendations:"
curl -s http://127.0.0.1:8081/v1/recommendations
echo
