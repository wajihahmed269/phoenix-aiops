# Observability Target Issue Demo

This demo keeps the incident in the observability lane and proves the advisory path stays read-only.

## What It Demonstrates

- Prometheus target evidence appears in the report.
- The incident is summarized clearly for the operator.
- No mutation path is generated.

## Run

```bash
services/ai-remediation/scripts/demo_observability_target_issue.sh
```

## Expected Outcome

- A dry-run notification payload is produced.
- The report shows evidence, recommendation, and next step.
- The operator can confirm the issue without touching the workload plane.
