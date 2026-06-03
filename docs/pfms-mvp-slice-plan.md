# PFMS MVP Slice Integration Plan

## Objective

Plan a minimal Phoenix-Ops demo workload using only this PFMS slice:

```text
pfms-ui -> api-gateway -> budget-service -> database
```

This is planning only. Do not modify PFMS source code, Phoenix-Ops Terraform, Kubernetes manifests, or live cluster state yet.

## Selected Services

| Service | Role | Reason selected |
|---|---|---|
| `pfms-ui` | React frontend | Provides visible user workflow and architecture dashboard surface for demos. |
| `api-gateway` | Spring Boot API gateway and auth | Contains the strongest real backend logic: JWT auth, BCrypt password handling, gateway routing, and actuator support. |
| `budget-service` | Spring Boot domain API | Most complete PFMS domain service and a good target for health, latency, DB, and dependency failure demos. |
| Database | Backing store for gateway and/or budget data | Required to make the slice stateful and operationally meaningful. Exact engine must be chosen before implementation. |

## Why This Slice

This slice keeps enough production-style complexity for Phoenix-Ops without importing the full PFMS sprawl:

- It has a user-facing frontend.
- It has authentication and API gateway behavior.
- It has a domain service with health and metrics hooks.
- It introduces one stateful dependency.
- It avoids Kafka, RabbitMQ, Consul, Eureka, MongoDB, Laravel, Go, and FastAPI until the base path is stable.

## Services Intentionally Excluded

| Excluded service/system | Reason |
|---|---|
| `notification-service` | Requires Kafka and MongoDB; useful later but adds dependency complexity now. |
| Kafka/Kafka UI | Not required for basic UI -> gateway -> budget path. Add later for event failure demos. |
| RabbitMQ | Only needed for transaction/account demo flow, which is excluded. |
| `account-service` | Thin demo service and not needed for budget flow. |
| `transaction-service` | RabbitMQ/Consul demo path, not needed for MVP. |
| `expense-service` | Laravel/Sail stack adds another runtime and DB model. |
| `goal-service` | H2/Consul/Redis assumptions add complexity outside the selected flow. |
| `analytics-service` | Minimal source implementation; not needed for MVP. |
| `reporting-service` | Minimal source implementation; not needed for MVP. |
| `config-server` | Defer unless direct config extraction proves too invasive. Prefer ConfigMaps first. |
| `discovery-server`/Eureka | Defer if the gateway can route directly to Kubernetes service DNS. |
| Consul | Not needed for selected services if Kubernetes DNS is used. |
| Jaeger/Grafana/Prometheus app bundles | Phoenix-Ops observability should own platform observability later. |

## Required Docker Changes

Do not implement yet. Required changes for the selected PFMS services:

### `pfms-ui`

- Add a production container image build path if missing or unsuitable.
- Make API base URL configurable at build time or runtime.
- Avoid hardcoded `http://localhost:8080` in deployable builds.
- Use immutable image tags for GitOps.

### `api-gateway`

- Replace prebuilt-JAR Docker dependency with a reproducible build process, or define CI as the artifact producer.
- Use a consistent Java runtime version matching the build target.
- Remove `latest` tags from deployable image references.
- Keep runtime config external through environment variables, ConfigMaps, and Secrets.

### `budget-service`

- Replace prebuilt-JAR Docker dependency with a reproducible build process, or define CI as the artifact producer.
- Normalize the exposed/listening port.
- Confirm whether H2 is acceptable for demo or replace it with the selected database.
- Keep Kafka disabled or optional for MVP unless the notification path is added later.

## Required Env Var Changes

Define a documented runtime contract before manifests are created.

### Frontend

Required config:

```text
PFMS_API_BASE_URL=<api-gateway URL exposed inside or outside cluster>
```

The exact variable name can change during implementation, but the deployable frontend must not hardcode localhost.

### API Gateway

Required config:

```text
SPRING_PROFILES_ACTIVE=<mvp profile>
SPRING_DATASOURCE_URL=<database JDBC URL>
SPRING_DATASOURCE_USERNAME=<from Secret>
SPRING_DATASOURCE_PASSWORD=<from Secret>
SECURITY_JWT_SECRET_KEY=<from Secret>
SECURITY_JWT_EXPIRATION_TIME=<duration>
BUDGET_SERVICE_URL=<Kubernetes service URL or gateway route target>
CORS_ALLOWED_ORIGINS=<frontend origin>
```

Avoid committing real values. Use Secret templates only.

### Budget Service

Required config:

```text
SPRING_PROFILES_ACTIVE=<mvp profile>
SERVER_PORT=<normalized port>
SPRING_DATASOURCE_URL=<database JDBC URL, if persistent DB is selected>
SPRING_DATASOURCE_USERNAME=<from Secret, if needed>
SPRING_DATASOURCE_PASSWORD=<from Secret, if needed>
MANAGEMENT_ENDPOINTS_WEB_EXPOSURE_INCLUDE=health,info,metrics,prometheus
KAFKA_ENABLED=false or equivalent implementation switch
```

The current PFMS config uses H2 and Config Server patterns. The MVP should prefer direct env/ConfigMap control unless implementation proves Config Server is required.

## Required Kubernetes Manifests

Planning target only. Do not create manifests yet.

Required resources:

```text
Namespace: pfms-demo
ConfigMaps:
  pfms-ui-config
  api-gateway-config
  budget-service-config
Secret templates:
  api-gateway-secret-template
  database-secret-template
Deployments:
  pfms-ui
  api-gateway
  budget-service
  database, if in-cluster DB is selected
Services:
  pfms-ui
  api-gateway
  budget-service
  database, if in-cluster DB is selected
Optional:
  Ingress or NodePort only after explicit exposure decision
```

Manifest rules:

- Use `ClusterIP` by default.
- Use dummy secret templates only.
- Add readiness and liveness probes for all app services.
- Add resource requests and limits.
- Keep labels/selectors consistent and boring.
- Do not enable Argo CD auto-sync for the first rollout.

## Required GitOps Layout

Recommended Phoenix-Ops layout once implementation starts:

```text
gitops/apps/pfms-mvp/
  namespace.yaml
  kustomization.yaml
  configmaps/
  secrets/
  deployments/
  services/

gitops/environments/dev/pfms-mvp/
  kustomization.yaml

gitops/helm-values/pfms-mvp/
  README.md or values placeholders, only if Helm is chosen
```

Argo CD Application template can be added only after:

- Git path is final.
- Image tags are known.
- Secret process is documented.
- Local render and dry-run validation pass.

Initial Argo CD behavior:

- Manual sync only.
- No auto-prune.
- No self-heal.
- No public ingress by default.

## Required CI/CD Image Build Steps

A minimal image pipeline should build only the selected services first:

1. Build `api-gateway` with Maven and run tests where reliable.
2. Build `budget-service` with Maven and run tests where reliable.
3. Build `pfms-ui` with npm using reproducible install.
4. Build container images for each selected service.
5. Tag images immutably using commit SHA or release version.
6. Push images to a user-approved registry.
7. Update GitOps image references only after image tags exist.

Do not invent registry names. The registry must be chosen by the user before implementation.

## Health Check Strategy

| Component | Readiness target | Liveness target | Notes |
|---|---|---|---|
| `pfms-ui` | HTTP `/` or static asset path | HTTP `/` | Also verify frontend can reach configured gateway in smoke tests. |
| `api-gateway` | `/actuator/health/readiness` if enabled, otherwise `/actuator/health` | `/actuator/health/liveness` if enabled, otherwise `/actuator/health` | Must include DB readiness in operational checks. |
| `budget-service` | `/actuator/health/readiness` if enabled, otherwise `/actuator/health` | `/actuator/health/liveness` if enabled, otherwise `/actuator/health` | Must not require Kafka in MVP unless Kafka is included. |
| Database | Native readiness command or TCP check | Native health command | Use Kubernetes startup/readiness behavior appropriate to chosen DB. |

Smoke test path after approved deployment:

```text
1. Load frontend.
2. Register or log in through api-gateway.
3. Call budget categories endpoint.
4. Create/read one budget record if persistence is enabled.
```

## Phoenix-Ops Demo Failure Scenarios

Good MVP failure scenarios:

- `budget-service` pod crash or restart loop.
- `api-gateway` cannot reach `budget-service` due to wrong service DNS or port.
- Database unavailable causing auth or budget failures.
- Expired or invalid JWT causing UI session failure.
- Readiness probe failure causing service to be removed from routing.
- Misconfigured frontend API base URL causing visible UI/backend disconnect.
- CPU or memory pressure on `budget-service` causing latency/restarts.

Defer these until the event path is added:

- Kafka unavailable.
- Notification consumer lag.
- RabbitMQ queue failures.
- Consul/Eureka service discovery split-brain.

## Estimated Implementation Order

1. Confirm database engine and whether it runs in-cluster for the demo.
2. Define the runtime contract for `pfms-ui`, `api-gateway`, and `budget-service`.
3. Patch PFMS source to remove localhost assumptions for the selected slice only.
4. Fix Docker builds for selected services.
5. Build and tag images in a user-approved registry.
6. Create Kubernetes manifests or Helm chart for `pfms-mvp`.
7. Add Secret templates with dummy values only.
8. Add GitOps environment overlay under `gitops/environments/dev/pfms-mvp/`.
9. Run local render and dry-run validation.
10. Add a manual-sync Argo CD Application template only after image paths and Git paths are final.
11. Deploy only after explicit approval.
12. Run smoke tests and document failure demo runbooks.

## Open Decisions Before Implementation

- Which database should back the MVP: MySQL, PostgreSQL, or H2 for first demo only?
- Should the database run in-cluster or remain external/manual for the first demo?
- Which image registry should be used?
- Should Eureka/Config Server be removed for the MVP path, or kept temporarily to reduce source changes?
- What external access method should the frontend use: port-forward, NodePort, or later ingress?

## MVP Recommendation

Proceed with the PFMS MVP slice only after locking these choices:

```text
Database engine
Image registry
Config strategy
Exposure strategy
```

The first implementation should target direct Kubernetes service DNS, manual Argo CD sync, and no event brokers.
