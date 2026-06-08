# Phoenix-Ops Remediation Orchestration Architecture

## Operational Intelligence Doctrine

## Safety Governance

## Incident Lifecycle

## Recommendation Orchestration

## Human-Approved Autonomous Infrastructure Recovery

---

# 1. Introduction

Phoenix-Ops is not designed to become another dashboard-heavy Kubernetes demo platform.

The goal is not to create:

* another Grafana showcase
* another “AI DevOps chatbot”
* another auto-scaling tutorial
* another toy remediation loop

The goal is to design and implement a production-style operational intelligence system capable of:

```text
detecting
analyzing
classifying
prioritizing
documenting
recommending
and eventually remediating
real infrastructure incidents
```

inside a bounded and governed operational environment.

This document defines the architectural doctrine for that system.

---

# 2. Foundational Philosophy

The core philosophy of Phoenix-Ops is:

```text
bounded operational intelligence
```

NOT:

```text
unbounded autonomous AI execution
```

Phoenix-Ops intentionally separates:

```text
observation
analysis
recommendation
approval
execution
verification
rollback
```

into independent architectural layers.

This separation exists because most “AI Ops” systems fail in one of two ways:

## Failure Pattern A — Monitoring-only systems

These systems:

* collect metrics
* generate alerts
* display dashboards

But:

* provide no deterministic remediation strategy
* provide no operational reasoning
* provide no recommendation governance
* provide no incident orchestration

Result:
human operators still manually investigate everything.

---

## Failure Pattern B — Reckless autonomous systems

These systems:

* allow direct AI execution
* trust LLM reasoning blindly
* mutate infrastructure automatically
* ignore blast radius
* skip governance
* skip rollback architecture

Result:

* cascading failures
* destructive automation
* outage amplification
* irrecoverable configuration drift

Phoenix-Ops is designed specifically to avoid BOTH categories of failure.

---

# 3. Core Architectural Principle

Phoenix-Ops operates using:

```text
human-governed deterministic remediation orchestration
```

This means:

## AI can:

* summarize
* classify
* correlate
* explain
* recommend
* enrich diagnostics

But AI CANNOT:

* invent infrastructure mutations
* generate arbitrary kubectl actions
* modify Terraform
* change RBAC
* expose services publicly
* scale infrastructure blindly
* bypass policy engine

---

# 4. System Architecture

## High-Level Operational Flow

```text
Cluster Telemetry
    ↓
Collectors
    ↓
Normalization Pipeline
    ↓
Incident Engine
    ↓
Policy Engine
    ↓
Recommendation Engine
    ↓
Persistence Layer
    ↓
Human Review Workflow
    ↓
Optional Approved Execution
    ↓
Verification Engine
    ↓
Rollback Layer
```

---

# 5. Current Platform State

Current Phoenix-Ops stack includes:

## Infrastructure

* Oracle Cloud Infrastructure (OCI)
* Private VCN networking
* Multi-node K3s cluster
* SSH tunnel-based Kubernetes API access
* GitOps deployment model
* Argo CD orchestration

---

## Core Services

### BankApp

* frontend
* backend
* MySQL

### Observability

* Prometheus
* Grafana
* Loki
* Promtail
* kube-state-metrics
* node-exporter

### GitOps

* Argo CD
* declarative Kubernetes manifests

---

# 6. Existing Telemetry Sources

Phoenix-Ops currently integrates:

## Metrics

Source:

```text
Prometheus
```

Used for:

* CPU
* memory
* restart spikes
* target failures
* resource pressure
* unhealthy workloads

---

## Logs

Source:

```text
Loki
```

Used for:

* error pattern extraction
* repeated stack traces
* incident evidence
* anomaly correlation

---

## Kubernetes API

Used for:

* pod state
* deployment health
* replica status
* restart counts
* events
* rollout state

---

## Argo CD

Used for:

* application sync state
* degraded applications
* rollout health
* GitOps drift visibility

---

# 7. Incident Lifecycle Philosophy

Phoenix-Ops treats incidents as structured operational objects.

NOT:

```text
temporary alerts
```

Every incident should become:

```text
observable
traceable
reviewable
auditable
recoverable
```

---

# 8. Incident Lifecycle

## Stage 1 — Detection

Telemetry collectors detect anomalies.

Examples:

* CrashLoopBackOff
* readiness failure
* target_down
* restart spike
* memory pressure
* rollout unhealthy
* repeated error logs

---

## Stage 2 — Normalization

Raw telemetry becomes:

```json
{
  "incident_type": "deployment_unhealthy",
  "namespace": "bankapp",
  "resource": "banking-backend",
  "severity": "high",
  "timestamp": "2026-06-09T01:00:00Z"
}
```

Normalization prevents:

* collector-specific chaos
* inconsistent evidence formats
* duplicate recommendation generation

---

## Stage 3 — Correlation

The engine attempts to correlate:

* logs
* metrics
* Kubernetes state
* rollout state
* known suppressions

This prevents:

```text
10 alerts for 1 actual outage
```

---

## Stage 4 — Recommendation Generation

Phoenix-Ops generates deterministic recommendations.

Important:

Recommendations are NEVER:

* hallucinated
* AI-generated freeform infrastructure actions

Recommendations MUST originate from:

```text
approved remediation catalog
```

---

# 9. Approved Remediation Catalog

Allowed future actions may include:

```text
restart_deployment
restart_failed_pod
pause_rollout
resume_rollout
rollback_previous_revision
cordon_node
drain_node
clear_known_stuck_job
```

Each action class must define:

* blast radius
* rollback strategy
* verification method
* cooldown window
* namespace policy
* execution safety

---

# 10. Forbidden Autonomous Actions

Phoenix-Ops explicitly forbids autonomous execution of:

```text
terraform apply
terraform destroy
RBAC modification
network policy deletion
secret mutation
public ingress exposure
database deletion
persistent volume deletion
cluster-wide scaling
Git force push
Argo application deletion
```

These actions require:

```text
human governance
```

ALWAYS.

---

# 11. Recommendation Philosophy

Recommendations are:

```text
structured operational proposals
```

NOT:

```text
chatbot suggestions
```

Each recommendation must contain:

```json
{
  "id": "rec-001",
  "incident_id": "inc-001",
  "resource": "banking-backend",
  "severity": "high",
  "recommended_action": "restart_deployment",
  "reason": "CrashLoopBackOff with repeated readiness failure",
  "confidence": "high",
  "safe_action": true
}
```

---

# 12. Recommendation States

A recommendation lifecycle includes:

```text
proposed
acknowledged
suppressed
approved
rejected
executed
verified
rolled_back
expired
```

Each transition must be auditable.

---

# 13. Persistence Model

Phoenix-Ops stores:

* incidents
* evidence
* timelines
* recommendations
* approvals
* execution history

Initially:

```text
JSONL local persistence
```

Future:

```text
PostgreSQL
```

Possible future:

```text
Recommendation CRDs
```

But NOT yet.

---

# 14. Why CRDs Are Delayed

Custom Resource Definitions are powerful.

But introducing them too early causes:

* API surface expansion
* controller complexity
* RBAC growth
* reconciliation debugging
* GitOps sync ordering problems

So the architecture intentionally delays CRDs until:

* recommendation model stabilizes
* lifecycle stabilizes
* execution workflow stabilizes

---

# 15. Human Governance Model

Phoenix-Ops uses:

```text
human-approved remediation
```

because:

* infrastructure failures can cascade
* metrics can lie
* logs can mislead
* temporary network failures exist
* Kubernetes eventually-consistent behavior exists

Blind automation creates:

```text
outage amplification
```

instead of:

```text
self-healing
```

---

# 16. Future Autonomous Recovery Doctrine

Autonomous recovery is allowed ONLY when:

## Conditions

* action is pre-approved
* blast radius small
* rollback exists
* cooldown inactive
* policy permits
* namespace allowed
* evidence confidence high
* verification possible

AND:

```text
human did not respond
within escalation window
```

---

# 17. Escalation Philosophy

Phoenix-Ops uses progressive escalation.

NOT:

```text
instant automation
```

---

# 18. Progressive Escalation Model

## T+0

Incident detected.

Actions:

* store incident
* collect telemetry
* generate recommendation
* send alert/email

---

## T+1 minute

If no response:

* collect more evidence
* bounded logs
* Kubernetes events
* rollout diagnostics
* optional K8sGPT scan
* generate readable incident report

---

## T+5 minutes

Continue:

* telemetry polling
* incident timeline updates
* recommendation reevaluation
* suppression analysis

---

## T+10–15 minutes

Only if:

* policy allows
* action safe
* rollback exists
* cooldown inactive
* namespace approved
* blast radius acceptable

Then:

```text
execute safest bounded remediation
```

---

# 19. Why This Architecture Matters

Most AI remediation demos skip:

* governance
* rollback
* auditability
* bounded execution
* safety contracts
* escalation logic

Phoenix-Ops intentionally prioritizes:

```text
operational survivability
```

over:

```text
flashy automation demos
```

---

# 20. Observability Philosophy

Phoenix-Ops observability exists to support:

```text
operational reasoning
```

NOT:

```text
dashboard screenshots
```

Every telemetry source should contribute toward:

* incident detection
* correlation
* recommendation quality
* verification
* rollback confidence

---

# 21. Loki Role

Loki is used for:

* bounded log retrieval
* repeated error extraction
* anomaly detection
* evidence enrichment

Loki is NOT:

* full forensic SIEM
* unlimited log archive
* unrestricted AI input source

Reason:

* cost
* security
* token explosion
* sensitive data risk

---

# 22. Prometheus Role

Prometheus is used for:

* deterministic thresholds
* resource pressure
* restart spikes
* unhealthy targets
* deployment instability

Prometheus metrics remain:

```text
high-confidence operational evidence
```

compared to freeform AI interpretation.

---

# 23. Kubernetes Collector Doctrine

The Kubernetes collector is authoritative for:

* rollout state
* pod lifecycle
* restart counts
* events
* readiness
* liveness
* deployment availability

It is NOT authoritative for:

* root cause certainty
* remediation choice

---

# 24. Argo CD Role

Argo is operational truth for:

* desired state
* sync status
* deployment reconciliation
* GitOps drift

Future execution workflows MUST respect:

```text
GitOps ownership
```

Phoenix-Ops should never become:

```text
kubectl imperative chaos
```

---

# 25. GitOps Doctrine

Declarative state remains authoritative.

Future remediation execution must:

* avoid drift
* preserve reconciliation integrity
* remain GitOps-compatible

This is critical.

Without this:

```text
AI remediation becomes infrastructure drift generator
```

---

# 26. Safety Layers

Phoenix-Ops safety model contains multiple independent layers.

## Layer 1 — Collector Bounds

* timeout limits
* namespace scoping
* bounded queries

## Layer 2 — Policy Engine

* action allowlists
* namespace restrictions
* severity normalization

## Layer 3 — Recommendation Engine

* deterministic generation
* no hallucinated actions

## Layer 4 — Approval Workflow

* human review
* escalation windows

## Layer 5 — Execution Constraints

* rollback requirement
* cooldowns
* blast radius checks

## Layer 6 — Verification

* recovery validation
* rollback trigger

---

# 27. Operational Artifact Storage

Phoenix-Ops should eventually maintain:

```text
incident-artifacts/
```

Containing:

```text
incident timeline
metrics snapshot
bounded logs
recommendations
execution history
rollback evidence
verification reports
```

This creates:

```text
operational memory
```

instead of ephemeral alerts.

---

# 28. Conclusion

Phoenix-Ops is evolving from:

```text
monitoring stack
```

into:

```text
governed operational intelligence platform
```

The architecture intentionally prioritizes:

* bounded automation
* deterministic recommendations
* GitOps integrity
* operational auditability
* survivability
* safe recovery
* escalation discipline

over:

* hype
* unsafe autonomy
* uncontrolled AI execution

This document defines the foundational doctrine that all future remediation systems inside Phoenix-Ops must follow.
