# Human-Approved Execution Design

## Purpose

Define the next phase after the live read-only pipeline without implementing it yet.

## Required Future Flow

```text
Telemetry
  -> Recommendation
  -> Human Approval
  -> Policy Check
  -> Controlled Execution
  -> Verification
  -> Audit Record
```

## Separation Of Duties

### Analysis service

- read-only
- recommendation-first
- no cluster mutation
- no execution endpoints

### Future execution service

- separate identity
- narrower permissions than cluster-admin
- validates:
  - approval record
  - policy
  - target resource identity
  - action bounds
- records verification after execution

## Candidate First Actions Later

- collect logs
- collect events
- open runbook
- propose rollout restart
- trigger approved Argo sync
- annotate recommendation status

These actions still require human approval before execution.

## Still Forbidden

- Terraform apply/destroy
- delete namespace
- drain node
- direct database writes
- RBAC widening
- public exposure changes
- chained autonomous execution

## Verification Requirements

Every future execution must include:

- pre-check snapshot
- action intent record
- bounded timeout
- post-action validation
- final audit entry
