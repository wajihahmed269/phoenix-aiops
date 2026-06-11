# K8sGPT Unavailable Demo

This demo shows that a missing K8sGPT binary does not stop the incident pipeline.

## What It Demonstrates

- K8sGPT is treated as an optional advisory source.
- The pipeline continues safely when the binary is missing.
- Incident artifacts still get written.

## Run

```bash
services/ai-remediation/scripts/demo_k8sgpt_unavailable.sh
```

## Expected Outcome

- The advisory is marked unavailable with a clear reason.
- The report still includes the incident, evidence, and operator next step.
- Notification remains dry-run by default.
