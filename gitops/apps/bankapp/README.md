# BankApp GitOps MVP

This directory contains the base manifests for the AI Banking App stable MVP slice:

```text
banking-frontend -> banking-backend -> RDS/MySQL
```

These files are placeholders for review and later manual GitOps deployment. Do not apply them directly, sync Argo CD, or expose services publicly until the image tags, pull secret, database secret, and runtime smoke path are confirmed.

For the first Phoenix-Ops presentation/demo, this slice also includes a temporary in-cluster MySQL Deployment named `bankapp-mysql`. This is a demo-stability workaround for the current private RDS reachability blocker only; the long-term target remains RDS/MySQL reachable from the Phoenix VPC through approved infrastructure changes.

## Images

Use immutable image tags only:

```text
ghcr.io/wajihahmed269/ai-banking-backend:REPLACE_WITH_IMMUTABLE_TAG
ghcr.io/wajihahmed269/ai-banking-frontend:REPLACE_WITH_IMMUTABLE_TAG
```

Before deployment, replace `REPLACE_WITH_IMMUTABLE_TAG` with a reviewed commit SHA, build ID, or release tag. Do not use `latest`.

The frontend serves the Vite build through nginx on port `80` and routes API calls through `/api`. The published `9b3cdb1` frontend image proxies `/api/` to `banking-app-service:80`, so this GitOps slice includes a compatibility ClusterIP Service named `banking-app-service` that selects the same backend pods as `banking-backend` and forwards port `80` to backend port `8080`. Keep this compatibility Service until the frontend image is rebuilt with a Phoenix-Ops-native upstream name.

## Required Secrets

`secret-template.yaml` is dummy-only and intentionally not included in `kustomization.yaml`. Create the real `bankapp-secret` through an approved secret workflow before any manual sync so Argo CD does not overwrite runtime values with dummy data.

Required keys:

```text
SPRING_DATASOURCE_URL
SPRING_DATASOURCE_USERNAME
SPRING_DATASOURCE_PASSWORD
JWT_SECRET
MYSQL_ROOT_PASSWORD
```

When using the temporary in-cluster MySQL demo path, set `SPRING_DATASOURCE_URL` to `jdbc:mysql://bankapp-mysql:3306/bankappdb?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC`, set `SPRING_DATASOURCE_USERNAME` to `bankapp`, keep `SPRING_DATASOURCE_PASSWORD` as the application database password, and generate `MYSQL_ROOT_PASSWORD` outside Git.

The image pull secret `ghcr-pull-secret` must also exist in the `bankapp` namespace before deployment.

## Manual Sync

The Argo CD Application template uses:

```text
repoURL: https://github.com/wajihahmed269/phoenix-aiops.git
targetRevision: HEAD
path: gitops/environments/dev/bankapp
```

Automated sync, prune, and self-heal are intentionally not configured. Review the Argo CD diff first, then run a manual sync only after secrets and immutable image tags are ready.

## Rollback

Prefer Git rollback:

1. Revert the GitOps commit that changed image tags or manifests.
2. Review the Argo CD diff.
3. Run a manual sync.
4. Verify pod readiness, logs, and the demo path.

## Smoke Checks

After a future manual sync, use local-only access such as port-forwarding to the `banking-frontend` Service. Keep services as `ClusterIP`.

Suggested checks:

```bash
kubectl -n bankapp get pods,svc
kubectl -n bankapp logs deploy/banking-backend
kubectl -n bankapp port-forward svc/banking-frontend 8088:80
```

Then browse `http://localhost:8088` and follow the stable demo path:

```text
open site -> signup/login -> dashboard -> add money -> pay bill -> transaction history
```
