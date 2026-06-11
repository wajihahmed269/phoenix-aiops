# Backend Readiness Failure Demo

This demo shows the advisory flow for a `banking-backend` readiness failure without enabling live remediation.

## What It Demonstrates

- Incident detection for `bankapp/banking-backend`.
- Evidence capture and incident report generation.
- Dry-run Brevo notification payload generation.
- The bounded restart policy is recognized, but not executed.

## Run

```bash
services/ai-remediation/scripts/demo_backend_readiness_failure.sh
```

## Expected Artifacts

- `summary.md`
- `timeline.md`
- `evidence.json`
- `k8sgpt.json`
- `recommendation.json`
- `notifications.log`

## Operator Talking Points

- The incident is reported clearly.
- The recommended action is limited to `deployment/banking-backend`.
- The restart policy stays disabled by default.
- The operator decides whether to continue, acknowledge, or suppress.
