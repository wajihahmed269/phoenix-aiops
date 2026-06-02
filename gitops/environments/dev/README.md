# Dev Environment

This directory is the GitOps entry point for the development environment.

Current content:
- `kustomization.yaml` references the BankApp placeholder manifests.

Before deployment:
- Replace placeholder image references.
- Replace dummy secret values with a secure secret workflow.
- Add Argo CD Application manifests only after the Git repository URL and sync policy are known.
