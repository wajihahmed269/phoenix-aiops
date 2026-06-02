# Argo CD Install - MVP Bootstrap

## Architecture Overview

This bootstrap installs Argo CD into the existing K3s cluster as a Helm release in the `argocd` namespace.

MVP access is local-only:
- Argo CD server runs as `ClusterIP`.
- No Ingress is created.
- No LoadBalancer is created.
- Operators access the UI through `kubectl port-forward`.

BankApp is not deployed in this step. Argo CD Applications are intentionally left for the next phase after Argo CD access is validated.

## Why Helm Is Used

Helm keeps Argo CD installation and upgrades repeatable with one release name, one chart source, and one values file:

- Chart: `argo/argo-cd`
- Release: `argocd`
- Namespace: `argocd`
- Values: `gitops/helm-values/argocd-values.yaml`

The repository keeps the values file under GitOps control, while the install script performs the controlled bootstrap into the cluster.

## Namespace Strategy

Argo CD is isolated in the `argocd` namespace. The install script creates the namespace if it is missing and then installs or upgrades the Helm release into that namespace.

The namespace manifest in `gitops/argocd/namespace.yaml` remains useful for review and future GitOps bootstrap flows.

## Local-Only Access

The default service type is `ClusterIP`. Use port-forwarding from your workstation:

```bash
./scripts/argocd-port-forward.sh
```

Then open:

```text
https://localhost:8080
```

The browser may warn about the default Argo CD certificate. That is expected for this MVP stage.

## Install Flow

Review the active Kubernetes context first:

```bash
kubectl config current-context
```

Install or upgrade Argo CD after verifying the active context:

```bash
ARGOCD_CONFIRM=true ./scripts/install-argocd.sh
```

The script uses:

```bash
helm upgrade --install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace \
  --values gitops/helm-values/argocd-values.yaml \
  --wait
```

## Validation Flow

Check Helm release status:

```bash
helm status argocd -n argocd
```

Check Argo CD pods:

```bash
kubectl get pods -n argocd
```

Port-forward the server:

```bash
./scripts/argocd-port-forward.sh
```

Get the initial admin password:

```bash
./scripts/get-argocd-password.sh
```

Log in with:

```text
Username: admin
Password: output from scripts/get-argocd-password.sh
```

## Rollback Commands

Remove the Helm release:

```bash
helm uninstall argocd -n argocd
```

After confirming no Argo CD resources are needed, remove the namespace:

```bash
kubectl delete namespace argocd
```

Do not remove the namespace if another release or resource is using it.

## Security Notes

- Do not expose Argo CD publicly during this MVP stage.
- Do not create an Ingress until a domain, TLS plan, and access control model are known.
- Do not commit repository credentials, kubeconfigs, tokens, or admin passwords.
- Change or disable the initial admin account after the access model is defined.
- Keep automated sync disabled until the deployment workflow is reviewed.

## Future Migration Path

After Argo CD access is validated:

1. Define the Git repository URL and access method.
2. Add Argo CD Application manifests for BankApp.
3. Keep sync manual at first.
4. Add TLS, domain, and ingress only after DNS and security requirements are known.
5. Consider SSO or a stronger local access model before exposing Argo CD beyond port-forwarding.
