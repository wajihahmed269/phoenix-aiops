# OCI BankApp Readiness

Last updated: 2026-06-06 22:22 UTC

## Scope

This is a pre-deployment hardening assessment for the first safe BankApp deployment on the recovered OCI K3s cluster.

No BankApp workload was deployed, no Argo CD Application was synced, and no observability or PFMS workload was touched during this phase.

## Deployment Readiness

Current readiness: **not ready to sync yet**.

The rendered BankApp manifests are structurally clean and OCI-compatible, but two required Kubernetes Secrets do not exist yet and the GHCR app images require pull credentials.

Safe now:

- Render `gitops/apps/bankapp`.
- Review the BankApp Argo CD Application template.
- Keep all Services private as `ClusterIP`.
- Use the temporary in-cluster MySQL path after secrets are created.

Needs manual fix before sync:

- Create `bankapp-secret` in namespace `bankapp`.
- Create `ghcr-pull-secret` in namespace `bankapp`.
- Confirm the backend and frontend GHCR image tags are accessible with the pull secret.
- Confirm the first deployment uses `gitops/environments/dev/bankapp`, not the broad `gitops/environments/dev` entry point.

High risk:

- Syncing `gitops/environments/dev` broadly, because it currently points to BankApp.
- Syncing before secrets exist; MySQL and backend pods will fail to start.
- Assuming GHCR images are public; anonymous manifest checks returned `401 Unauthorized`.

Should defer:

- Observability deployment.
- PFMS deployment.
- Public Ingress, NodePort, or LoadBalancer exposure.
- External RDS restore or Terraform changes.
- Ollama service deployment or AI showcase path.

## Manifest Audit

Rendered path:

```bash
kubectl kustomize gitops/apps/bankapp
kubectl kustomize gitops/environments/dev/bankapp
```

Both render the same BankApp slice.

Rendered resources:

- `Namespace/bankapp`
- `ConfigMap/bankapp-config`
- `PersistentVolumeClaim/bankapp-mysql-data`
- `Service/bankapp-mysql`
- `Deployment/bankapp-mysql`
- `Deployment/banking-backend`
- `Service/banking-backend`
- `Service/banking-app-service`
- `Deployment/banking-frontend`
- `Service/banking-frontend`

Validation findings:

- Rendered object count: `10`.
- Duplicate resources: none.
- Namespaces: expected cluster-scoped `Namespace` plus namespaced `bankapp` resources.
- No Ingress resources.
- No LoadBalancer Services.
- No NodePort Services.
- No ExternalName Services.
- No ApplicationSet manifests.
- `secret-template.yaml` is intentionally not included in the kustomization.
- `application.yaml` is intentionally not included in the kustomization.

## OCI/K3s Compatibility

Compatible:

- All BankApp Services are `ClusterIP`.
- The Application destination uses the in-cluster Kubernetes API: `https://kubernetes.default.svc`.
- The namespace is explicit: `bankapp`.
- Replicas are minimal: one MySQL pod, one backend pod, one frontend pod.
- Resource requests and limits are modest enough for the 5-node OCI lab.

Storage:

- OCI K3s currently has `local-path` as the default StorageClass.
- `bankapp-mysql-data` does not set `storageClassName`, so it will bind through the default `local-path` provisioner.
- `local-path` is node-local storage. This is acceptable for the first demo deployment, but it is not HA and ties the MySQL data volume to node-local persistence behavior.

Exposure:

- No public service exposure exists in the GitOps BankApp manifests.
- Use `kubectl port-forward svc/banking-frontend 8088:80 -n bankapp` for local testing after a future approved sync.

Stale assumptions:

- The GitOps BankApp manifests do not contain AWS, EKS, ECR, ALB, ELB, RDS endpoint, Ingress, NodePort, or external DNS assumptions.
- The upstream app repo still contains old examples with `default` namespace, `ecr-secret`, `LoadBalancer`, `NodePort`, and optional Ingress. Those are not used by the Phoenix-Ops GitOps BankApp path.
- The BankApp README still documents the long-term RDS/MySQL target, but the current OCI first-deploy path uses temporary in-cluster MySQL.

## Image Audit

Backend:

- Image: `ghcr.io/wajihahmed269/ai-banking-backend:9b3cdb1`
- Pull secret reference: `ghcr-pull-secret`
- Anonymous GHCR manifest check: `401 Unauthorized`
- Assessment: treat as private or credential-required.

Frontend:

- Image: `ghcr.io/wajihahmed269/ai-banking-frontend:9b3cdb1`
- Pull secret reference: `ghcr-pull-secret`
- Anonymous GHCR manifest check: `401 Unauthorized`
- Assessment: treat as private or credential-required.

MySQL:

- Image: `mysql:8`
- Pull secret: none
- Anonymous Docker Hub manifest check: `200 OK`
- Assessment: accessible publicly, subject to normal Docker Hub rate limits.

Image tag assessment:

- Backend and frontend use immutable-looking tag `9b3cdb1`, not `latest`.
- MySQL uses floating major tag `8`; acceptable for a lab demo, but pinning to a full version such as `8.0.x` or digest would be more deterministic later.

## Required Secrets

Namespace: `bankapp`

Current live status:

- `bankapp` namespace: not present before deployment.
- `bankapp-secret`: not present.
- `ghcr-pull-secret`: not present.

`bankapp-secret` must be created outside Git with these keys:

```text
SPRING_DATASOURCE_URL
SPRING_DATASOURCE_USERNAME
SPRING_DATASOURCE_PASSWORD
JWT_SECRET
MYSQL_ROOT_PASSWORD
```

Recommended values for the temporary in-cluster MySQL path:

```text
SPRING_DATASOURCE_URL=jdbc:mysql://bankapp-mysql:3306/bankappdb?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC
SPRING_DATASOURCE_USERNAME=bankapp
SPRING_DATASOURCE_PASSWORD=<generate outside Git>
JWT_SECRET=<generate outside Git, at least 32 bytes of strong secret material>
MYSQL_ROOT_PASSWORD=<generate outside Git>
```

Secret reference validation:

- Backend loads `bankapp-secret` with `envFrom`, so all listed keys become environment variables.
- MySQL reads `SPRING_DATASOURCE_PASSWORD` as `MYSQL_PASSWORD`.
- MySQL reads `MYSQL_ROOT_PASSWORD` directly.
- Backend needs `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME`, `SPRING_DATASOURCE_PASSWORD`, and `JWT_SECRET`.
- `secret-template.yaml` currently lacks `MYSQL_ROOT_PASSWORD`; the README lists it correctly. Do not apply the template as-is.

`ghcr-pull-secret` must be created in `bankapp` and must authorize pulls for:

```text
ghcr.io/wajihahmed269/ai-banking-backend:9b3cdb1
ghcr.io/wajihahmed269/ai-banking-frontend:9b3cdb1
```

## AI Dependency Findings

Configured value:

```text
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:1b
```

Source behavior:

- Ollama is not called during backend startup.
- The backend only calls Ollama when the authenticated AI chat endpoint is used.
- Ollama failures are caught and returned as controlled "AI service unavailable" style responses.
- The backend has configurable Ollama timeouts with defaults:
  - connect timeout: `10000` ms
  - read timeout: `120000` ms
- The frontend AI request timeout is `45000` ms.

Risk:

- No `ollama` Service is part of the BankApp kustomization.
- The first AI request will fail or time out if no Service named `ollama` exists in the `bankapp` namespace or resolvable search path.
- This should not block backend pod startup, but it can produce slow or failed AI UX during demos.

Safest first-deploy strategy:

- Treat AI as deferred.
- Do not test the AI chat path in the first smoke test.
- Keep `SENDGRID_ENABLED=false` and `CLOUDINARY_ENABLED=false`.
- Later, either add a private in-cluster `ollama` Service deliberately or point `OLLAMA_BASE_URL` at an approved private service DNS name.

## MySQL Findings

The first OCI path uses in-cluster MySQL:

- Deployment: `bankapp-mysql`
- Service: `bankapp-mysql`
- Database: `bankappdb`
- User: `bankapp`
- PVC: `bankapp-mysql-data`, `2Gi`, `ReadWriteOnce`
- StorageClass: implicit default `local-path`

Startup and initialization:

- The MySQL image initializes the database and user only on an empty data directory.
- If the PVC already contains data from a previous run, changed database/user/password values may not reinitialize the existing database.
- The backend has no initContainer or explicit wait-for-MySQL gate.
- Backend startup depends on database reachability through Spring Data JPA and MySQL.
- `spring.jpa.hibernate.ddl-auto=update` allows schema creation/update at backend startup.

Probe behavior:

- MySQL readiness and liveness use `mysqladmin ping` against `127.0.0.1` with the root password.
- Backend readiness and liveness probe `/` on port `8080`.
- The backend does not include Spring Boot Actuator, so there is no `/actuator/health` endpoint today.
- `/` is a weak health proxy and may not prove DB readiness; it is still safer than pointing probes to non-existent Actuator paths.

Risk:

- If MySQL is slow on first initialization, the backend may start before MySQL is ready and can crash/retry.
- With one replica each, Kubernetes should eventually recover if MySQL becomes Ready and secrets are correct.
- PVC data persistence is node-local with `local-path`; this is acceptable for the first demo but not a production storage design.

## Deployment Blockers

Hard blockers before any sync:

- `bankapp-secret` does not exist.
- `ghcr-pull-secret` does not exist.
- `secret-template.yaml` is missing `MYSQL_ROOT_PASSWORD` and contains dummy values.
- GHCR image pulls require credentials.

Operational blockers:

- Avoid broad sync of `gitops/environments/dev`.
- Validate image pull credentials before creating the Argo CD Application or syncing.
- Confirm `JWT_SECRET` is stable and strong; otherwise tokens become invalid across pod restarts.
- Confirm `SPRING_DATASOURCE_URL` points to `bankapp-mysql` for the temporary in-cluster path.

Deferred blockers:

- AI/Ollama Service is not present.
- Backend does not expose Actuator health endpoints.
- MySQL storage is not HA.
- MySQL image tag is not fully pinned.

## Risk Assessment

Safe now:

- Render and inspect BankApp manifests.
- Create the `bankapp` namespace and required secrets in a controlled manual preflight step after approval.
- Keep first access local-only through port-forward.

Needs manual fix:

- Create `bankapp-secret` with the exact keys above.
- Create `ghcr-pull-secret`.
- Confirm GHCR pull permission.
- Use only the BankApp-specific Argo path.

High risk:

- Syncing without secrets.
- Syncing the broad dev environment.
- Assuming Ollama is present.
- Using dummy secret-template values.
- Reusing an existing dirty MySQL PVC with changed credentials.

Should defer:

- Frontend public exposure.
- AI demo path.
- Observability.
- PFMS.
- RDS migration.
- Terraform or OCI reprovisioning.

## Safest Deployment Sequence

Recommended first approach: **manual Argo CD sync of the complete BankApp slice after secret preflight**, not raw `kubectl apply`.

Reasoning:

- The slice is small and internally consistent.
- MySQL, backend, and frontend are coupled for the user-facing smoke path.
- The frontend depends on `banking-app-service`, which is included in the slice.
- Argo CD should own the deployed workload once the secrets are manually pre-created.

Sequence:

1. Confirm Argo CD remains healthy and private.
2. Do not sync `gitops/environments/dev`.
3. Create `bankapp` namespace only when deployment is explicitly approved.
4. Create `bankapp-secret` in `bankapp` with real values.
5. Create `ghcr-pull-secret` in `bankapp`.
6. Verify the pull secret can access both GHCR images.
7. Create or sync only the BankApp Argo CD Application that targets `gitops/environments/dev/bankapp`.
8. Manually sync BankApp.
9. Watch MySQL first, then backend, then frontend.
10. Use local-only port-forward to `svc/banking-frontend`.
11. Smoke test signup/login, dashboard, deposit, bill payment or transfer, and transaction history.
12. Skip AI chat in the first smoke test.

Alternative if extra caution is required:

- First sync MySQL only from a temporary reviewed path or one-off branch, then sync the full BankApp slice after MySQL is Ready.
- Do not make this the default unless startup ordering proves unstable; the current lightweight slice should be allowed to converge naturally after secrets are present.

## Rollback Considerations

Preferred rollback after an Argo-managed deployment:

1. Stop using the app through port-forward.
2. In Argo CD, delete or disable the BankApp Application only after confirming no other workloads depend on it.
3. Preserve the MySQL PVC if data might be needed.
4. Delete the `bankapp` namespace only if data loss is acceptable.

If a failed first sync occurs:

- Check image pull errors first.
- Check missing secret keys second.
- Check MySQL pod events and PVC binding third.
- Check backend logs for datasource connection failures fourth.
- Avoid deleting the PVC unless intentionally resetting MySQL initialization state.

Do not expose Services publicly as a rollback workaround.
