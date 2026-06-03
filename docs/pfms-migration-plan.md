# PFMS Migration Plan for Phoenix-Ops

## Goal

Turn PFMS from a local educational microservice repository into a controlled Phoenix-Ops lab workload that can be deployed through GitOps after validation.

This plan does not deploy anything. It defines the recommended migration sequence.

## Phase 0: Freeze the Workload Slice

Choose the first deployable subset:

- `pfms-ui`
- `api-gateway`
- `budget-service`
- `config-server` only if required after simplification
- `discovery-server` only if Eureka routing remains required
- One database for API gateway users
- Optional Kafka and `notification-service` if event flow is needed

Defer these until later:

- `account-service`
- `transaction-service`
- `expense-service`
- `goal-service`
- `analytics-service`
- `reporting-service`
- n8n, Portainer, Kafka UI, Grafana, Jaeger as app-owned dependencies

## Phase 1: Build and Runtime Contract

Define one contract per selected service:

- Container image name and immutable tag policy.
- Runtime port.
- Health, readiness, and liveness path.
- Required environment variables.
- Required ConfigMap keys.
- Required Secret keys.
- Required dependencies.

Do not create Phoenix-Ops GitOps manifests until this contract is documented.

## Phase 2: Remove Localhost Assumptions

Replace these patterns with configuration:

- `localhost`
- `127.0.0.1`
- `host.docker.internal`
- hardcoded dashboard URLs
- hardcoded CORS origins
- hardcoded Kafka/RabbitMQ/Eureka/Consul endpoints

For K3s, target Kubernetes service DNS names such as:

```text
api-gateway.<namespace>.svc.cluster.local
budget-service.<namespace>.svc.cluster.local
```

Use placeholders in documentation until actual service names are finalized.

## Phase 3: Secrets and Config Hygiene

Remove hardcoded secrets from deployable config:

- JWT signing secret.
- MySQL root/user passwords.
- MongoDB credentials.
- RabbitMQ credentials.
- Grafana admin password.
- Any demo credentials used outside demo docs.

Create only Secret templates in Phoenix-Ops. Do not commit real values.

## Phase 4: Containerization Fixes

For each selected service:

- Use reproducible dependency install commands.
- Prefer multi-stage builds where practical.
- Avoid prebuilt artifact requirements unless CI produces artifacts explicitly.
- Stop using `latest` for GitOps deployments.
- Add non-root runtime where feasible.
- Add image labels and consistent exposed ports.

## Phase 5: Kubernetes Manifests or Helm

Start with a minimal declarative baseline:

- Namespace.
- ConfigMaps.
- Secret templates.
- Deployments.
- Services.
- Readiness/liveness probes.
- Resource requests/limits.

Keep sync manual in Argo CD. Do not enable auto-sync until smoke tests are reliable.

## Phase 6: Dependency Strategy

Decide ownership for dependencies:

- Run database/broker dependencies in-cluster for lab realism, or
- Keep them external/manual for the first MVP.

For Phoenix-Ops MVP, prefer the smallest viable dependency set. Avoid deploying Kafka, RabbitMQ, Consul, Eureka, Config Server, and multiple databases all at once.

## Phase 7: Observability

Add platform-friendly observability after the app runs:

- Standard health endpoints.
- Prometheus scrape annotations or ServiceMonitor templates.
- Structured logs.
- Trace endpoint config through environment variables.
- Minimal alerts for service down, high restart count, and failed readiness.

## Phase 8: Argo CD Adoption

Create Argo CD Application templates only after:

- Image tags are known.
- Git path is known.
- Secret process is documented.
- Kustomize or Helm rendering passes locally.
- Manual kubectl dry-run succeeds when approved.

Initial Argo CD settings:

- Manual sync only.
- No auto-prune.
- No self-heal.
- No public ingress.

## Recommended First Milestone

Deliver a minimal PFMS slice in Phoenix-Ops:

```text
pfms-ui -> api-gateway -> budget-service -> database
```

Optional event extension:

```text
budget-service -> Kafka -> notification-service
```

This creates enough operational surface for AIOps without importing the full repository complexity at once.
