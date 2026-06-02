#!/usr/bin/env bash
set -euo pipefail

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required but was not found on PATH."
  exit 1
fi

echo "Active Kubernetes context:"
kubectl config current-context
echo

echo "Nodes:"
kubectl get nodes -o wide
echo

echo "System pods:"
kubectl get pods -n kube-system -o wide
echo

if kubectl get namespace argocd >/dev/null 2>&1; then
  echo "Argo CD pods:"
  kubectl get pods -n argocd -o wide
else
  echo "Argo CD namespace not found."
fi
echo

if kubectl get namespace bankapp >/dev/null 2>&1; then
  echo "BankApp pods:"
  kubectl get pods -n bankapp -o wide
else
  echo "BankApp namespace not found."
fi
