# AI Remediation Architecture

## Purpose

Phoenix-Ops needs safe AIOps primitives, not autonomous cluster mutation. The first version of AI remediation should ingest telemetry, analyze incidents, generate recommendations, require human approval for any future mutation, and keep the execution path separate from analysis.

## Current Platform Reality

- Observability is running on OCI K3s with Prometheus, Loki, Grafana, kube-state-metrics, node-exporter, and promtail.
- BankApp is healthy and internal-only.
- No Ollama workload is currently deployed in-cluster from this repo.
- BankApp still carries `OLLAMA_BASE_URL=http://ollama:11434`, but no matching Service exists today.
- GitOps is manual-first through Argo CD. Auto-sync is intentionally not part of this design.

## First-Version Scope

In scope:

- telemetry collection contracts
- incident normalization
- deterministic analyzers for known safe scenarios
- optional AI-assisted summarization behind a strict policy boundary
- recommendation objects with evidence, risk, confidence, and rollback hints
- human approval workflow design
- future execution interface definition without enabling execution

Out of scope:

- direct `kubectl` mutation from the analysis service
- Terraform execution
- autonomous restart, scale, patch, or delete actions
- public endpoints
- fake closed-loop remediation claims

## Component Model

```text
Prometheus / Loki / Kubernetes / Argo CD
                |
                v
        Telemetry Adapters
                |
                v
         Event Normalizer
                |
                v
       Analyzer Orchestrator
        |                 |
        |                 +--> Optional LLM Summarizer
        |                        (private, local, bounded)
        v
      Policy Engine
                |
                v
     Recommendation Generator
                |
                v
        Approval API / Queue
                |
                v
      Future Execution Layer
      (separate service, not implemented)
```

## Responsibilities

### Telemetry adapters

- Pull alert and target state from Prometheus
- Pull incident logs and label-scoped context from Loki
- Pull pod, deployment, event, and rollout state from Kubernetes
- Pull sync and health state from Argo CD Applications
- Return normalized evidence blocks instead of raw tool-specific blobs

### Event normalizer

- Convert alerts, cron checks, manual triggers, and webhook events into one incident envelope
- Attach cluster, namespace, resource, severity hint, timestamps, and evidence references
- Reject malformed or oversized events before analysis

### Analyzer orchestrator

- Route incidents to deterministic analyzers first
- Use scenario-specific analyzers for:
  - pod crashloop
  - repeated restart
  - deployment unhealthy
  - high memory usage
  - Prometheus target down
  - log anomaly summary
- Call LLM summarization only as a secondary step when local evidence is already bounded

### Policy engine

- Enforce allowed actions, forbidden actions, approval requirements, cooldowns, and rate limits
- Downgrade or suppress recommendations that exceed the allowed blast radius
- Mark all mutating actions as `requires_human_approval=true`

### Recommendation generator

- Emit structured recommendations with:
  - evidence
  - confidence
  - risk score
  - suggested action
  - rollback hint
  - policy decision
  - rationale

### Approval layer

- Present recommendations for operator review
- Record who approved or rejected a recommendation
- Preserve the original evidence and policy decision with the approval record

### Future execution layer

- Separate deployment and identity from analysis
- Re-validate policy at execution time
- Require an approval token or signed approval record
- Support only narrowly scoped, reversible actions in later phases

## Initial Event Pipeline

1. Telemetry source emits or exposes a signal.
2. Collector or manual trigger builds an incident envelope.
3. Event normalizer validates the envelope.
4. Analyzer orchestrator runs deterministic checks.
5. Optional LLM summarizer produces a bounded summary from selected evidence only.
6. Policy engine filters or constrains possible actions.
7. Recommendation generator emits one or more recommendations.
8. Recommendation is stored and exposed for human review.
9. No execution occurs in this phase.

## First Safe Scenarios

### Pod crashloop detection

- Evidence: pod status, restart count, recent events, last logs
- Safe output: inspect image/config errors, compare with last Git revision, propose manual restart only as a reviewed action

### High memory usage detection

- Evidence: `kubectl top`, pod limits/requests, recent logs, node pressure
- Safe output: classify likely leak vs normal spike, suggest manual investigation or scaling proposal, not direct scaling

### Deployment unhealthy detection

- Evidence: rollout status, unavailable replicas, events, Argo health state
- Safe output: recommend checking failed revision, image tag, probes, config drift

### Prometheus target down

- Evidence: job name, scrape URL, last error, recent config change
- Safe output: suppress known-limitation alerts such as kubelet `403` when policy says they are expected

### Log anomaly summarization

- Evidence: Loki query sample bounded by label and time window
- Safe output: summarize repeated errors, stack traces, or probe failures without proposing mutation by default

### Repeated restart detection

- Evidence: restart counts over time, events, rollout history
- Safe output: distinguish rollout-related restarts from unstable steady-state restarts

## Approval Flow

```text
incident -> recommendation -> operator review -> approved/rejected
```

Approval requirements:

- all mutating actions require explicit human approval
- approval must be attached to a specific recommendation ID
- approval expires after a bounded window
- execution must re-check policy and current cluster state before any future action

## Rollback Considerations

- Recommendations must include a rollback hint even when no execution occurs yet.
- Future execution actions must be reversible or have a bounded fallback.
- Non-reversible actions such as database mutation, namespace deletion, or Terraform changes remain forbidden.

## Security Boundaries

- Analysis service gets read-only telemetry access.
- Execution service, when added later, gets a separate identity and narrower action scope.
- Prompt input must exclude secrets, kubeconfigs, token data, and unrelated logs.
- No public ingress; keep all AI components internal or local-only.
- Model calls must remain private and local when Ollama is introduced.

## Blast-Radius Controls

- One recommendation is scoped to one incident and one primary resource.
- Cross-namespace recommendations require elevated severity review.
- Cooldowns prevent repeated identical recommendations from spamming operators.
- Rate limits prevent alert storms from creating unbounded AI work.

## Observability Integration

- Prometheus supplies alert state, resource pressure, and scrape health.
- Loki supplies labeled log context.
- Grafana remains the human visualization layer, not the approval plane.
- Argo CD state is evidence for GitOps drift and rollout health.

## Ollama Integration Direction

- Keep inference local/private and optional.
- Do not make the analysis pipeline depend on Ollama availability.
- Run inference on the `ollama` node only when intentionally deployed later.
- Constrain prompts to bounded evidence windows.
- Treat model output as advisory text, never as an execution command.
