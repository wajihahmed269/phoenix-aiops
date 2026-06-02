# Phoenix AIOps - Phase 2: GitOps and BankApp Deployment

## Objective

Phase 2 creates the GitOps foundation for deploying BankApp onto the existing K3s cluster with Helm-style values, Kustomize manifests, and Argo CD bootstrap files.

This phase does not install Argo CD, apply Kubernetes manifests, or deploy BankApp to the live cluster. It prepares declarative files that can be reviewed, validated, and applied later.

## Prerequisites

- Phase 1 is complete.
- All 5 K3s nodes are `Ready`.
- `kubectl` can reach the K3s cluster when you intentionally choose to validate against it.
- Helm is installed locally on the workstation, or installed with `scripts/install-helm.sh`.
- BankApp container image references are known before any real deployment.
- Any real credentials are created outside this repository or managed by a secure secret workflow.

## Target Architecture

- Argo CD runs in the `argocd` namespace.
- BankApp runs in the `bankapp` namespace.
- BankApp frontend and backend are declared as separate Kubernetes Deployments.
- Frontend and backend Services expose stable in-cluster names.
- Configuration is provided by a ConfigMap.
- Secret files in this repository are templates with dummy values only.
- Environment entry points live under `gitops/environments/`.

## Folder Structure

```text
gitops/
  argocd/
    namespace.yaml
    README.md
  apps/
    bankapp/
      namespace.yaml
      configmap.yaml
      secret-template.yaml
      backend-deployment.yaml
      backend-service.yaml
      frontend-deployment.yaml
      frontend-service.yaml
      kustomization.yaml
  helm-values/
    argocd-values.yaml
  environments/
    dev/
      README.md
      kustomization.yaml
scripts/
  install-helm.sh
  validate-gitops.sh
```

## Execution Order

1. Review all files under `gitops/`.
2. Replace placeholder BankApp image references with real image references after the image source is known.
3. Replace the dummy secret template with a secure secret process before deployment.
4. Install Helm locally if needed:
   ```bash
   ./scripts/install-helm.sh
   ```
5. Run local validation:
   ```bash
   ./scripts/validate-gitops.sh
   ```
6. Install Argo CD only when ready.
7. Register the GitOps repository with Argo CD only after the repository URL and access method are known.
8. Create Argo CD Application manifests after the Git repository URL, target revision, and desired sync policy are known.

## Validation Commands

Local file checks:
```bash
find gitops -maxdepth 4 -type f | sort
./scripts/validate-gitops.sh
```

Safe local Kubernetes render:
```bash
kubectl kustomize gitops/apps/bankapp
kubectl kustomize gitops/environments/dev
```

Optional client-side dry run. This may still contact the active Kubernetes context for API discovery, so run it only when that context is intentional and reachable:
```bash
ENABLE_KUBECTL_DRY_RUN=1 ./scripts/validate-gitops.sh
```

Do not run `kubectl apply` without `--dry-run` during this phase.

## Rollback Notes

- Since this phase only adds repository files, rollback is a Git revert or file removal.
- No live Kubernetes resources should exist from this phase.
- If files are applied later, remove Argo CD Applications first, then remove BankApp resources, then remove the `bankapp` namespace when it is safe.
- Keep Terraform rollback separate from this phase.

## Risks and Guardrails

- Do not commit real credentials, kubeconfigs, tokens, or generated secrets.
- Do not apply manifests to a live cluster during this phase.
- Do not install Argo CD until the bootstrap plan is reviewed.
- Do not invent image names, repository URLs, domains, or credentials.
- Keep Argo CD sync manual until the deployment path is proven.
- Keep BankApp remediation and automation human-reviewed until policies are explicitly defined.
