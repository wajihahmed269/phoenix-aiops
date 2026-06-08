# Phoenix-Ops K8sGPT CLI Advisor Implementation

## Purpose

This phase integrates K8sGPT as a workstation-local, read-only advisor inside the existing Phoenix-Ops AI remediation pipeline.

K8sGPT is implemented as:

- optional evidence enrichment
- bounded subprocess execution
- explicit-kubeconfig analysis
- namespace-scoped diagnostics
- non-blocking advisory augmentation

K8sGPT is not implemented as:

- remediation authority
- execution engine
- operator or controller
- CRD-backed workflow
- in-cluster deployment

## Why CLI-Only In This Phase

CLI-only mode preserves the current safety boundary:

- no RBAC expansion
- no Helm chart lifecycle
- no Argo CD application ordering
- no cluster resource footprint
- no controller drift or reconciliation risk

This keeps the first K8sGPT integration aligned with the doctrine in:

- `docs/aiops/remediation-orchestration-architecture.md`
- `docs/aiops/k8sgpt-advisor-and-fallback-remediation-plan.md`

## Architecture

The runtime flow is:

```text
Existing collectors
  -> incident correlation
  -> optional K8sGPT namespace scan
  -> K8sGPT finding matching per incident
  -> deterministic recommendation engine
  -> incident artifact persistence
  -> timeline update
```

Files added in this phase:

- `services/ai-remediation/app/collectors/k8sgpt.py`
- `services/ai-remediation/app/models/identity.py`
- `services/ai-remediation/app/pipeline/correlation.py`
- `services/ai-remediation/app/pipeline/summary.py`
- `services/ai-remediation/app/store/incident_artifacts.py`
- `services/ai-remediation/scripts/validate_k8sgpt_advisor.sh`
- `services/ai-remediation/tests/test_k8sgpt_collector.py`

Key updates:

- `services/ai-remediation/config/default.json`
- `services/ai-remediation/app/config/loader.py`
- `services/ai-remediation/app/pipeline/poller.py`
- `services/ai-remediation/app/store/lifecycle.py`
- `services/ai-remediation/app/models/recommendation.py`
- `services/ai-remediation/app/analyzers/rules.py`

## Safety Model

The collector enforces:

- explicit `--kubeconfig ~/.kube/phoenix-k3s-oci.yaml`
- namespace allowlist checks
- bounded filter list
- hard subprocess timeout
- maximum output size limit
- defensive JSON parsing
- best-effort failure handling

Failure modes handled without stopping the pipeline:

- missing `k8sgpt` binary
- timeout
- invalid JSON output
- tunnel or kubeconfig connectivity failures
- non-zero command exit
- oversize output

When this happens, Phoenix-Ops appends `advisory_unavailable` evidence and continues deterministic recommendation generation.

## Incident Artifact Structure

Artifacts are stored under:

```text
incident-artifacts/<incident-id>/
```

Current files:

- `timeline.md`
- `metrics.json`
- `logs.txt`
- `k8sgpt-analysis.json`
- `recommendations.json`
- `incident-summary.md`

This creates operational replayability and keeps escalation context local and auditable.

## Correlation And Suppression

Incidents are first correlated by resource identity to avoid duplicate recommendations caused by multiple collectors reporting the same failing workload.

K8sGPT findings are then treated as:

- supplemental evidence
- not separate incidents

Suppression currently filters advisory findings that match known noisy patterns such as:

- completed Helm jobs
- expected Argo drift phrasing
- known 403-style scrape noise

Severity is normalized to a bounded set:

- `critical`
- `high`
- `medium`
- `low`
- `info`

## Timeline Persistence

The timeline currently records:

- detection
- evidence persistence
- recommendation persistence
- dedupe suppression
- manual acknowledge/suppress state changes

This forms the foundation for future bounded fallback execution, verification, and rollback tracking.

## Human-Readable Summary Model

The summary generator is intentionally bounded. It only uses:

- incident type
- resource identity
- limited evidence snippets
- at most one matched K8sGPT diagnosis
- deterministic recommendation rationale

It does not dump raw logs, large telemetry bodies, or unbounded LLM output.

## Validation

Use:

```bash
services/ai-remediation/scripts/validate_k8sgpt_advisor.sh
```

The validator checks:

- `python3` presence
- `kubectl` presence
- kubeconfig readability
- tunnel reachability via `kubectl cluster-info`
- bounded K8sGPT collector execution
- graceful fallback when the binary is intentionally replaced with a missing path

## Risks And Scaling Concerns

- Namespace-wide scans per polling cycle can become expensive if the allowlist grows significantly.
- K8sGPT JSON schema drift is still possible; the parser is defensive but not schema-version aware.
- Correlation is resource-centric today and may need stronger rollout ownership mapping later.
- Artifact volume can grow over time and will need retention controls before continuous polling is enabled at higher frequency.

## Why Operator Mode Is Delayed

Operator mode is intentionally deferred until:

- recommendation lifecycle is stable
- artifact and timeline model is mature
- bounded fallback execution contracts exist
- approval and rollback governance is implemented

Introducing CRDs or an in-cluster controller earlier would widen the safety surface before the governance model is complete.

## Future Roadmap

Later phases can add:

- cluster fingerprint validation
- stronger workload ownership correlation
- artifact retention policies
- richer escalation stages
- pre-approved remediation catalog integration
- verification and rollback artifact capture
- optional operator mode after governance stabilizes
