# Observability Rollout Report

## Scope

- Deployed through `argocd/observability` on OCI K3s using `~/.kube/phoenix-k3s-oci.yaml`
- No public ingress or LoadBalancer exposure added for observability
- Grafana admin secret created manually in `observability`
- Stabilization completed through GitOps revisions `021880b` and `e82d083`

## What Was Deployed

- Namespace: `observability`
- Deployments: `prometheus`, `loki`, `grafana`, `kube-state-metrics`
- DaemonSets: `promtail`, `node-exporter`
- Services: all `ClusterIP`
- PVCs: `prometheus-data` 5Gi, `loki-data` 5Gi
- Argo CD Application: `argocd/observability`

## Final Working State

- `argocd/observability` is `Synced` and `Healthy` at revision `e82d083`
- All observability pods are `Running`
- Prometheus pod is `Running`; `/-/healthy` and `/-/ready` return OK
- Loki pod is `Running`; `/ready` returns OK
- Loki labels are present: `app`, `container`, `filename`, `namespace`, `pod`, `stream`
- Loki query `{namespace="bankapp"}` returns BankApp logs
- Grafana pod is `Running`; `/login` returns 200 and `/api/health` reports `database: ok`
- Grafana datasources are provisioned: `Prometheus`, `Loki`
- Grafana dashboards are loaded: `BankApp Operations`, `Phoenix Cluster Health`
- Node exporter is running on all five nodes
- Promtail is running on all five nodes
- Prometheus PVC and Loki PVC are both `Bound`

## What Failed And Was Fixed

### Promtail and Loki ingestion

Problem:
- Promtail discovered `0/0` targets, tailed no files, and pushed no log lines
- Loki labels were empty and BankApp queries returned zero results

Root cause:
- Promtail relied on `HOSTNAME` for node-local Kubernetes pod discovery
- In the DaemonSet, the default hostname was the pod name instead of the node name

Fix:
- Commit `021880b Fix promtail node-local pod discovery`
- Added `HOSTNAME` from `spec.nodeName` in `gitops/apps/observability/promtail-daemonset.yaml`
- Synced through Argo CD and verified successful rollout

Result:
- Promtail target discovery works
- Loki ingestion works
- BankApp frontend logs are visible in Loki
- Earlier `10.43.0.1:443 connect: no route to host` messages appear to have been transient startup noise

### kube-state-metrics health probes

Problem:
- `kube-state-metrics` was in `CrashLoopBackOff`
- Kubelet reported probe failures with `404` on `/readyz` and `/livez`

Root cause:
- The image `registry.k8s.io/kube-state-metrics/kube-state-metrics:v2.14.0` starts cleanly, but those probe paths are not served on the telemetry port in this runtime

Fix:
- Commit `e82d083 Fix kube-state-metrics health probes`
- Switched readiness and liveness probes to `/metrics` on the telemetry port in `gitops/apps/observability/kube-state-metrics-deployment.yaml`
- Synced through Argo CD and verified rollout completed successfully

Result:
- `kube-state-metrics` is now `1/1 Running`
- `argocd/observability` moved from `Progressing` to `Healthy`

## Prometheus kubelet/cAdvisor Decision

Current state:
- Prometheus has `9` targets `up` and `10` targets `down`
- All down targets are the `kubernetes-kubelet` and `kubernetes-cadvisor` jobs
- Each failure is `403 Forbidden` from direct kubelet access on `https://<node-ip>:10250`

Assessment:
- Current Prometheus RBAC is sufficient for Kubernetes API discovery
- The failures are from kubelet authorization, not missing Kubernetes API RBAC
- We should not weaken kubelet security for this lab just to make those scrapes work

Prepared local-only patch:
- File: `gitops/apps/observability/prometheus-configmap.yaml`
- Removes the `kubernetes-kubelet` and `kubernetes-cadvisor` scrape jobs
- Dry-run passed
- Not committed and not synced yet

Recommended lab posture:
- Disable those two scrape jobs
- Rely on `node-exporter` plus `kube-state-metrics` for node and Kubernetes-state visibility

## Resource Usage Before And After

### Before rollout baseline

- `controlplane`: 67m CPU, 2248Mi memory, 37%
- `app`: 15m CPU, 1542Mi memory, 26%
- `observatory`: 13m CPU, 1336Mi memory, 22%
- `aiops`: 12m CPU, 1137Mi memory, 19%
- `ollama`: 24m CPU, 1676Mi memory, 28%

### Current stabilized snapshot

- `controlplane`: 74m CPU, 2353Mi memory, 39%
- `app`: 21m CPU, 1627Mi memory, 27%
- `observatory`: 25m CPU, 1476Mi memory, 24%
- `aiops`: 31m CPU, 1320Mi memory, 22%
- `ollama`: 35m CPU, 1723Mi memory, 29%

### Current observability pod memory snapshot

- `grafana`: 69Mi
- `prometheus`: 48Mi
- `loki`: 64Mi
- `promtail`: about 25Mi to 37Mi per pod
- `node-exporter`: about 7Mi to 8Mi per pod
- `kube-state-metrics`: healthy after rollout; current memory not captured during the last `top` window because it was restarting during earlier snapshots

## Remaining Risks

- Prometheus still has noisy down targets from `kubernetes-kubelet` and `kubernetes-cadvisor`
- The lab currently depends on `node-exporter` and `kube-state-metrics` rather than direct kubelet scraping
- BankApp logs are visible, but only frontend logs were explicitly revalidated in this pass; backend and MySQL visibility should be spot-checked during the next smoke pass
- Observability is stable enough for the next phase, but Prometheus scrape noise should be cleaned up before using alerts as AI-remediation triggers

## Next Prerequisites For AI Remediation Phase

1. Decide whether to commit and sync the local Prometheus patch that disables kubelet and cAdvisor scrape jobs
2. Re-run Prometheus target validation after that decision
3. Spot-check backend and MySQL logs in Loki in addition to frontend logs
4. Define the initial alert and incident signals that should feed future AI analysis
5. Keep any future remediation flow human-approved only; no automatic cluster mutation without explicit approval
