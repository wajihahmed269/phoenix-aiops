# Argo CD Bootstrap

This directory contains Argo CD bootstrap files that are safe to review and validate locally.

Current files:
- `namespace.yaml` creates the `argocd` namespace.

Related files:
- `../apps/bankapp/application.yaml` is a future BankApp Application template. It is not included in the BankApp Kustomization and should not be applied until the real repository URL and image references are known.
- `../helm-values/argocd-values.yaml` keeps Argo CD server access as `ClusterIP` for port-forward-only UI access.

Not included:
- Repository credentials.
- Real Git repository URLs.
- Automated sync policy.

When ready, install Argo CD from the Helm chart, then create Application manifests only after the Git repository URL, target revision, and sync policy are known.

Do not run `kubectl apply` for these files during Phase 2.
