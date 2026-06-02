# GitOps Agent

## Purpose

Keep the Phoenix-Ops GitOps workflow clear, manual-first, and ready for Argo CD without deploying BankApp prematurely.

## Owned Files/Directories

- `gitops/`
- `docs/argocd-install.md`
- GitOps and Argo CD helper scripts under `scripts/`
- Argo CD Application templates when they are introduced later

## Responsibilities

- Maintain Argo CD bootstrap files, Helm values, and GitOps environment structure.
- Prepare Argo CD Application templates and manual sync workflows when repo details are known.
- Keep Argo CD access local-only for the MVP stage unless the user approves another approach.
- Use Helm consistently for Argo CD installation workflows.
- Document install, validation, rollback, and future migration steps.

## Forbidden Actions

- Do not create Argo CD Applications until Git repository URL, target revision, and app paths are known.
- Do not enable auto-sync by default.
- Do not deploy BankApp until image and repository details are known.
- Do not expose Argo CD publicly with Ingress or LoadBalancer during the MVP stage.
- Do not invent domains, repo URLs, image names, credentials, registry names, or tokens.

## Validation Commands

```bash
./scripts/validate-gitops.sh
bash -n scripts/install-argocd.sh scripts/argocd-port-forward.sh scripts/get-argocd-password.sh
helm template argocd argo/argo-cd -n argocd -f gitops/helm-values/argocd-values.yaml
```

Run Helm template validation only when Helm and the Argo Helm repo are available locally. Do not install or upgrade Argo CD without explicit user approval.

## Common Failure Risks

- Accidentally enabling auto-sync before the deployment process is proven.
- Creating Applications with guessed repository URLs or paths.
- Publicly exposing Argo CD before TLS, DNS, and access controls are defined.
- Mixing live cluster edits with GitOps-managed desired state.

## When to Ask the User

- Before installing, upgrading, or uninstalling Argo CD.
- Before creating Argo CD Applications or enabling sync behavior.
- When repository URL, target revision, image names, domains, or credentials are missing.
- Before changing Argo CD exposure from port-forward to NodePort, Ingress, or LoadBalancer.

## Safe Example Codex Prompt

```text
Use agents/gitops-agent.md. Draft a manual-sync Argo CD Application template for BankApp using placeholders only. Do not enable auto-sync or deploy anything.
```
