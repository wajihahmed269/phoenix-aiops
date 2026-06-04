# Phoenix-Ops Observability

This directory contains the lightweight foundational observability stack for the Phoenix-Ops K3s lab.

Components:

- Prometheus for metrics
- Grafana for dashboards
- Loki for log storage
- Promtail for node-local container log collection
- kube-state-metrics for Kubernetes object state
- node-exporter for node CPU, memory, filesystem, and host metrics

The stack is intentionally internal-only. Services are `ClusterIP`; use port-forwarding for demos and debugging. Do not add Ingress, LoadBalancer, or public dashboard exposure in this phase.

## Runtime Secrets

`grafana-secret-template.yaml` is dummy-only and intentionally not included in `kustomization.yaml`. Create the real `grafana-admin-secret` in the `observability` namespace before manual Argo CD sync.

Required keys:

```text
admin-user
admin-password
```

## Validation

```bash
kubectl kustomize gitops/apps/observability
kubectl kustomize gitops/environments/dev/observability
kubectl apply --dry-run=client --validate=false -k gitops/apps/observability
```

## Manual Sync

The Argo CD Application uses manual sync only:

```text
repoURL: https://github.com/wajihahmed269/phoenix-aiops.git
targetRevision: HEAD
path: gitops/environments/dev/observability
```

Automated sync, prune, and self-heal are intentionally not configured.

## Demo Access

```bash
kubectl -n observability port-forward svc/grafana 3000:3000
kubectl -n observability port-forward svc/prometheus 9090:9090
```

Then browse `http://localhost:3000` for Grafana or `http://localhost:9090` for Prometheus.

## BankApp Visibility

Immediate visibility comes from Kubernetes state metrics, cAdvisor/container metrics, and Loki logs for the `bankapp` namespace. The current BankApp backend image does not expose Actuator Prometheus metrics, so direct application metrics should be added later through an app-image change that exposes `/actuator/prometheus`.
