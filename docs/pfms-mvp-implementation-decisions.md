# PFMS MVP Implementation Decisions

## Scope

This document finalizes implementation decisions for the Phoenix-Ops PFMS demo slice:

```text
pfms-ui -> api-gateway -> budget-service -> database
```

This is decision documentation only. Do not modify PFMS source code, create Kubernetes manifests, create Dockerfiles, modify Terraform, or deploy anything from this document alone.

PFMS inspection source: `/home/wajih/sandbox/pfms-audit`

## Chosen Database Engine

Chosen MVP database engine: **MySQL 8.0**.

Rationale:

- `api-gateway` already uses MySQL-shaped configuration and the local DB script runs `mysql:8.0`.
- The PFMS parent Maven `pom.xml` includes `com.mysql:mysql-connector-j` as a runtime dependency inherited by Java modules.
- `budget-service` currently uses H2 configuration, but its JPA model can be moved to MySQL through a dedicated MVP profile and environment variables without adding a new database driver.
- PostgreSQL is mentioned in PFMS docs, but the selected Java service code does not currently include a PostgreSQL driver.
- H2 is useful for unit tests and local development, but it is not the right stateful dependency for a Phoenix-Ops Kubernetes demo.

Use one MySQL instance for the MVP, with separate logical databases or schemas for gateway auth data and budget data. Do not commit real database passwords.

## Services Included

| Service | Role | Decision |
|---|---|---|
| `pfms-ui` | Frontend | Include. It gives Phoenix-Ops a visible workload and user workflow. |
| `api-gateway` | Auth and routing | Include. It provides login/signup, JWT validation, and the gateway path to budgets. |
| `budget-service` | Budget domain API | Include. It is the selected domain service and the main failure-demo target. |
| MySQL | Stateful dependency | Include as the single MVP database engine. |

## Services Excluded

| Service or dependency | Decision |
|---|---|
| `config-server` | Exclude for MVP. Replace with explicit local profile/env configuration. |
| `discovery-server`/Eureka | Exclude for MVP after small source/config edits remove discovery reliance. |
| Consul | Exclude. The selected slice can use Docker Compose service names locally and Kubernetes DNS later. |
| Kafka | Exclude for MVP. Budget notification publishing must be disabled or made conditional. |
| RabbitMQ | Exclude. It is only needed for the transaction/account path. |
| `notification-service` | Exclude because it requires Kafka and MongoDB. |
| `account-service` and `transaction-service` | Exclude because they are RabbitMQ/Consul-oriented and outside the budget path. |
| `expense-service`, `goal-service`, `analytics-service`, `reporting-service` | Exclude until the MVP path is stable. |
| App-owned Grafana, Jaeger, Kafka UI, Portainer, n8n | Exclude. Phoenix-Ops platform observability should own observability later. |

## Config Strategy

Use an explicit MVP profile, for example `SPRING_PROFILES_ACTIVE=mvp`, backed by service-local config and environment variables.

Do not use Spring Cloud Config Server for the MVP. The current `spring.config.import=optional:configserver:...` entries are local-machine oriented and make startup dependent on another service and an external Git source.

Required future config behavior:

- `api-gateway` reads database URL, username, password, JWT secret, JWT expiration, CORS origins, and budget route target from environment variables or a local MVP profile.
- `budget-service` reads database URL, username, password, server port, management exposure, and notification publishing toggle from environment variables or a local MVP profile.
- `pfms-ui` reads the API gateway base URL from a build-time or runtime configuration mechanism instead of hardcoding `http://localhost:8080`.
- All real secrets stay outside git. Phoenix-Ops may later create Secret templates with dummy values only.

## Service Discovery Strategy

Use direct service addressing for the MVP:

- Docker Compose: route from `api-gateway` to `http://budget-service:8082`.
- Kubernetes: route from `api-gateway` to `http://budget-service:8082` through in-namespace service DNS.

Do not run Eureka or Consul for the MVP.

Current blockers:

- `api-gateway` uses `@EnableDiscoveryClient` and gateway route URI `lb://budget-service`.
- `budget-service` uses `@EnableDiscoveryClient`.
- `budget-service` injects `EurekaClient` in `BudgetControllerV1` and the `/v1/api/budgets/greeting` endpoint calls Eureka.

Decision: remove or disable discovery for the MVP and replace the gateway route with a direct HTTP URI. Replace the UI health check dependency on the Eureka-backed greeting endpoint with an actuator health or simple service health path.

## Messaging Strategy

Kafka must be excluded for the MVP, but `budget-service` currently has runtime coupling:

- `BudgetService` publishes a `BudgetNotification` event after saving a budget.
- `BudgetNotificationHandler` handles the event after commit.
- `BudgetNotificationProducer` requires a `KafkaTemplate`.
- `KafkaTopicConfig` creates a Kafka topic bean.

Decision: implement a small feature flag later, such as `PFMS_NOTIFICATIONS_ENABLED=false`, and make producer, handler, topic config, and event publication conditional. Do not deploy Kafka just to make the MVP boot.

RabbitMQ is not involved in this slice.

## Local Docker Compose Strategy

Create a future PFMS-local MVP compose file that starts only:

```text
mysql
api-gateway
budget-service
pfms-ui
```

Compose decisions:

- Use service names, not `localhost` or `host.docker.internal`, for container-to-container traffic.
- Use MySQL health checks and `depends_on` with health conditions where supported.
- Do not use hardcoded real passwords. Use local `.env` placeholders and document required variables.
- Avoid `delose/*:latest` tags in deployable workflows. Use local build tags for compose testing, then immutable registry tags for GitOps.
- Keep Kafka, Eureka, Config Server, Consul, and RabbitMQ out of the MVP compose file.

## Kubernetes and GitOps Strategy

Do not create Kubernetes manifests yet.

Future Phoenix-Ops layout should be:

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
```

Kubernetes decisions:

- Use namespace `pfms-demo` unless the user chooses a different name before implementation.
- Use `ClusterIP` services by default.
- Expose the frontend only after an explicit access decision.
- Use readiness and liveness probes for UI, gateway, budget-service, and database.
- Keep Argo CD manual sync only.
- Do not enable auto-sync, auto-prune, self-heal, or public ingress during the first rollout.

## Image Registry Strategy Placeholder

Do not invent a registry.

Future image references must remain placeholders until the user chooses a registry:

```text
<registry>/<namespace>/pfms-ui:<immutable-tag>
<registry>/<namespace>/api-gateway:<immutable-tag>
<registry>/<namespace>/budget-service:<immutable-tag>
```

Preferred tag strategy: commit SHA or explicit release version. Avoid `latest` in GitOps.

## Exact Files to Edit Later

Do not edit these files yet. This is the implementation backlog.

### PFMS UI

| File | Future change |
|---|---|
| `pfms-ui/src/services/api.ts` | Replace hardcoded `API_GATEWAY_URL = 'http://localhost:8080'` with configurable gateway URL. Change budget health call away from `/v1/api/budgets/greeting` if greeting is removed. |
| `pfms-ui/src/pages/BudgetPage.tsx` | Replace direct `http://localhost:8080/v1/api/budgets` call with shared API base URL helper. |
| `pfms-ui/src/components/BudgetServiceHealth.tsx` | Stop requiring response text containing `Hello from`; use actuator or normalized health response. |
| `pfms-ui/src/components/DashboardMonitor.tsx` | Remove or hide hardcoded localhost dashboard links for excluded services in the MVP view. |
| `pfms-ui/src/pages/ArchitecturePage.tsx` | Reduce MVP architecture view or make service dashboard URLs configurable. |
| `pfms-ui/package.json` | Confirm production build command and CI build behavior. |
| `pfms-ui/Dockerfile` | Create later for production static UI serving. |

### API Gateway

| File | Future change |
|---|---|
| `api-gateway/src/main/resources/application.properties` | Remove Config Server localhost import for MVP profile and make runtime config env-driven. |
| `api-gateway/src/main/resources/application-docker.properties` | Stop using `host.docker.internal` Config Server import for MVP. |
| `api-gateway/src/main/resources/application-sit.properties` | Do not use hardcoded local MySQL root credentials for MVP. |
| `api-gateway/src/main/resources/bootstrap.yml` | Remove or neutralize incorrect local Config Server URI for MVP. |
| `config-repo/api-gateway.properties` | Extract needed gateway route/JWT/JPA settings into service-local MVP config; remove hardcoded secrets from deployable path. |
| `api-gateway/src/main/java/com/delose/pfms/api_gateway/ApiGatewayApplication.java` | Remove `@EnableDiscoveryClient` or make discovery disabled for MVP. |
| `api-gateway/src/main/java/com/delose/pfms/api_gateway/config/SecurityConfiguration.java` | Make CORS origins configurable. |
| `api-gateway/src/main/java/com/delose/pfms/api_gateway/config/SecurityWebFluxConfiguration.java` | Make CORS origins configurable and review actuator path permissions. |
| `api-gateway/src/main/java/com/delose/pfms/api_gateway/service/JwtService.java` | Keep secret read from config/env only; no hardcoded fallback. |
| `api-gateway/Dockerfile` | Replace prebuilt-JAR-only image flow with multi-stage build or documented CI artifact flow. |
| `api-gateway/docker-build.sh` | Stop tagging `delose/api-gateway:latest` for deployable builds. |
| `api-gateway/run-docker.sh` | Replace `host.docker.internal`, hardcoded root/secret, Eureka env, and `latest` image tag for MVP testing. |
| `api-gateway/db-run.sh` | Replace hardcoded local MySQL credentials if retained for local testing, or supersede with MVP compose. |

### Budget Service

| File | Future change |
|---|---|
| `budget-service/src/main/resources/application.yml` | Add MVP profile defaults; remove `host.docker.internal` OTLP endpoint from deployable path; expose health/info/metrics deliberately. |
| `budget-service/src/main/resources/application-dev.yml` | Avoid using Config Server localhost and Kafka as default MVP dependencies. |
| `budget-service/src/main/resources/application-docker.yml` | Avoid `host.docker.internal` Config Server/Eureka and Kafka defaults for MVP. |
| `config-repo/budget-service.yml` | Replace H2 deployable settings with MySQL MVP settings or stop relying on config-repo for MVP. |
| `budget-service/src/main/java/com/delose/pfms/budget_service/BudgetServiceApplication.java` | Remove `@EnableDiscoveryClient` or make discovery disabled for MVP. |
| `budget-service/src/main/java/com/delose/pfms/budget_service/controller/BudgetControllerV1.java` | Remove `EurekaClient` dependency and replace `/greeting` with a discovery-free response, or rely on actuator health. |
| `budget-service/src/main/java/com/delose/pfms/budget_service/service/BudgetService.java` | Make notification event publication conditional on a disabled-by-default MVP flag. |
| `budget-service/src/main/java/com/delose/pfms/budget_service/producer/BudgetNotificationHandler.java` | Make handler conditional on notifications enabled. |
| `budget-service/src/main/java/com/delose/pfms/budget_service/producer/BudgetNotificationProducer.java` | Make producer conditional on notifications enabled. |
| `budget-service/src/main/java/com/delose/pfms/budget_service/config/KafkaTopicConfig.java` | Make topic config conditional on notifications enabled. |
| `budget-service/Dockerfile` | Replace prebuilt-JAR-only image flow with multi-stage build or documented CI artifact flow; expose normalized port. |
| `budget-service/docker-build.sh` | Stop tagging `delose/budget-service:latest` for deployable builds. |
| `budget-service/run-docker.sh` | Remove Kafka and Eureka env requirements for MVP testing. |

### Local MVP Compose and CI

| File | Future change |
|---|---|
| `docker-compose.mvp.yml` or equivalent PFMS-local compose file | Create later with only MySQL, API gateway, budget-service, and UI. |
| `.env.example` or MVP-specific env example | Create later with placeholder-only variables. |
| `.github/workflows/*` | Create later only after registry and build scope are approved. |

## Exact Commands to Test Later

These commands are for later implementation work, not for this planning step.

PFMS source checks:

```bash
cd /home/wajih/sandbox/pfms-audit
./mvnw -pl api-gateway -am test
./mvnw -pl budget-service -am test
cd pfms-ui
npm ci
npm run build
```

Local MVP Docker Compose checks, after an MVP compose file exists:

```bash
cd /home/wajih/sandbox/pfms-audit
docker compose -f docker-compose.mvp.yml config
docker compose -f docker-compose.mvp.yml up --build
curl -fsS http://localhost:8080/actuator/health
curl -fsS http://localhost:8080/v1/api/budgets/categories
curl -fsS http://localhost:8082/actuator/health
docker compose -f docker-compose.mvp.yml down
```

Phoenix-Ops GitOps checks, after manifests exist:

```bash
cd /home/wajih/phoenix-aiops
find gitops/apps/pfms-mvp -type f -maxdepth 4 -print
kubectl kustomize gitops/apps/pfms-mvp
kubectl kustomize gitops/environments/dev/pfms-mvp
kubectl --dry-run=client -f <rendered-manifest-file>
```

Do not run live `kubectl apply` without explicit approval.

## Implementation Order

1. Patch PFMS selected-service config to support an MVP profile without Config Server.
2. Remove or disable Eureka from `api-gateway` and `budget-service`.
3. Replace gateway `lb://budget-service` route with direct `budget-service` HTTP route.
4. Make budget-service Kafka notification publishing disabled by default.
5. Move `budget-service` from H2 deployable config to MySQL MVP config.
6. Make UI gateway URL configurable and remove the direct hardcoded budget URL.
7. Normalize the UI health check around actuator or a discovery-free endpoint.
8. Add production Dockerfiles or documented CI artifact image builds for selected services.
9. Add a PFMS-local `docker-compose.mvp.yml` for smoke testing.
10. Run local tests and compose smoke tests.
11. Choose an image registry and immutable tag convention.
12. Add Phoenix-Ops GitOps manifests with dummy Secret templates only.
13. Add a manual-sync Argo CD Application template only after image and Git paths are known.
14. Deploy only after explicit user approval.

## Risks

- `budget-service` Kafka coupling may prevent startup until producer/topic beans and event publishing are made conditional.
- `budget-service` Eureka coupling is in source code, not just config, because the controller injects `EurekaClient`.
- `api-gateway` currently has both discovery-based gateway routes and discovery annotations.
- Moving `budget-service` from H2 to MySQL may expose schema, dialect, or migration issues because there are no visible Flyway/Liquibase migrations.
- UI fallback mock data can hide backend failures during demo testing unless smoke tests assert backend calls.
- JWT and CORS settings are currently hardcoded in config/source and must become explicit env/Secret/ConfigMap inputs.
- Existing Dockerfiles depend on prebuilt JARs, which can make CI and image rebuilds brittle.
- No registry has been selected, so GitOps image references must remain placeholders.
- Database credentials must be provided through a real secret process later; dummy templates are not deployable.

## Final Decision

Phoenix-Ops should implement PFMS as a reduced MySQL-backed MVP slice, not as a full PFMS adoption. The first implementation pass should focus on making the selected services boot without Config Server, Eureka, Kafka, Consul, or RabbitMQ, then prove the slice locally with Docker Compose before any Kubernetes or Argo CD work.
