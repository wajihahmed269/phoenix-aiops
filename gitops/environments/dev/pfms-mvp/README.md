# PFMS MVP Dev Environment

This environment renders the PFMS MVP demo workload for development validation:

```text
pfms-ui -> api-gateway -> budget-service -> mysql
```

The full PFMS platform is intentionally not included. Kafka, Eureka, Config Server, RabbitMQ, and Consul are disabled for this slice.

Image references are placeholders and must be replaced only after images are pushed to an approved registry. Secret values are dummy templates and must not be used as production credentials.

Argo CD sync must remain manual. Do not enable automated sync, prune, or self-heal until the deployment process has been reviewed and explicitly approved.
