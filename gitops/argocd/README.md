# Argo CD Bootstrap

This directory contains Argo CD bootstrap files that are safe to review and validate locally.

Current files:
- `namespace.yaml` creates the `argocd` namespace.

Not included yet:
- Argo CD installation commands.
- Argo CD Application manifests.
- Repository credentials.
- Real Git repository URLs.

When ready, install Argo CD from the official manifests or Helm chart, then add Application manifests after the Git repository URL, target revision, and sync policy are known.

Do not run `kubectl apply` for these files during Phase 2.
