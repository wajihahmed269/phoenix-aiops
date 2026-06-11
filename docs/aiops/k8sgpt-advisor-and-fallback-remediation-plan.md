# Phoenix-Ops K8sGPT Advisor And Fallback Remediation Plan

## K8sGPT Integration Doctrine

## Progressive Escalation Design

## Safe Autonomous Recovery

## Incident Evidence Expansion

## Human-Absent Recovery Strategy

---

# 1. Introduction

Phoenix-Ops is transitioning from:

```text id="n6xnp6"
static monitoring + deterministic recommendations
```

toward:

```text id="mms4e8"
live operational intelligence with bounded recovery orchestration
```

The purpose of this phase is NOT to create:

* uncontrolled autonomous AI
* fully self-operating infrastructure
* unrestricted remediation execution
* “AI runs Kubernetes” systems

The purpose is to create:

```text id="9olwbj"
bounded operational survivability
```

during periods where:

* operators are unavailable
* incidents escalate rapidly
* infrastructure degradation continues
* telemetry evolves after initial detection

This document defines the architecture, philosophy, safety model, fallback execution plan, K8sGPT integration design, escalation workflow, and future autonomous recovery boundaries.

---

# 2. Why K8sGPT Exists In Phoenix-Ops

Phoenix-Ops already contains:

* Prometheus collectors
* Loki collectors
* Kubernetes collectors
* Argo collectors
* deterministic recommendation engine
* policy engine

However:

Raw telemetry is often difficult for humans to interpret quickly during incidents.

Example:

```text id="0w9s6o"
CrashLoopBackOff
readiness failing
container restarting
target_down
HTTP 503
deployment unhealthy
```

These signals indicate:

```text id="gcjlwm"
symptoms
```

but not always:

```text id="p6g8uh"
human-readable operational diagnosis
```

K8sGPT is introduced specifically to improve:

```text id="07y3h7"
diagnostic readability
```

NOT:

```text id="i1vqph"
decision authority
```

---

# 3. K8sGPT Architectural Role

K8sGPT is an:

```text id="k7i4l1"
optional bounded evidence enhancer
```

NOT:

* remediation authority
* execution engine
* autonomous controller
* policy authority
* orchestration engine

Phoenix-Ops itself remains:

```text id="vrw11l"
the operational authority
```

---

# 4. Core Design Principle

K8sGPT contributes:

```text id="5jxqko"
human-readable diagnosis
```

Phoenix-Ops contributes:

```text id="n3grl5"
policy-governed deterministic remediation orchestration
```

This separation is critical.

Without this separation:

```text id="z7a95s"
LLM hallucinations become infrastructure mutations
```

which is unacceptable.

---

# 5. Three-Stage Integration Strategy

Phoenix-Ops intentionally adopts K8sGPT progressively.

NOT:

```text id="f1jv1g"
full operator deployment immediately
```

---

# 6. Stage 1 — CLI Advisor Mode

## Philosophy

Stage 1 is designed to:

* minimize risk
* avoid cluster modifications
* avoid CRDs
* avoid operators
* avoid Helm complexity
* avoid Argo ordering issues

K8sGPT runs:

```text id="4sd86g"
outside the cluster
```

on the workstation only.

---

# 7. Stage 1 Operational Flow

```text id="fktd1q"
Incident detected
↓
Phoenix collectors gather telemetry
↓
K8sGPT CLI scan executes
↓
K8sGPT findings captured
↓
Findings attached as evidence
↓
Phoenix policy engine evaluates
↓
Recommendation generated
↓
Human-readable incident report created
```

No mutation occurs.

---

# 8. Why Local CLI First

Running locally avoids:

* Kubernetes RBAC expansion
* CRD lifecycle issues
* operator reconciliation bugs
* additional cluster resource pressure
* GitOps synchronization complexity
* Helm chart drift
* controller crash loops

This is the safest operational entry point.

---

# 9. Initial Collector Design

Planned collector:

```text id="56l3cl"
services/ai-remediation/app/collectors/k8sgpt.py
```

Responsibilities:

* bounded K8sGPT execution
* timeout enforcement
* output normalization
* evidence extraction
* graceful degradation

Responsibilities NOT included:

* remediation selection
* execution authority
* policy bypass
* autonomous action generation

---

# 10. Planned Execution Model

Phoenix-Ops should invoke K8sGPT using:

```bash
k8sgpt analyze \
  --kubeconfig ~/.kube/phoenix-k3s-oci.yaml \
  --namespace bankapp \
  --filter Pod \
  --output json
```

Important:

Phoenix-Ops MUST:

* always pass explicit kubeconfig
* never rely on default kubectl context
* enforce timeout limits
* bound namespace scope
* bound output size

---

# 11. Explicit Kubeconfig Doctrine

This is mandatory because Phoenix-Ops previously operated:

* EKS
* OCI K3s
* multiple kubeconfigs

The architecture MUST prevent:

```text id="9kl3aj"
cross-cluster accidental analysis
```

Required doctrine:

```text id="ffm60n"
ALL collectors MUST require explicit kubeconfig path
```

Never:

```text id="v4e4pc"
kubectl default context trust
```

---

# 12. OCI Tunnel Dependency

Phoenix-Ops Kubernetes API is private.

Therefore:

```text id="jsg76g"
K8sGPT depends on SSH tunnel availability
```

Tunnel architecture:

* localhost API forwarding
* private control-plane access
* non-public Kubernetes API

This improves security significantly.

---

# 13. Failure Philosophy

Phoenix-Ops assumes:

```text id="b5ql9x"
K8sGPT WILL fail sometimes
```

This is intentional architecture planning.

The system must remain operational even if:

* K8sGPT crashes
* CLI missing
* tunnel unavailable
* output invalid
* AI backend unavailable
* scan timeout occurs

K8sGPT is:

```text id="ddp9it"
best-effort diagnostic enrichment
```

NOT:

```text id="50m2rd"
critical dependency
```

---

# 14. Collector Failure Handling

Expected implementation behavior:

```python id="e29b9m"
try:
    run_k8sgpt()
except Exception:
    mark_evidence_unavailable()
    continue_pipeline()
```

Critical principle:

```text id="0wwlqs"
the incident pipeline must never stop because K8sGPT failed
```

---

# 15. Known Failure Scenarios

## Missing Binary

Possible error:

```text id="z4f5sp"
FileNotFoundError: k8sgpt not found
```

Expected behavior:

* collector disabled
* warning logged
* pipeline continues

---

## Wrong Kubeconfig

Possible issue:

* EKS context accidentally used
* unauthorized cluster access
* wrong resources scanned

Mitigation:

* explicit kubeconfig path required
* validation before execution
* cluster fingerprint verification later

---

## OCI Tunnel Failure

Possible error:

```text id="2mqc3y"
dial tcp 127.0.0.1:6443: connect: connection refused
```

Expected behavior:

* evidence unavailable
* no pipeline crash
* no recommendation corruption

---

## Timeout Scenario

Possible issue:

* large cluster scan
* stalled subprocess
* AI backend delay

Mitigation:

* hard timeout
* namespace scoping
* filter constraints

---

## Output Schema Drift

Possible issue:

* K8sGPT JSON changes
* parsing breaks

Mitigation:

* defensive parsing
* schema normalization
* raw evidence fallback

---

# 16. Human Governance Still Exists

K8sGPT does NOT bypass:

* policy engine
* recommendation engine
* safety contracts
* approval workflow

This is extremely important.

---

# 17. Plan B Philosophy

Phoenix-Ops assumes:

```text id="sq7r9x"
humans may be unavailable during outages
```

Examples:

* sleeping
* offline
* pager fatigue
* delayed response
* infrastructure incident escalation

Traditional monitoring systems stop here.

Phoenix-Ops does not.

---

# 18. Progressive Escalation Doctrine

Phoenix-Ops escalates gradually.

NOT:

```text id="vjlwmj"
instant autonomous remediation
```

---

# 19. Progressive Timeline

## T+0 Minutes

Actions:

* detect incident
* collect telemetry
* generate recommendation
* persist evidence
* send initial alert/email

No execution.

---

# 20. T+1 Minute Escalation

If no human response:

Actions:

* collect additional logs
* collect Kubernetes events
* collect rollout state
* run K8sGPT scan
* generate readable analysis
* send escalation email

Still:

```text id="fuyq9s"
no remediation execution
```

---

# 21. T+5 Minute Escalation

Actions:

* continue telemetry polling
* incident reevaluation
* recommendation reevaluation
* timeline persistence
* suppression analysis

Artifacts updated:

```text id="2x8h6s"
incident-artifacts/<incident-id>/
```

Potential contents:

* timeline.md
* metrics.json
* logs.txt
* k8sgpt-analysis.json
* recommendations.json

---

# 22. T+10–15 Minute Escalation

Autonomous remediation becomes possible ONLY if:

* no operator response
* policy allows
* rollback exists
* action class approved
* blast radius acceptable
* cooldown inactive
* namespace approved
* recommendation confidence high

This is:

```text id="mspkq2"
bounded fallback survivability
```

NOT:

```text id="hnh7h5"
full autonomous AI
```

---

# 23. Pre-Approved Remediation Catalog

Future fallback execution may allow:

```text id="od2gpn"
restart_deployment
restart_failed_pod
pause_rollout
resume_rollout
rollback_previous_revision
clear_known_stuck_job
cordon_node
```

Potentially later:

```text id="zh1bqk"
drain_node
```

But only with:

* rollback logic
* verification
* bounded scope
* audit storage

---

# 24. Forbidden Autonomous Actions

Never autonomous:

* terraform apply
* terraform destroy
* RBAC mutation
* NetworkPolicy deletion
* PVC deletion
* secret modification
* Git force push
* Argo application deletion
* cluster-wide scaling

These remain:

```text id="bmxl72"
human-only governance actions
```

---

# 25. Evidence Expansion Philosophy

Phoenix-Ops continuously expands evidence during escalation.

Reason:

```text id="0d5vcv"
incidents evolve over time
```

The system should never rely only on:

* initial logs
* initial metrics
* first observation

---

# 26. Timeline Persistence

Phoenix-Ops should maintain:

```text id="86d4h9"
incident timeline memory
```

This includes:

* telemetry changes
* recommendation changes
* escalation state
* remediation attempts
* verification status

This creates:

```text id="r3ozc7"
operational replayability
```

---

# 27. Why Markdown Artifacts Matter

Markdown incident artifacts provide:

* operator readability
* Git-friendly storage
* audit history
* timeline clarity

Example:

```text id="thn7om"
incident-artifacts/inc-001/timeline.md
```

This becomes:

```text id="c6rhhq"
operational forensic history
```

---

# 28. Shell Script Philosophy

Phoenix-Ops will eventually use shell orchestration carefully.

BUT:

```text id="pzy21y"
shell scripts must remain deterministic and bounded
```

Shell scripts should NEVER:

* invent actions
* run arbitrary commands
* mutate infrastructure blindly

---

# 29. Future Script Categories

Possible future scripts:

```text id="t2g0mz"
scripts/incident-capture.sh
scripts/verify-rollout-health.sh
scripts/restart-deployment-safe.sh
scripts/rollback-last-revision.sh
scripts/collect-bounded-logs.sh
scripts/capture-resource-snapshot.sh
```

---

# 30. Shell Script Safety Requirements

Every remediation script must define:

* input validation
* namespace restrictions
* timeout enforcement
* rollback support
* logging
* verification checks

Example:

```text id="rjlwm6"
restart-deployment-safe.sh
```

should:

* verify deployment exists
* verify namespace allowed
* capture pre-action state
* perform restart
* wait for rollout
* rollback if rollout fails

---

# 31. Blast Radius Philosophy

Phoenix-Ops classifies actions by blast radius.

## Low Risk

* restart pod
* restart deployment

## Medium Risk

* rollback deployment
* cordon node

## High Risk

* drain node
* cluster scaling

## Forbidden

* Terraform mutation
* RBAC changes
* secret deletion

---

# 32. Future Verification Layer

Future execution workflows must verify:

* pod recovery
* rollout success
* error reduction
* metric stabilization

Without verification:

```text id="olz8zb"
remediation is incomplete
```

---

# 33. Rollback Doctrine

Every autonomous remediation must support:

```text id="e5m2dc"
bounded rollback
```

Rollback capability is mandatory before autonomous execution approval.

---

# 34. Future Ollama Integration

Phoenix-Ops may later integrate:

```text id="7hh3c7"
local Ollama summarization
```

Purpose:

* readable reports
* incident summaries
* escalation explanations

NOT:

* unrestricted command generation
* infrastructure authority

---

# 35. Why Gateway API Is Delayed

Gateway API is powerful.

But adding it too early introduces:

* CRDs
* routing complexity
* controller dependencies
* debugging overhead

Gateway API should be introduced:

```text id="91zmkp"
after remediation architecture stabilizes
```

NOT before.

---

# 36. Why CRDs Are Delayed

Recommendation CRDs are attractive.

But early CRD introduction creates:

* controller burden
* reconciliation complexity
* Argo ordering issues
* API lifecycle burden

Phoenix-Ops intentionally delays CRDs until:

* lifecycle stable
* execution stable
* governance stable

---

# 37. Long-Term Vision

Phoenix-Ops eventually becomes:

```text id="c9ll3i"
governed operational intelligence platform
```

capable of:

* observing
* diagnosing
* escalating
* recommending
* recovering
* verifying
* rolling back

inside bounded operational constraints.

---

# 38. Final Architectural Doctrine

K8sGPT is:

```text id="8k06x4"
diagnostic augmentation
```

Phoenix-Ops is:

```text id="pjlwm9"
the operational authority
```

Humans remain:

```text id="7bgz17"
the governance boundary
```

Autonomous execution remains:

```text id="49sk2l"
bounded survivability fallback
```

NOT:

```text id="g6vjlwm"
unrestricted AI autonomy
```

That distinction is the core architectural philosophy of Phoenix-Ops.

