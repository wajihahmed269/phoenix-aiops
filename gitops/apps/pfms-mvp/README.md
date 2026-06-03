# PFMS MVP GitOps App

This directory contains declarative manifests for the PFMS MVP demo workload:

```text
pfms-ui -> api-gateway -> budget-service -> mysql
```

The full PFMS system is intentionally not deployed here. Kafka, Eureka, Config Server, RabbitMQ, and Consul are intentionally disabled for this MVP slice.

Images are placeholders and must be replaced with immutable tags after the selected images are built and pushed to an approved registry. The Secret manifest is a dummy template only and is not production-ready.

The Argo CD `Application` template is kept separate from `kustomization.yaml` and must remain manual-sync. Do not enable automated sync, prune, or self-heal for the first rollout.

Deploy only after:

- PFMS MVP images have been pushed to a registry.
- Dummy secrets have been replaced through an approved secret process.
- Rendered manifests have been reviewed.
- A human explicitly approves deployment.
