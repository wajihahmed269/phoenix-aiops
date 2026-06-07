# OCI BankApp Secret Preflight

Last updated: 2026-06-07

## Scope

This is a local operator runbook for preparing BankApp prerequisites before any future manual Argo CD sync on the OCI K3s cluster.

Do not run these commands until deployment is explicitly approved. This guide does not deploy BankApp, does not sync Argo CD, does not expose any Service publicly, and does not store real secret values in Git.

## Current State

- OCI K3s nodes are Ready.
- Argo CD and the ApplicationSet controller are healthy.
- Argo CD Services remain `ClusterIP`.
- No Argo CD Applications or ApplicationSets are deployed.
- BankApp is not deployed.
- BankApp is not ready to sync until `bankapp-secret` and `ghcr-pull-secret` exist in namespace `bankapp`.

## Required Secrets

Namespace:

```text
bankapp
```

`bankapp-secret` must contain exactly these application/runtime keys:

```text
SPRING_DATASOURCE_URL
SPRING_DATASOURCE_USERNAME
SPRING_DATASOURCE_PASSWORD
JWT_SECRET
MYSQL_ROOT_PASSWORD
```

The temporary in-cluster MySQL path uses this datasource target:

```text
jdbc:mysql://bankapp-mysql:3306/bankappdb?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC
```

`ghcr-pull-secret` must authorize image pulls from GHCR for:

```text
ghcr.io/wajihahmed269/ai-banking-backend:9b3cdb1
ghcr.io/wajihahmed269/ai-banking-frontend:9b3cdb1
```

## Commands To Run Later

Run these only after explicit approval and after confirming the active Kubernetes context points to the intended OCI K3s cluster.

Create the namespace:

```bash
kubectl create namespace bankapp
```

Create `bankapp-secret` with placeholder values replaced locally at runtime:

```bash
kubectl -n bankapp create secret generic bankapp-secret \
  --from-literal=SPRING_DATASOURCE_URL='jdbc:mysql://bankapp-mysql:3306/bankappdb?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC' \
  --from-literal=SPRING_DATASOURCE_USERNAME='bankapp' \
  --from-literal=SPRING_DATASOURCE_PASSWORD='<BANKAPP_DATABASE_PASSWORD>' \
  --from-literal=JWT_SECRET='<JWT_SECRET_AT_LEAST_32_BYTES>' \
  --from-literal=MYSQL_ROOT_PASSWORD='<MYSQL_ROOT_PASSWORD>'
```

Create `ghcr-pull-secret` with placeholder values replaced locally at runtime:

```bash
kubectl -n bankapp create secret docker-registry ghcr-pull-secret \
  --docker-server='ghcr.io' \
  --docker-username='<GHCR_USERNAME>' \
  --docker-password='<GHCR_TOKEN_WITH_READ_PACKAGES>' \
  --docker-email='<GHCR_ACCOUNT_EMAIL>'
```

Verify only metadata, not secret values:

```bash
kubectl -n bankapp get secret bankapp-secret ghcr-pull-secret
```

## Render Validation

Before any future sync, render only the BankApp-specific paths:

```bash
kubectl kustomize gitops/apps/bankapp
kubectl kustomize gitops/environments/dev/bankapp
```

Do not sync `gitops/environments/dev` broadly. The BankApp Argo CD Application path should remain:

```text
gitops/environments/dev/bankapp
```

## Blockers

Hard blockers before sync:

- `bankapp-secret` does not exist yet.
- `ghcr-pull-secret` does not exist yet.
- GHCR image pulls require credentials for the backend and frontend images listed above.
- `secret-template.yaml` is dummy-only, is not included in the kustomization, and must not be applied as-is.

Operational blockers:

- Do not sync BankApp until the required secrets exist.
- Do not sync `gitops/environments/dev` broadly.
- Do not deploy observability or PFMS as part of this phase.
- Do not expose BankApp, Argo CD, or any supporting Service publicly.
- Do not modify Terraform for this preflight.

## Sync Readiness

After the namespace and both required secrets exist, BankApp can proceed to the next review step: inspect the Argo CD diff for the BankApp-specific Application/path and then perform a manual BankApp sync only after explicit approval.

Secrets existing is necessary but not a command to sync. Keep automated sync disabled and keep first access local-only, such as through a later approved `kubectl port-forward`.
