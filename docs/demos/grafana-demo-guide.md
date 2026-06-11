# Grafana Demo Guide

Use Grafana to prove the platform is healthy and to provide the evidence behind an incident demo.

## Port Forward Pattern

Use the existing cluster tunnel and a local port-forward for Grafana or Prometheus. Keep all access local only.

```bash
scripts/oci-k3s-tunnel.sh
kubectl -n observability port-forward svc/grafana 3000:80
kubectl -n observability port-forward svc/prometheus 9090:9090
kubectl -n observability port-forward svc/loki 3100:3100
```

## Panels To Show

- Cluster health dashboard.
- BankApp operations dashboard.
- Prometheus target status panels.
- Loki log panels for readiness and restart signals.

## Queries To Use

- Prometheus target health: `up{namespace="bankapp"}`
- BankApp workload readiness: `kube_deployment_status_replicas_available{namespace="bankapp"}`
- Loki readiness failures: `{namespace="bankapp"} |= "readiness probe failed"`
- Loki restart signals: `{namespace="bankapp"} |= "Back-off restarting failed container"`

## Screenshots To Capture Later

- A healthy cluster overview before the demo.
- A bankapp workload panel during the incident.
- A Loki log panel that shows the failure evidence.
- A final panel showing the workload recovered or still bounded by policy.
