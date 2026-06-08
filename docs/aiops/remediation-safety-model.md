# Remediation Safety Model

## Principle

Phoenix-Ops remediation is recommendation-first. Analysis can suggest; execution, if added later, must validate policy again and require human approval for any mutation.

## Severity Levels

| Level | Meaning | Typical examples | Default approval |
| --- | --- | --- | --- |
| `info` | Context only | scrape noise, transient restart, low-signal log anomaly | no mutation allowed |
| `low` | Small operational issue | one target down, mild pod restart growth | mutation requires approval |
| `medium` | Service degradation risk | deployment unhealthy, sustained memory pressure | mutation requires approval |
| `high` | Active service impact | crashloop, repeated rollout failure | mutation requires approval plus second validation |
| `critical` | Broad impact or data risk | multi-service outage, storage failure | mutation requires approval, incident owner review, and rollback plan |

## Allowed Action Classes

First safe phase:

- `collect_evidence`
- `query_logs`
- `query_metrics`
- `summarize_incident`
- `open_runbook`
- `propose_rollout_restart`
- `propose_scale_change`
- `propose_config_review`

These are recommendation classes, not live actions.

## Forbidden Actions

Always forbidden in the analysis service:

- `delete_namespace`
- `delete_pod`
- `drain_node`
- `cordon_node`
- `terraform_apply`
- `terraform_destroy`
- `database_write`
- `secret_read_plaintext`
- `rbac_widen`
- `networkpolicy_weaken`
- `public_exposure_change`
- `auto_sync_enable`

## Approval Requirements

- Any future cluster mutation requires explicit human approval.
- Approval must be tied to:
  - recommendation ID
  - action type
  - target resource
  - expiry time
- Approval cannot be reused for a different resource or repeated automatically.

## Cooldowns

- identical recommendation for the same resource: 15 minutes
- identical medium or high severity recommendation across the same namespace: 30 minutes
- suppressed known limitations: 6 hours

## Rate Limits

- max 20 analyzed incidents per 10 minutes per cluster
- max 5 recommendations per 10 minutes for the same resource
- max 1 pending mutating recommendation per resource

## Audit Logging Requirements

Every recommendation record must include:

- recommendation ID
- source event ID
- cluster
- namespace
- resource kind and name
- evidence references
- analyzer version
- policy version
- suggested action
- risk score
- confidence
- approval requirement
- operator decision, if any

## Evidence Handling

- keep raw evidence references, not unlimited raw payloads
- truncate large log excerpts
- strip secrets and tokens before model use
- preserve exact timestamps for metrics and logs

## Known-Limitation Handling

The policy layer must support explicit suppressions for issues that are understood and accepted operationally. Current example:

- Prometheus kubelet/cAdvisor `403 Forbidden` scrape failures can be tagged as a known limitation until the scrape jobs are removed or redesigned.

## Future Execution Guardrails

When an execution layer is added later, it must:

- use a separate service account from the analysis service
- validate approval expiry and policy at execution time
- check the live resource still matches the recommendation target
- record command intent before execution
- capture post-action verification
- stop after one bounded action, never chain actions automatically
