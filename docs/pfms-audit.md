# PFMS Operational Architecture Audit

## Scope

Repository audited: `https://github.com/delose/personal-finance-management-system`

Local clone: `/home/wajih/sandbox/pfms-audit`

Audited commit: `b40b095794793168540dc8b3e65fccbad79afffe`

This audit is inspection-only. No PFMS services were started, no Kubernetes manifests were applied, and no Phoenix-Ops infrastructure was changed.

## Executive Recommendation

Recommendation: **partially suitable**.

PFMS is useful for Phoenix-Ops as a realistic, noisy, polyglot microservices workload after a controlled operationalization pass. It is not currently production-worthy or GitOps-ready. The repository has enough architectural surface area to exercise AIOps workflows: multiple runtimes, service discovery, messaging, databases, auth, health checks, local Docker scripts, tracing docs, and a partial Helm chart. However, the deployment model is inconsistent and heavily localhost-oriented, with hardcoded credentials, incomplete charting, startup-order risk, and uneven service maturity.

Use PFMS as a staged lab workload, not as a direct production-style deployment target yet.

## Architecture Summary

PFMS is a polyglot personal finance microservice system with:

- React frontend in `pfms-ui/`.
- Spring Boot API gateway with JWT auth in `api-gateway/`.
- Spring Boot services for budgets, goals, notifications, config, and discovery.
- NestJS services for transactions and accounts.
- Laravel expense service.
- Go analytics service.
- Python/FastAPI reporting service.
- Kafka for budget/notification flow.
- RabbitMQ for transaction/account flow.
- Eureka and Consul both used for service discovery.
- Config Server backed by the same GitHub repository and `config-repo/`.
- Local observability examples with Jaeger, Prometheus, Grafana, Kafka UI, Portainer, and dashboard links.

The architecture is ambitious and educational, but it is not coherent enough for direct K3s/Argo CD adoption without pruning and standardization.

## Repository Structure

Key top-level areas:

| Path | Purpose | Operational maturity |
|---|---|---|
| `pfms-ui/` | React frontend | Functional local dev shape, hardcoded API URLs |
| `api-gateway/` | Spring Boot gateway/auth | Real auth components, but config/security concerns |
| `budget-service/` | Spring Boot budget API and Kafka producer | Most complete domain service |
| `goal-service/` | Spring Boot goals API | Basic CRUD and health, H2 default |
| `notification-service/` | Spring Boot Kafka consumer and MongoDB usage | Partial, hardcoded Mongo URI |
| `account-service/` | NestJS RabbitMQ consumer | Thin demo service, no real DB usage despite compose DB |
| `transaction-service/` | NestJS RabbitMQ producer and Consul registration | Thin demo gateway/service |
| `expense-service/` | Laravel service | Scaffold with API resource and Sail compose |
| `analytics-service/` | Go service | Minimal health and analytics endpoint only |
| `reporting-service/` | FastAPI service | Minimal health and Consul registration |
| `config-server/` | Spring Cloud Config Server | Points at GitHub repo `config-repo` |
| `discovery-server/` | Eureka server | Basic service registry |
| `config-repo/` | Centralized config | Contains hardcoded secrets and localhost values |
| `kafka/`, `message-broker/`, `consul-server/`, `jaeger/`, `n8n/` | Local middleware compose stacks | Useful for local demo, not production-ready |
| `pfms-chart/` | Helm umbrella chart | Incomplete; scaffolded values and no templates found |
| `k8s/` | Kubernetes notes | README only, not deployable manifests |

## Service Inventory

| Service | Runtime | Port evidence | Data store | Messaging | Discovery | Health evidence |
|---|---:|---:|---|---|---|---|
| `pfms-ui` | React | 3000 | None | None | None | No backend health; UI probes hardcoded localhost |
| `api-gateway` | Spring Boot | 8080 | MySQL `apigwdb` | None | Eureka | Actuator configured |
| `config-server` | Spring Boot | 8888 | Git config repo | None | Eureka | Actuator configured |
| `discovery-server` | Spring Boot/Eureka | 8761 | None | None | Eureka server | Actuator health |
| `budget-service` | Spring Boot | 8082 in config, README claims mixed ports | H2 by default, README says PostgreSQL | Kafka producer | Eureka | Actuator health/metrics |
| `goal-service` | Spring Boot | 8084 | H2 by default | Kafka dependency present, no strong flow found | Consul | `/goal-health-check`, actuator |
| `notification-service` | Spring Boot | 8085 | MongoDB URI with `admin:secret` | Kafka consumer | Consul | `/notif-health-check`, actuator |
| `transaction-service` | NestJS | HTTP 3004, TCP 3002 | Compose Postgres declared, source does not use it meaningfully | RabbitMQ producer | Consul | `/health` |
| `account-service` | NestJS | 3003 | Compose Postgres declared, source does not use it meaningfully | RabbitMQ consumer | None | `/health` |
| `expense-service` | Laravel | 80/5173 through Sail | MySQL/SQLite config | None | Consul scripts mentioned | `/api/health` |
| `analytics-service` | Go | Dockerfile exposes 8081 | None in source despite TimescaleDB claim | None in source despite Kafka claim | None | `/health` |
| `reporting-service` | FastAPI | 8000 | None in source | Dependencies include Kafka/Rabbit libraries | Consul | `/health` |

## Frontend/Backend Split

The frontend is clearly separated under `pfms-ui/`, but it is not environment-ready:

- API base URL is hardcoded to `http://localhost:8080` in `pfms-ui/src/services/api.ts`.
- Additional pages/components call hardcoded localhost URLs for expenses, dashboard, service health, Eureka, Consul, RabbitMQ, Kafka UI, Portainer, Prometheus, and Grafana.
- Auth tokens are stored in `localStorage`; acceptable for a lab but not ideal for production without a stronger browser security model.
- The UI includes architecture visualization and health polling, which is useful for Phoenix-Ops demonstrations after URLs become configurable.

## Database Dependencies

Observed database dependencies are inconsistent:

- API gateway uses MySQL with `root` and `secret` in local/docker config.
- Budget and goal services use H2 defaults despite docs claiming PostgreSQL.
- Notification service uses MongoDB with `admin:secret` and port `3308` mapped to MongoDB `27017`.
- Account and transaction compose files declare Postgres but source services are mostly RabbitMQ demo handlers.
- Expense service uses Laravel defaults with SQLite/MySQL via `.env.example` and Sail compose.
- Analytics docs claim TimescaleDB, but the Go source has no DB integration.

Production implication: the data layer must be redesigned before K8s. PFMS currently mixes demo persistence, documentation claims, and runtime config in ways that will not migrate cleanly.

## Messaging Systems

PFMS includes both Kafka and RabbitMQ:

- Kafka is used by `budget-service` producer and `notification-service` consumer on topic `notification_requests_topic`.
- RabbitMQ is used by `transaction-service` and `account-service`, with `guest:guest` and `host.docker.internal` hardcoded in source/compose.
- Kafka compose uses `localhost:9092` advertised listener and a fixed cluster ID, which is local-machine oriented.
- Message names and docs differ: README mentions `budget.created`, while code uses `notification_requests_topic`.

Production implication: Phoenix-Ops can use messaging failures as AIOps scenarios, but first the topics, queues, service names, and broker endpoints need one canonical contract.

## Authentication Systems

API gateway contains real JWT auth pieces:

- `/auth/signup` and `/auth/login` exist.
- Passwords are encoded with BCrypt.
- JWT generation and validation exist.
- WebFlux and servlet security configurations both exist, which increases ambiguity.

Concerns:

- JWT secret is hardcoded in `config-repo/api-gateway.properties`.
- CORS origins are hardcoded to localhost ports.
- `/dashboard` and `/actuator` are permitted in WebFlux config.
- Debug logging for Spring Security is enabled in config.
- No production secret injection model exists.

## Config Management and Environment Variables

Config management exists but is not production safe:

- Spring Cloud Config Server points to the public GitHub repository and `config-repo/`.
- Config files contain local URLs, `host.docker.internal`, and hardcoded passwords/secrets.
- Several services depend on `SPRING_PROFILES_ACTIVE=docker` scripts rather than a clean environment contract.
- NestJS services use some env vars but still fall back to hardcoded localhost/host.docker.internal and `guest:guest`.
- Frontend does not use build-time environment variables for API URLs.

Production implication: PFMS needs a complete config contract before GitOps. ConfigMaps and Secret templates can be generated only after removing hardcoded runtime assumptions.

## Docker Support

Docker support is broad but uneven:

Strengths:

- Most backend services have Dockerfiles.
- Several services include local run/build scripts.
- Middleware compose stacks exist for Consul, Kafka, RabbitMQ, Jaeger, n8n, Prometheus/Grafana in one service folder.

Weaknesses:

- Java Dockerfiles require prebuilt JARs copied from `target/`, so image builds depend on external build order.
- Node Dockerfiles use `npm install` instead of reproducible `npm ci`.
- Several images/scripts tag `delose/<service>:latest`, which is not suitable for GitOps or immutable deployments.
- `expense-service` has Sail compose but no service Dockerfile found in the top-level service listing.
- `reporting-service/Dockerfile` copies `uv.lock`, but no `uv.lock` was found.
- Compose files use `host.docker.internal`, fixed host ports, local credentials, and local-only advertised listeners.
- `run-pfms.sh` kills processes with `kill -9` on port 3000.
- Startup orchestration is script-based and does not wait for all dependencies to become healthy.

Docker readiness score: **4/10**.

## Docker Compose Support

Compose is split per service/middleware, not a reliable whole-system composition:

- No single root compose file defines the whole dependency graph.
- `run-pfms.sh` starts MongoDB and backend scripts but does not call the middleware launcher consistently.
- Per-service compose files often include private DB containers that conflict on host ports or do not match source code usage.
- Kafka, RabbitMQ, Consul, Jaeger, n8n, Portainer, Prometheus, and Grafana are local demo tools, not production deployment definitions.

## Kubernetes and Helm Support

Kubernetes readiness is low:

- `k8s/README.md` is Docker Desktop/kubectl notes, not manifests.
- `pfms-chart/` is an umbrella chart with only three subcharts: account-service, api-gateway, budget-service.
- No Helm templates were found under `pfms-chart/`; only scaffolded `values.yaml` files exist.
- Subchart values default to `image.repository: nginx` and `chart-example.local`, showing the chart is scaffold-level.
- Most services are missing Helm entries entirely.
- No external dependency charts or stateful deployment strategy exists for MySQL, MongoDB, Postgres, Kafka, RabbitMQ, Consul, Eureka, or Config Server.

Kubernetes readiness score: **2/10**.

## CI/CD Workflows

No `.github/workflows` directory was found in the clone. The repo has local build scripts and Maven/npm/composer/go/uv manifests, but no central CI pipeline.

CI/CD maturity score: **1/10**.

## Observability Support

Observability is present as an idea and partially implemented:

Strengths:

- Spring Boot actuator exists in several Java services.
- Budget/notification include Micrometer tracing and OTLP endpoint configuration.
- Jaeger compose and documentation exist.
- Goal service has Prometheus/Grafana compose and Prometheus config.
- UI has an architecture/health dashboard concept.

Weaknesses:

- OTLP endpoints are hardcoded to `host.docker.internal`.
- No Kubernetes ServiceMonitor or PodMonitor manifests are ready.
- No centralized logging plan.
- No alert rules.
- No consistent health endpoint contract across services.
- Observability docs are local-demo oriented.

Observability readiness score: **4/10**.

## Deployment Dependency Graph

A realistic startup order inferred from files:

```text
Base runtime dependencies
  -> MySQL for api-gateway users
  -> MongoDB for notification-service
  -> Kafka + Kafka UI
  -> RabbitMQ
  -> Consul
  -> Config Server dependencies

Discovery/config layer
  -> discovery-server/Eureka
  -> config-server, which reads config-repo from GitHub

Application layer
  -> api-gateway, depends on MySQL, Config Server, Eureka
  -> budget-service, depends on Config Server, Eureka, Kafka, H2/default DB
  -> goal-service, depends on Consul, H2/default DB, optional Redis config
  -> notification-service, depends on Kafka, MongoDB, Consul
  -> transaction-service, depends on RabbitMQ, Consul
  -> account-service, depends on RabbitMQ
  -> expense-service, depends on Laravel app config and MySQL/SQLite
  -> analytics-service, currently mostly standalone
  -> reporting-service, depends on Consul for registration

Frontend
  -> pfms-ui, depends on api-gateway and hardcoded local service/dashboard URLs
```

Startup ordering risks:

- Scripts build and start services sequentially but do not prove dependencies are healthy.
- Config Server and Eureka have circular-ish timing risk because services import config and register/fetch discovery.
- Kafka/RabbitMQ readiness is not checked before producers/consumers start.
- Config Server clones from GitHub at runtime, making startup network-dependent.
- Docker host networking assumptions will fail inside Kubernetes without changes.

## Broken or Incomplete Areas

- README claims a production-ready system, but several services are thin demos or scaffolds.
- Helm chart is incomplete and contains scaffold defaults such as `nginx` images.
- No root compose file fully models the system.
- `reporting-service/Dockerfile` references `uv.lock`, but no lock file was found.
- API gateway uses both servlet and WebFlux security config, increasing configuration ambiguity.
- README service ports conflict with code/config in places.
- Claims for TimescaleDB, AI advisor, and some analytics/reporting capabilities are not backed by complete service implementations in the inspected files.
- Multiple services have DB dependencies in docs/compose that are not clearly used in source.

## Hardcoded Localhost and Host-Specific Usage

Frequent hardcoded values were found:

- `http://localhost:8080` in frontend API service.
- Multiple frontend dashboard links to localhost services.
- `host.docker.internal` in Spring configs, NestJS source, run scripts, and compose files.
- Kafka advertised listener uses `EXTERNAL://localhost:9092`.
- Consul and Eureka URLs use localhost or host.docker.internal.
- CORS origins are hardcoded to localhost ports.

Kubernetes implication: most service-to-service communication must be replaced with Kubernetes DNS names and config-driven endpoints.

## Hardcoded Credentials and Insecure Configs

Examples found:

- MySQL root password `secret` in API gateway configs/scripts.
- JWT secret values committed in `config-repo/api-gateway.properties`.
- MongoDB URI `mongodb://admin:secret@...` in notification configs.
- RabbitMQ `guest:guest` in source and compose.
- Postgres `pfms/pfms` in account and transaction compose files.
- Grafana admin password `admin` in compose.
- Demo credentials documented as `demo@pfms.dev` / `demo123`.
- Actuator exposure uses `*` in several configs.
- Portainer mounts `/var/run/docker.sock` in local compose.

These are acceptable for a local educational repo but must not enter Phoenix-Ops GitOps as real secrets.

## Health Endpoints

Health coverage is mixed:

- Spring services often expose actuator health or custom health endpoints.
- NestJS services expose `/health`.
- Expense service exposes `/api/health`.
- Analytics service exposes `/health`.
- Reporting service exposes `/health`.

Gaps:

- No consistent readiness/liveness paths across all services.
- Health endpoints do not consistently verify dependencies such as DB, Kafka, RabbitMQ, Consul, Config Server, or Eureka.
- Frontend health logic is hardcoded to local endpoints.

## Kubernetes Migration Challenges

Major challenges for Phoenix-Ops/K3s:

1. Convert localhost/host.docker.internal to Kubernetes service DNS.
2. Decide whether to keep both Eureka and Consul or simplify service discovery.
3. Replace demo credentials with Secret templates and external secret handling.
4. Normalize ports and health endpoint paths.
5. Build immutable images with pinned tags and real registry strategy.
6. Create complete Helm charts or Kustomize manifests for every selected service.
7. Add dependency readiness, init checks, and restart-safe behavior.
8. Separate local demo tools from required runtime dependencies.
9. Add persistent volume strategy for databases and brokers if they run in-cluster.
10. Remove runtime dependency on cloning config from GitHub inside Config Server, or make it explicit and private-safe.

## Argo CD Challenges

- No complete deployable chart exists today.
- Image tags are `latest` or placeholders, not immutable.
- Hardcoded secrets cannot be committed to GitOps.
- Sync waves/hooks would be needed for dependencies, but the current dependency graph is not clean.
- Auto-sync would be unsafe until startup order and health gates are fixed.
- Config Server fetching from GitHub can create drift between GitOps desired state and runtime config state.
- External services such as Kafka/RabbitMQ/Consul/Eureka/DBs need a deliberate ownership model before Argo CD can manage them.

## Production Readiness Evaluation

| Category | Score | Notes |
|---|---:|---|
| Containerization quality | 4/10 | Broad Docker coverage, but many images depend on prebuilt artifacts, local host assumptions, and `latest` tags |
| Microservice realism | 6/10 | Strong variety of patterns, but uneven implementation depth and inconsistent contracts |
| Deployment complexity | 8/10 | High complexity due to many runtimes, brokers, DBs, service discovery systems, and config server |
| Maintainability | 4/10 | Large educational surface, but inconsistent ports, configs, scripts, and service maturity |
| Documentation quality | 5/10 | Extensive docs, but many claims exceed deployable reality |
| Operational maturity | 3/10 | Partial health/observability, weak CI/CD, incomplete Helm, hardcoded credentials |

## Estimated Effort to Operationalize for Phoenix-Ops

Minimum viable Phoenix-Ops workload, using a reduced subset:

- Effort: **2-4 days**.
- Scope: UI, API gateway, budget service, config/discovery if needed, one database, Kafka optional.
- Output: 3-5 services with clean images, Secret templates, ConfigMaps, health checks, and manual Argo CD sync.

Full PFMS operationalization:

- Effort: **2-4 weeks**.
- Scope: all runtimes, all brokers, all DBs, both discovery systems or a simplification, full Helm/Kustomize, CI, observability, secrets, startup ordering, smoke tests.
- Risk: high unless the service inventory is reduced and contracts are frozen first.

## Strongest Architectural Points

- Rich polyglot microservice surface suitable for AIOps demos.
- Real API gateway auth components with JWT and BCrypt.
- Kafka and RabbitMQ flows can create useful operational failure scenarios.
- Existing health endpoints and actuator support provide a starting point.
- Local tracing/Jaeger documentation shows intent for observability.
- UI architecture dashboard is valuable for Phoenix-Ops demonstration after endpoint config is fixed.

## Major Risks

- Direct deployment to K3s would likely fail due to local-host assumptions and incomplete manifests.
- Hardcoded credentials and JWT secrets are not safe for GitOps.
- The Helm chart is not currently a deployable representation of the app.
- Mixed service discovery systems add complexity without clear production benefit.
- Several services are demo-level and do not match README claims.
- No CI/CD means build reliability is unknown.
- Startup order and dependency health are not controlled enough for Argo CD.

## Final Recommendation

Adopt PFMS only as a **partially suitable** workload after a narrowing pass.

For Phoenix-Ops, the best path is to start with a reduced PFMS slice:

1. API gateway.
2. React UI.
3. Budget service.
4. One database backing auth/budget data.
5. Kafka plus notification service only if messaging is required for the demo.

Do not attempt full PFMS deployment first. The full repository is too inconsistent for a first GitOps workload and would distract from Phoenix-Ops platform validation.
