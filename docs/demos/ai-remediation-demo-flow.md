# AI Remediation Demo Flow

Use this flow when you want to show the full advisory path without enabling live execution.

## Flow

1. Start the lab and open the K3s tunnel.
2. Validate cluster health.
3. Run the backend readiness failure demo.
4. Run the observability target issue demo.
5. Run the K8sGPT unavailable demo.
6. Review `incident-artifacts/<incident-id>/` for `summary.md`, `timeline.md`, `recommendation.json`, `evidence.json`, `k8sgpt.json`, and `notifications.log`.
7. Capture Grafana and Argo CD screenshots if you need evidence for the demo deck.

## Demo Rules

- Keep notifications in dry-run mode.
- Keep the bounded auto-restart policy disabled.
- Do not perform any live Kubernetes mutation.

## Success Criteria

- The incident report is readable without log spelunking.
- The recommended action is explicit and bounded.
- The operator can explain why no automation executed.
