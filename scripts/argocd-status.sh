#!/usr/bin/env bash
set -euo pipefail

namespace="${ARGOCD_NAMESPACE:-argocd}"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required but was not found on PATH."
  exit 1
fi

echo "Active Kubernetes context:"
kubectl config current-context
echo

echo "Argo CD namespace:"
kubectl get namespace "${namespace}"
echo

echo "Argo CD pods:"
kubectl get pods -n "${namespace}" -o wide
echo

echo "Argo CD services:"
kubectl get svc -n "${namespace}"
echo

echo "Argo CD applications:"
kubectl get applications.argoproj.io -n "${namespace}" 2>/dev/null || {
  echo "No Argo CD Applications found or the Argo CD CRD is unavailable."
}
