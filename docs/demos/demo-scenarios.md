# Demo Scenarios

All demo scenarios are deterministic and safe-by-default. They do not enable live remediation.

## Scenario A: Backend Readiness Failure

- Purpose: show the AI-remediation pipeline detecting an unhealthy `banking-backend` deployment.
- Expected output: incident artifact files, dry-run notification, bounded restart policy preparation, and a report that explains the next operator step.
- Script: `services/ai-remediation/scripts/demo_backend_readiness_failure.sh`

## Scenario B: Observability Target Issue

- Purpose: show Prometheus/Loki evidence flowing into the advisory path without mutation.
- Expected output: read-only evidence capture, recommendation generation, and a report that stays advisory.

## Scenario C: K8sGPT Unavailable

- Purpose: show that a missing K8sGPT binary does not break the pipeline.
- Expected output: advisory continues safely, marks K8sGPT unavailable, and still writes incident artifacts.
- Script: `services/ai-remediation/scripts/demo_k8sgpt_unavailable.sh`

## Common Demo Rules

- Use dry-run notification mode.
- Do not enable live auto-restart.
- Do not apply manifests, delete pods, or mutate the cluster.
