# AI Banking App Workload Plan

## Purpose

This document defines the operational plan for making the AI Banking App, also called Zephyr, the primary Phoenix-Ops GitOps workload. The app is already functionally working, so the plan favors a stable, deterministic deployment path over architecture changes or feature expansion.

PFMS remains useful as a secondary external workload experiment. It should not block or complicate the Banking App path.

## Source Reviewed

- Phoenix-Ops guidance: `AGENTS.md`, `agents/gitops-agent.md`, `agents/kubernetes-agent.md`
- Phoenix-Ops docs: `docs/phase-2.md`, `docs/bankapp-gitops-flow.md`
- Banking app repo: `https://github.com/wajihahmed269/ai-banking-app.git`
- Local clone: `/home/wajih/sandbox/ai-banking-app-workload`
- Banking app commit reviewed: `9b3cdb1 Fix notification read column mapping`

The requested file `/home/wajih/phoenix-aiops/Pasted text.txt` was not present during this audit, so no assumptions from that file are included here.

## Architecture Summary

The current clean workload shape is:

```text
banking-frontend -> banking-backend -> RDS/MySQL
                                   -> optional Ollama
```

The frontend is a React/Vite app served by nginx. It defaults to same-origin API routing through `/api`, and the frontend nginx config proxies `/api/` to `banking-app-service`.

The backend is a Spring Boot monolith. It owns authentication, JWT issuing and validation, financial operations, idempotency support, notifications, rate limiting, persistence, and Ollama-backed AI responses.

The database layer is MySQL-compatible. The clean Phoenix-Ops path should use an existing private RDS/MySQL endpoint rather than introducing an in-cluster database for the primary demo path.

Ollama should be optional for the first GitOps slice. The backend already degrades gracefully when Ollama is unavailable, returning a controlled "AI unavailable" style response instead of crashing the workload.

## Current Deployment Model

The app repo contains several deployment modes:

- Local/backend Docker image from the root `Dockerfile`
- Frontend Docker image from `frontend/Dockerfile`
- `docker-compose.yml` for a single backend container backed by external database and Ollama env vars
- Raw Kubernetes examples under `k8s/`
- GitHub Actions workflows for security checks, ECR image push, EC2/Kubernetes deployment, and ZAP scanning
- Recovery, smoke, alert, backup, and remediation scripts under `scripts/` and `phoenix-ops/`

Phoenix-Ops already contains placeholder BankApp GitOps files under:

```text
gitops/apps/bankapp/
gitops/environments/dev/
```

Those placeholders are useful scaffolding but are not ready to deploy as-is.

## Operational Strengths

- The app is already a better fit than PFMS as the primary operational showcase because it has a stable banking demo path, real auth, money movement, JWT behavior, AI integration, CI/CD history, recovery scripts, and observability artifacts.
- Backend financial operations use `BigDecimal`.
- Deposits, withdrawals, transfers, and payments are transactionally handled in service code.
- Transfers lock users in deterministic order to reduce deadlock risk.
- Idempotency support exists and is tested when `Idempotency-Key` is present.
- Frontend API access is centralized under `frontend/src/api/`.
- Frontend session storage is centralized under `frontend/src/auth/session.js`.
- Frontend has error boundaries and fallback rendering for high-risk dashboard sections.
- Backend has tests covering auth, protected banking flow, rate limiting, idempotency replay/conflict, invalid money input, insufficient funds, and notifications.
- Dockerfiles exist for both backend and frontend.
- Frontend nginx already supports SPA fallback and same-origin `/api/` proxying.
- Existing docs define a deterministic demo path:

```text
open site -> signup/login -> dashboard -> add money -> pay bill -> transaction history
```

- CI/CD already includes secret scanning, static analysis, dependency checks, image scanning, ECR push, deployment verification, and DAST concepts.
- Recovery scripts already cover ECR pull-secret refresh, deployment restarts, rollout status, smoke checks, and database backup.
- Ollama usage has bounded timeouts and safe fallback behavior.

## Operational Weaknesses

- Existing app `k8s/` manifests are direct-deploy examples, not Phoenix-Ops GitOps-ready manifests.
- App manifests use `default` namespace; Phoenix-Ops should use a dedicated namespace such as `bankapp` or `zephyr`.
- Current app frontend manifest uses `wajihahmed269/ai-banking-frontend:latest`; GitOps must use immutable tags only.
- Current app backend manifest uses `PLACEHOLDER_IMAGE`, `imagePullPolicy: Always`, and ECR naming assumptions.
- Current app backend Service is `LoadBalancer`; Phoenix-Ops should start with `ClusterIP` and local-only access or controlled port-forward, not public exposure.
- Current app frontend Service is `NodePort`; Phoenix-Ops should avoid public exposure for the first GitOps slice unless explicitly approved later.
- Existing Phoenix-Ops placeholder frontend deployment uses container port `3000`, but the frontend nginx image exposes port `80`.
- Existing Phoenix-Ops placeholder backend probes point at `/health`, but the backend does not currently expose `/health` or Actuator.
- The backend `pom.xml` does not include `spring-boot-starter-actuator`, so production-style readiness/liveness probes need either Actuator added later or probes must temporarily target a known existing path.
- Existing Phoenix-Ops placeholder secret keys do not match the backend's env var contract.
- The backend defaults to an ephemeral JWT signing key if `JWT_SECRET` is absent. This is acceptable for local dev, but Kubernetes must always provide a stable secret across replicas.
- CORS defaults to `http://localhost:5173`; Phoenix-Ops must set `FRONTEND_URL` deliberately for the selected access method.
- `spring.jpa.show-sql=true` is enabled by default, which is noisy for production-style logs.
- `spring.jpa.hibernate.ddl-auto=update` is acceptable for a lab MVP but should be treated as a migration risk later.
- Rate limiting is in-memory, so limits are per-pod when replicas exceed one.
- Account cache is in-memory, so repeated reads may behave per-pod under multi-replica backend deployments. Money mutations evict local cache only.
- Idempotency is implemented but optional when the header is absent. The demo-stability doc says mandatory idempotency is intentionally off for now.
- Some app repo alert/remediation docs contain hardcoded public IP examples. Those must not be copied into Phoenix-Ops GitOps as production-style defaults.
- The app CI still pushes a `latest` ECR tag in one workflow. GitOps must ignore `latest` and consume immutable tags only.

## Clean Stable MVP Deployment Path

Use the smallest slice that preserves the working app behavior:

```text
bankapp-frontend
  image: immutable frontend image
  service: ClusterIP, port 80
  nginx: proxy /api/ to backend service

bankapp-backend
  image: immutable backend image
  service: ClusterIP, port 8080
  env: database, JWT, CORS, Ollama config

RDS/MySQL
  external private database endpoint
  credentials from Kubernetes Secret or external secret workflow

Ollama
  optional for phase 1
  can be a private existing service URL, a separate internal deployment, or disabled/unavailable with graceful backend fallback
```

Do not convert the backend into microservices. Do not introduce a service mesh. Do not add ingress during the first GitOps rollout.

## Required Container Images

Use immutable tags only. Recommended tags:

```text
ghcr.io/wajihahmed269/ai-banking-backend:<git-sha>
ghcr.io/wajihahmed269/ai-banking-frontend:<git-sha>
```

If ECR is preferred later, use the same immutable tag rule:

```text
<account-id>.dkr.ecr.<region>.amazonaws.com/<backend-repo>:<git-sha>
<account-id>.dkr.ecr.<region>.amazonaws.com/<frontend-repo>:<git-sha>
```

Do not use `latest` in GitOps.

## Required Environment Variables

Backend:

```text
SPRING_DATASOURCE_URL
SPRING_DATASOURCE_USERNAME
SPRING_DATASOURCE_PASSWORD
JWT_SECRET
FRONTEND_URL
OLLAMA_BASE_URL
OLLAMA_MODEL
RATE_LIMIT_ENABLED
RATE_LIMIT_CAPACITY
RATE_LIMIT_WINDOW_SECONDS
IDEMPOTENCY_RETENTION_HOURS
MONEY_MAX_TRANSACTION_AMOUNT
SENDGRID_ENABLED
CLOUDINARY_ENABLED
```

Optional backend env vars if features are enabled later:

```text
SENDGRID_API_KEY
SENDGRID_FROM_EMAIL
SENDGRID_FROM_NAME
NOTIFICATION_DEV_RECIPIENT
CLOUDINARY_CLOUD_NAME
CLOUDINARY_API_KEY
CLOUDINARY_API_SECRET
CLOUDINARY_MAX_FILE_SIZE_BYTES
OLLAMA_CONNECT_TIMEOUT_MS
OLLAMA_READ_TIMEOUT_MS
```

Frontend:

```text
VITE_API_BASE_URL=/api
VITE_DEMO_MODE=true
```

Important: Vite variables are build-time values. If Phoenix-Ops needs runtime frontend configuration later, that should be planned deliberately. For the first GitOps slice, build the frontend with `/api` and keep same-origin nginx proxying.

## Required Secrets

Use dummy templates only in Git. Real values must be created outside the repo or through an approved external secret workflow.

Required secret keys for Kubernetes should match Spring env vars directly:

```text
SPRING_DATASOURCE_URL
SPRING_DATASOURCE_USERNAME
SPRING_DATASOURCE_PASSWORD
JWT_SECRET
```

Optional:

```text
OLLAMA_BASE_URL
SENDGRID_API_KEY
CLOUDINARY_API_KEY
CLOUDINARY_API_SECRET
```

The Phoenix-Ops placeholder `bankapp-secret` currently uses `BANKAPP_DB_USERNAME`, `BANKAPP_DB_PASSWORD`, and `BANKAPP_API_TOKEN`; that does not match the backend runtime contract and should be replaced in a future manifest implementation pass.

## Required GitOps Folders

Keep the existing Phoenix-Ops structure, but revise contents later:

```text
gitops/apps/bankapp/
  namespace.yaml
  kustomization.yaml
  configmap.yaml
  secret-template.yaml
  backend-deployment.yaml
  backend-service.yaml
  frontend-deployment.yaml
  frontend-service.yaml
  application.yaml
  README.md

gitops/environments/dev/
  kustomization.yaml
  README.md
```

Do not delete PFMS folders. PFMS remains under:

```text
gitops/apps/pfms-mvp/
gitops/environments/dev/pfms-mvp/
```

## Required Kubernetes Manifests

The first implementation pass should produce or update:

- Namespace: `bankapp` or `zephyr`, with Phoenix-Ops labels
- ConfigMap: non-secret runtime flags, CORS/access assumptions, AI model, rate-limit settings
- Secret template: dummy-only database, JWT, optional Ollama keys
- Backend Deployment: immutable image, env from ConfigMap/Secret, resource requests/limits, probes, `imagePullSecrets` if needed
- Backend Service: `ClusterIP`, port `8080`
- Frontend Deployment: immutable image, container port `80`, probes on `/`, resources, `imagePullSecrets` if needed
- Frontend Service: `ClusterIP`, port `80`
- Argo CD Application template: manual sync only, no auto-sync, no prune, no self-heal
- README: manual sync, image publishing, secret handling, rollback, and smoke checks

Do not add ingress yet.

## Probe Strategy

Preferred path:

1. Add Spring Boot Actuator in the app repo in a separate app-focused change.
2. Expose `management.endpoints.web.exposure.include=health,info,prometheus`.
3. Use `/actuator/health/readiness` and `/actuator/health/liveness` when configured.

Minimal no-code path:

- Backend readiness/liveness can temporarily use `GET /`, because it is permitted and served by the Spring MVC app.
- This is weaker because it proves HTTP rendering, not DB readiness.

Recommendation: add Actuator before the real GitOps deployment because readiness should reflect backend dependency health for a production-style showcase.

## Rollout Strategy

1. Build and push immutable backend and frontend images from the reviewed app commit.
2. Update GitOps manifests with those immutable tags.
3. Keep Argo CD sync manual.
4. Sync backend and frontend together only after database secret and pull secret are confirmed.
5. Use one backend replica for initial verification if cache/rate-limit behavior needs deterministic demo behavior.
6. Move to two backend replicas only after JWT secret, database connectivity, CORS, and frontend session flow are confirmed.
7. Keep frontend replicas at two after the image and service path are stable.
8. Verify rollout status, pod readiness, events, service endpoints, and logs before browser testing.

## Recovery Strategy

Primary rollback should be Git-based:

1. Revert the GitOps image tag change.
2. Review Argo CD diff.
3. Manual sync.
4. Verify backend and frontend rollout status.

Operational checks:

```bash
kubectl -n bankapp get deploy,pods,svc
kubectl -n bankapp rollout status deploy/bankapp-backend --timeout=300s
kubectl -n bankapp rollout status deploy/bankapp-frontend --timeout=300s
kubectl -n bankapp logs deploy/bankapp-backend --tail=100
kubectl -n bankapp logs deploy/bankapp-frontend --tail=100
```

Recovery scripts from the app repo are useful references, but they are currently tied to `default` namespace, ECR, and direct cluster commands. They should be adapted before becoming Phoenix-Ops-managed automation.

## Observability Integration Points

Immediate:

- Kubernetes deployment, pod, service, and event status
- Backend application logs
- Frontend nginx access/error logs
- Argo CD application health and sync status
- Database connectivity failures in backend logs
- Ollama timeout/unavailable warnings in backend logs

Recommended after Actuator:

- `/actuator/health`
- `/actuator/info`
- `/actuator/prometheus`
- Prometheus scrape annotations or ServiceMonitor, depending on the monitoring stack used

Existing app repo alert files are good reference material, but they are namespace/IP specific and should not be copied directly.

## AI/Ollama Deployment Considerations

Ollama should be optional in the first Phoenix-Ops BankApp rollout.

Options:

- Use an existing private Ollama endpoint and set `OLLAMA_BASE_URL`.
- Run Ollama separately in the cluster later with a private `ClusterIP` service.
- Leave Ollama unavailable during the first rollout and demonstrate backend graceful degradation.

Do not expose Ollama publicly. Do not add external AI APIs. Keep model name explicit through `OLLAMA_MODEL`.

The app's AI service already has:

- connect timeout
- read timeout
- prompt bounds
- unsafe request refusal
- fallback messages when Ollama is unavailable

## Deployment Risks

- Probe mismatch can cause false healthy or false unhealthy rollouts.
- Missing stable `JWT_SECRET` will break auth across replicas and restarts.
- Wrong frontend nginx upstream name will break all API calls.
- Using `latest` will make rollbacks and demo recovery nondeterministic.
- Missing image pull secret will block rollout.
- CORS mismatch will matter if direct frontend-to-backend calls are used instead of same-origin proxying.
- In-memory rate limit and account cache are per-pod; multi-replica behavior should be verified before using the app as a deterministic demo.
- `ddl-auto=update` can hide database migration drift.
- Existing direct-deploy workflow assumptions can conflict with GitOps if both manage the same cluster resources.
- Existing app alert docs include public IP examples and `default` namespace assumptions.
- The requested additional engineering context file was unavailable, so this plan should be revisited if that file contains constraints not covered here.

## Recommended Implementation Phases

### Phase 1: GitOps Readiness Cleanup

- Update Phoenix-Ops BankApp GitOps placeholders to match actual app ports, env names, and image policy.
- Keep images as placeholders or use immutable tags only after images are published.
- Add manual-sync Application template only.
- Do not deploy.

Estimated effort: 1 focused session.

### Phase 2: Image Publishing

- Build backend and frontend images from a known commit.
- Push immutable tags to the chosen registry.
- Document image digests and tags.
- Update GitOps image references.
- Do not sync automatically.

Estimated effort: 1 focused session.

### Phase 3: First Manual GitOps Rollout

- Confirm database secret, JWT secret, and pull secret exist.
- Run Kustomize validation.
- Manually sync in Argo CD.
- Verify pods, services, logs, and frontend path.
- Run the stable demo path manually.

Estimated effort: 1 focused session plus runtime debugging window.

### Phase 4: Operational Hardening

- Add Actuator and production-style health probes.
- Add Prometheus scrape/ServiceMonitor only after the base rollout is stable.
- Adapt recovery scripts to Phoenix-Ops namespace and GitOps behavior.
- Add dashboard/alert plans declaratively.

Estimated effort: 1-2 sessions.

### Phase 5: AI/Ollama Showcase

- Decide whether Ollama is external private service or in-cluster service.
- Add private service/env config.
- Verify graceful degradation and successful AI response path.
- Add bounded operational checks.

Estimated effort: 1 session if Ollama endpoint already exists; more if in-cluster Ollama resources are needed.

## Deployability Assessment

The Banking App is deployable as the primary Phoenix-Ops workload after a focused GitOps cleanup. It is stronger than PFMS for Phoenix-Ops because it already exercises the operational themes the platform is meant to demonstrate:

- auth consistency
- money-flow correctness
- database persistence
- AI integration
- CI/CD and image publishing
- rollout verification
- recovery scripts
- observability hooks
- deterministic user demo path

PFMS was useful for proving generic external workload mechanics. Zephyr is the better primary showcase because it aligns with the platform story.

## Recommended Rollout Order

1. Backend image publishing with immutable tag.
2. Frontend image publishing with immutable tag.
3. GitOps manifest cleanup and validation.
4. Manual Argo CD sync into a dedicated namespace.
5. Verify backend health/logs/database.
6. Verify frontend same-origin API path.
7. Run stable demo path.
8. Add Actuator and stronger probes.
9. Add observability integration.
10. Add Ollama as optional private AI dependency.

## Exact Next Implementation Prompt

```text
Read:
- AGENTS.md
- agents/gitops-agent.md
- agents/kubernetes-agent.md
- docs/phase-2.md
- docs/bankapp-gitops-flow.md
- docs/ai-banking-app-workload-plan.md

Context:
The AI Banking App is now the primary Phoenix-Ops workload. The app repo is cloned at ~/sandbox/ai-banking-app-workload and is already functionally working. Do not redesign the app or change behavior.

Goal:
Update the existing Phoenix-Ops BankApp GitOps placeholders so they accurately describe the stable MVP deployment slice, but do not deploy.

Critical rules:
- Do not modify Terraform.
- Do not modify Ansible.
- Do not deploy anything.
- Do not run kubectl apply.
- Do not sync Argo CD.
- Do not expose services publicly.
- Do not enable Argo CD auto-sync.
- Do not delete PFMS work.
- Use placeholder image names unless immutable images have already been published.
- Use dummy secret templates only.
- Keep changes minimal and operationally focused.

Tasks:
1. Inspect ~/sandbox/ai-banking-app-workload Dockerfiles, nginx config, application.properties, and k8s examples.
2. Update only gitops/apps/bankapp and gitops/environments/dev as needed.
3. Use a dedicated namespace for BankApp.
4. Keep frontend and backend as separate deployments.
5. Use ClusterIP services only.
6. Set frontend container port to 80.
7. Set backend container port to 8080.
8. Align ConfigMap and Secret template keys with the app runtime env vars.
9. Keep backend image and frontend image immutable-placeholder references.
10. Keep Argo CD Application manual-sync only.
11. Add clear README guidance for image publishing, secrets, manual sync, rollback, and smoke verification.
12. Run:
   - kubectl kustomize gitops/apps/bankapp
   - kubectl kustomize gitops/environments/dev
   - YAML syntax check if available
   - git diff -- gitops/apps/bankapp gitops/environments/dev

Output:
- changed files
- validation results
- exact diff
- remaining blockers
- next manual steps
```
