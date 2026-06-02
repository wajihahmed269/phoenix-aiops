#!/usr/bin/env bash
set -euo pipefail

namespace="${ARGOCD_NAMESPACE:-argocd}"
secret_name="${ARGOCD_INITIAL_ADMIN_SECRET:-argocd-initial-admin-secret}"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required but was not found on PATH."
  exit 1
fi

echo "Active Kubernetes context:"
kubectl config current-context
echo

if ! kubectl get secret "${secret_name}" -n "${namespace}" >/dev/null 2>&1; then
  echo "Secret ${namespace}/${secret_name} was not found."
  echo "Argo CD may not be installed yet, or the initial admin secret may already have been removed."
  exit 1
fi

password="$(kubectl get secret "${secret_name}" -n "${namespace}" -o jsonpath='{.data.password}' | base64 --decode)"

echo "Argo CD initial admin credentials:"
echo "Username: admin"
echo "Password: ${password}"
echo
echo "Use port-forwarded access: https://localhost:8080"
echo "After logging in, change the admin password and avoid committing credentials."
