# AI Remediation Service Skeleton

This service is the first safe Phoenix-Ops live AIOps foundation.

It now does four things:

- accepts normalized incident events
- collects read-only telemetry from Prometheus, Loki, Kubernetes, and Argo CD
- runs deterministic analyzers
- emits policy-gated recommendations
- persists recommendations for human review

It does not execute changes against Kubernetes, Argo CD, or Terraform.

## Structure

```text
services/ai-remediation/
  app/
    analyzers/
    api/
    cli.py
    collectors/
    config/
    models/
    pipeline/
    policies/
    recommendations/
    store/
    prompts/
    main.py
  config/
  data/
  scripts/
  tests/
```

## Current Endpoints

- `GET /healthz`
- `GET /v1/policies/current`
- `POST /v1/analyze`
- `GET /v1/recommendations`
- `GET /v1/recommendations/{id}`
- `POST /v1/recommendations/{id}/acknowledge`
- `POST /v1/recommendations/{id}/suppress`
- `POST /v1/poll-once`

## Run Locally

```bash
python3 services/ai-remediation/app/main.py
python3 services/ai-remediation/app/cli.py poll-once
```

Default bind:

- host: `127.0.0.1`
- port: `8081`

## Example Request

```json
{
  "event_id": "evt-001",
  "source": "prometheus",
  "scenario": "target_down",
  "cluster": "phoenix-oci-k3s",
  "namespace": "observability",
  "resource": {
    "kind": "ScrapeTarget",
    "name": "kubernetes-kubelet"
  },
  "observed_at": "2026-06-08T12:00:00Z",
  "severity_hint": "low",
  "summary": "Prometheus target is down",
  "evidence": [
    {
      "type": "metric",
      "name": "up",
      "value": 0,
      "labels": {
        "job": "kubernetes-kubelet",
        "lastError": "server returned HTTP status 403 Forbidden"
      }
    }
  ]
}
```

## Design Notes

- Policy is file-backed and explicit.
- Config is file-backed and explicit.
- Recommendations are structured and auditable.
- Persistence is local JSONL for now; no database is introduced in this phase.
- Collectors are read-only by design.
- LLM integration is optional and intentionally absent from the execution path.
