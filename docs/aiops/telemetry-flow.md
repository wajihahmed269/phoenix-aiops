# Telemetry Flow

## Goal

Define a small, explicit telemetry path that supports incident analysis without forcing immediate execution.

## Telemetry Sources

### Prometheus

Used for:

- alert state
- target health
- resource utilization
- restart-related counters when exposed

Current operational note:

- kubelet and cAdvisor scrape noise may still exist as `403 Forbidden`; treat that as a policy-managed signal until the jobs are removed from the live config.

### Loki

Used for:

- namespace-scoped incident logs
- pod-specific error context
- repeated message detection

Current operational note:

- BankApp frontend logs are confirmed visible for `{namespace="bankapp"}`.
- Backend and MySQL logs should remain part of the next smoke validation loop.

### Kubernetes API

Used for:

- pod phase
- restart counts
- events
- rollout status
- deployment availability
- namespace and resource metadata

### Argo CD

Used for:

- Application sync state
- health state
- revision and drift context

## Incident Envelope

Every source should normalize into the same structure:

```json
{
  "event_id": "uuid-or-source-id",
  "source": "prometheus",
  "scenario": "target_down",
  "cluster": "phoenix-oci-k3s",
  "namespace": "observability",
  "resource": {
    "kind": "ServiceMonitorTarget",
    "name": "kubernetes-kubelet"
  },
  "observed_at": "2026-06-08T10:15:00Z",
  "severity_hint": "low",
  "summary": "Prometheus target is down",
  "evidence": [
    {
      "type": "metric",
      "name": "up",
      "value": 0,
      "labels": {
        "job": "kubernetes-kubelet"
      }
    }
  ]
}
```

## Collector Strategy

First phase should support three collector modes:

1. manual incident submission
2. scheduled polling of known checks
3. alert webhook ingestion later

Do not start with a large event bus.

## Evidence Collection Rules

- prefer labels and structured metadata over raw blobs
- cap log windows to a small time range
- cap log line counts per request
- include Argo revision when a deployment incident may be GitOps-related
- include node name when the issue may be node-local

## AI Summarization Flow

```text
normalized incident
  -> deterministic analyzer
  -> bounded evidence bundle
  -> optional LLM summary
  -> policy filter
  -> recommendation object
```

The model should only receive:

- a short scenario description
- selected evidence excerpts
- the allowed action classes
- the requirement that no autonomous execution is allowed

The model should not receive:

- secrets
- kubeconfigs
- full cluster dumps
- unrelated namespace logs
- approval tokens

## Ollama Integration Guidance

Current state:

- no Ollama workload is deployed from Phoenix-Ops today
- no in-cluster `ollama` Service is available

Safe next step later:

- deploy Ollama privately in a dedicated namespace or on the `ollama` node
- expose it only as a private `ClusterIP`
- run a small model with bounded concurrency
- keep timeouts short
- degrade gracefully when inference is unavailable

## Minimal Data Retention Guidance

- recommendation records: keep until reviewed and archived
- bounded evidence snippets: retain with the recommendation
- raw logs and metrics remain in Loki and Prometheus under their own retention controls

## Human Review Loop

The telemetry pipeline ends at a recommendation. The operator decides whether to:

- ignore
- acknowledge
- create a manual runbook task
- approve a future bounded action
