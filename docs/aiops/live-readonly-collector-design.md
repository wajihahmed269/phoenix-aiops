# Live Read-Only Collector Design

## Goal

Connect the AI remediation service to real cluster telemetry without introducing write paths.

## Collector Boundaries

### Prometheus collector

- HTTP GET only
- bounded timeout
- narrow endpoint: `/api/v1/targets`
- emits `target_down` incidents only

### Loki collector

- bounded query range
- namespace allowlist only
- max log lines cap
- sanitizes obvious secret-like tokens
- emits `log_anomaly` incidents only when repeated signal exists

### Kubernetes collector

- explicit `kubectl --kubeconfig ~/.kube/phoenix-k3s-oci.yaml`
- subprocess allowlist: `get`, `top`, `describe`
- no `apply`, `patch`, `delete`, `rollout`, `scale`, or `exec`
- emits:
  - `pod_crashloop`
  - `repeated_restart`
  - `deployment_unhealthy`
  - `high_memory`

### Argo collector

- read-only `kubectl get applications.argoproj.io -A -o json`
- emits application drift or degraded health as incidents
- never syncs applications

## Local Runtime Model

The service runs locally and talks to:

- Kubernetes and Argo via `kubectl`
- Prometheus and Loki via local URLs, typically through operator-managed port-forwards

This keeps access narrow and operator-controlled.
