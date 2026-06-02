#!/usr/bin/env bash
set -euo pipefail

namespace="${ARGOCD_NAMESPACE:-argocd}"
service_name="${ARGOCD_SERVER_SERVICE:-argocd-server}"
local_port="${ARGOCD_LOCAL_PORT:-8080}"
remote_port="${ARGOCD_REMOTE_PORT:-443}"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required but was not found on PATH."
  exit 1
fi

echo "Active Kubernetes context:"
kubectl config current-context
echo
echo "Forwarding https://localhost:${local_port} to service/${service_name}:${remote_port} in namespace ${namespace}."
echo "Press Ctrl-C to stop the port-forward."
echo

kubectl port-forward -n "${namespace}" "svc/${service_name}" "${local_port}:${remote_port}"
