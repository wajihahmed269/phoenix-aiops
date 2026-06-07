# Observability Rollout Report

## Scope

- Deployed through `argocd/observability` on OCI K3s using `~/.kube/phoenix-k3s-oci.yaml`
- No public ingress or LoadBalancer exposure added for observability
- Grafana admin secret created manually in `observability`

## What Was Deployed

- Namespace: `observability`
- Deployments: `prometheus`, `loki`, `grafana`, `kube-state-metrics`
- DaemonSets: `promtail`, `node-exporter`
- Services: all `ClusterIP`
- PVCs: `prometheus-data` 5Gi, `loki-data` 5Gi
- Argo CD Application: `argocd/observability`

## What Works

- `argocd/observability` exists and sync completed successfully
- Prometheus pod is `Running`; `/-/healthy` and `/-/ready` return OK
- Loki pod is `Running`; `/ready` returns OK
- Grafana pod is `Running`; `/login` returns 200 and `/api/health` reports `database: ok`
- Grafana datasources are provisioned: `Prometheus`, `Loki`
- Grafana dashboards are loaded: `BankApp Operations`, `Phoenix Cluster Health`
- Node exporter is running on all five nodes
- Promtail is running on all five nodes
- Prometheus PVC and Loki PVC are both `Bound`

## What Failed

- Loki ingestion is not working yet
- `Loki /loki/api/v1/labels` returns no labels
- Query `{namespace="bankapp"}` returns zero results
- Promtail is discovering `0/0` targets and sending `0` bytes / `0` entries
- `positions.yaml` remains empty: `positions: {}`
- Prometheus kubelet and cAdvisor targets return `403 Forbidden`
- `kube-state-metrics` is in `CrashLoopBackOff`; its probes hit `/readyz` and `/livez` and receive `404`

## Root Cause Found

- Promtail is using the pod hostname for Kubernetes pod service discovery
- In this DaemonSet, the default hostname is the pod name, not the node name
- That causes Kubernetes discovery to field-select on `spec.nodeName=<promtail-pod-name>`, which matches nothing
- Result: Promtail discovers zero pod targets, tails zero files, and pushes zero log lines to Loki

## Local Fix Prepared But Not Applied To Cluster

- File: `gitops/apps/observability/promtail-daemonset.yaml`
- Minimal change: set `HOSTNAME` from `spec.nodeName`
- This is a local uncommitted Git change only; it has not been synced to Argo CD or live-patched into the cluster

## Prometheus 403 Assessment

- Current Prometheus RBAC is sufficient for Kubernetes API reads
- The `403 Forbidden` errors are from direct kubelet access on `https://<node-ip>:10250/metrics` and `/metrics/cadvisor`
- Safest near-term approach for this lab: disable kubelet and cAdvisor scrape jobs and rely on `node-exporter` plus `kube-state-metrics`
- Safer than weakening kubelet authz or enabling broader node-level access

## Resource Usage Before And After

### Before rollout

- `controlplane`: 67m CPU, 2248Mi memory, 37%
- `app`: 15m CPU, 1542Mi memory, 26%
- `observatory`: 13m CPU, 1336Mi memory, 22%
- `aiops`: 12m CPU, 1137Mi memory, 19%
- `ollama`: 24m CPU, 1676Mi memory, 28%

### After rollout snapshot

- `controlplane`: 64m CPU, 2380Mi memory, 40%
- `app`: 21m CPU, 1599Mi memory, 27%
- `observatory`: 28m CPU, 1455Mi memory, 24%
- `aiops`: 33m CPU, 1269Mi memory, 21%
- `ollama`: 38m CPU, 1713Mi memory, 28%

### Observability pod memory snapshot

- `grafana`: 67Mi
- `prometheus`: 43Mi
- `loki`: 35Mi
- `promtail`: about 19Mi per pod
- `node-exporter`: about 7Mi per pod

## Remaining Risks

- Loki has no useful value until Promtail discovery is fixed and log ingestion is proven
- `kube-state-metrics` instability reduces dashboard completeness and cluster metrics reliability
- Kubelet/cAdvisor direct scraping is not usable as currently configured
- Argo CD is currently tracking remote GitHub `HEAD`, so local fixes cannot reach the cluster until committed and pushed, or manually live-patched with accepted drift

## Next Steps Toward AI Remediation

1. Commit and push the Promtail node-name fix, then run a one-shot Argo sync for `observability`
2. Revalidate Loki labels and confirm `bankapp` log visibility
3. Fix `kube-state-metrics` health probes with the smallest verified probe path change
4. Disable kubelet/cAdvisor scrape jobs for this lab unless a safer kubelet-auth path is explicitly chosen
5. Once logs and metrics are stable, use Loki plus Prometheus as the telemetry base for a human-approved AI remediation flow
