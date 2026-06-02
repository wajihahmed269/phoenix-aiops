#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
values_file="${repo_root}/gitops/helm-values/argocd-values.yaml"
namespace="${ARGOCD_NAMESPACE:-argocd}"
release_name="${ARGOCD_RELEASE:-argocd}"
repo_name="${ARGOCD_HELM_REPO_NAME:-argo}"
repo_url="${ARGOCD_HELM_REPO_URL:-https://argoproj.github.io/argo-helm}"
chart_ref="${repo_name}/argo-cd"
wait_flag="${ARGOCD_HELM_WAIT:-true}"
confirm="${ARGOCD_CONFIRM:-false}"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required but was not found on PATH."
  exit 1
fi

if ! command -v helm >/dev/null 2>&1; then
  echo "helm is required but was not found on PATH."
  echo "Install Helm locally first, for example: HELM_VERSION=v3.x.x ./scripts/install-helm.sh"
  exit 1
fi

if [ ! -f "${values_file}" ]; then
  echo "Missing Helm values file: ${values_file}"
  exit 1
fi

echo "Active Kubernetes context:"
kubectl config current-context
echo
echo "This will install or upgrade Argo CD only. It will not deploy BankApp or create Argo CD Applications."
echo "Namespace: ${namespace}"
echo "Release: ${release_name}"
echo "Values: ${values_file}"
echo

if [ "${confirm}" != "true" ]; then
  echo "Set ARGOCD_CONFIRM=true to run the install after you verify the active context."
  exit 1
fi

kubectl get namespace "${namespace}" >/dev/null 2>&1 || kubectl create namespace "${namespace}"

if ! helm repo list | awk '{print $1}' | grep -qx "${repo_name}"; then
  helm repo add "${repo_name}" "${repo_url}"
fi

helm repo update "${repo_name}"

helm_args=(
  upgrade
  --install "${release_name}" "${chart_ref}"
  --namespace "${namespace}"
  --create-namespace
  --values "${values_file}"
)

if [ "${wait_flag}" = "true" ]; then
  helm_args+=(--wait)
fi

helm "${helm_args[@]}"

echo
echo "Argo CD bootstrap complete."
echo "Validate with: helm status ${release_name} -n ${namespace}"
echo "Access locally with: ./scripts/argocd-port-forward.sh"
