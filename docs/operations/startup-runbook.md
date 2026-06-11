# Startup Runbook

Use the OCI lab scripts only. Do not use Terraform for startup in this phase.

## Start The Lab

```bash
scripts/oci-start-lab.sh
```

## Open The Cluster Tunnel

```bash
scripts/oci-k3s-tunnel.sh
```

## Confirm Readiness

```bash
scripts/check-cluster-health.sh
scripts/oci-status-lab.sh
```

## Post-Start Checks

- Verify the active Kubernetes context is the OCI tunnel context.
- Confirm `bankapp`, `argocd`, and system pods are running.
- Confirm the observability stack is reachable through port-forwarded access only.
- Run the AI-remediation validators before any demo.
