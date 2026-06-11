# Operator Command Cheatsheet

## Lab Lifecycle

```bash
scripts/oci-start-lab.sh
scripts/oci-k3s-tunnel.sh
scripts/oci-status-lab.sh
scripts/oci-stop-lab.sh
```

## Cluster Health

```bash
scripts/check-cluster-health.sh
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get ingress -A
```

## Argo CD And Observability

```bash
scripts/argocd-status.sh
kubectl get pods -n argocd -o wide
kubectl get pods -n bankapp -o wide
```

## AI Remediation Validation

```bash
python3 -m compileall services/ai-remediation/app services/ai-remediation/tests
python3 -m unittest discover -s services/ai-remediation/tests
services/ai-remediation/scripts/validate_notification_flow.sh
bash services/ai-remediation/scripts/validate_backend_restart_policy.sh
```

## Demo Safety

- Keep `ALERT_DRY_RUN=true` unless you are explicitly validating provider integration.
- Keep `AUTO_RESTART_BANKING_BACKEND=false` unless you are explicitly validating the bounded policy.
- Never use Terraform or arbitrary `kubectl` mutations for demos.
