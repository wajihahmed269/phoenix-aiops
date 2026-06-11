# Current Platform Architecture

Phoenix-Ops is currently organized around an OCI-hosted K3s lab, Argo CD-managed application delivery, and a read-only AIOps/remediation control plane.

## Platform Layers

- `OCI` provides the lab compute and networking.
- `K3s` runs the in-cluster workloads.
- `Argo CD` delivers the BankApp manifests.
- `Prometheus`, `Grafana`, and `Loki` provide observability.
- `services/ai-remediation` provides advisory detection, evidence collection, reporting, and dry-run notification flows.

## Control Flow

1. Read-only collectors gather telemetry.
2. The AIOps pipeline correlates incidents and produces a recommendation.
3. K8sGPT may enrich the advisory evidence, but it never decides execution.
4. Incident artifacts are written locally for operator review.
5. Notifications are sent in dry-run mode by default.
6. The bounded banking-backend auto-restart policy remains disabled unless explicitly enabled by config and environment.

## Safety Boundaries

- No Terraform execution from this phase.
- No CRDs, operator installs, Gateway API changes, or public exposure.
- No destructive Kubernetes automation.
- No live auto-restart unless the narrow banking-backend policy is explicitly enabled.

## Operator Entry Points

- Start the lab with `scripts/oci-start-lab.sh`.
- Open the K3s tunnel with `scripts/oci-k3s-tunnel.sh`.
- Check cluster health with `scripts/check-cluster-health.sh`.
- Review remediation validations with the scripts under `services/ai-remediation/scripts/`.
