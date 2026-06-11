#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export PYTHONPATH="${ROOT_DIR}/services/ai-remediation"
export ALERT_DRY_RUN="${ALERT_DRY_RUN:-true}"

echo "Phoenix-Ops observability target issue demo"
echo "ALERT_DRY_RUN=${ALERT_DRY_RUN}"

python3 - <<'PY'
import json
import tempfile
from pathlib import Path

from app.escalation.workflow import build_escalation_state
from app.models.factory import create_incident_event
from app.models.recommendation import ActionProposal, Recommendation
from app.notifications.formatters import build_email_payload, build_markdown_summary
from app.notifications.service import send_incident_notification
from app.store.incident_artifacts import IncidentArtifactStore

with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)
    env_file = tmp / ".env.aiops"
    env_file.write_text(
        "\n".join(
            [
                "BREVO_API_KEY=test-secret",
                "ALERT_FROM_EMAIL=phoenix@example.com",
                "ALERT_TO_EMAIL=ops@example.com",
                "ALERT_PROVIDER=brevo",
                "ALERT_DRY_RUN=true",
                "AUTO_RESTART_BANKING_BACKEND=false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    config = {
        "incident_artifacts_path": str(tmp / "incident-artifacts"),
        "incident_artifacts": {"max_json_bytes": 262144, "max_text_bytes": 65536, "max_timeline_entries": 2000, "timeline_summary_entries": 5, "max_notification_log_bytes": 65536},
        "alerting": {"env_file": str(env_file), "provider_timeout_seconds": 5, "provider_max_retries": 2, "max_notification_log_bytes": 65536},
        "auto_remediation": {"enabled": False, "allowed_actions": ["restart_banking_backend"], "allowed_namespace": "bankapp", "allowed_deployment": "banking-backend", "timeout_minutes": 10, "require_snapshot": True, "verify_rollout": True},
        "remediation": {"simulation_only": True, "namespace_allowlist": ["bankapp"], "resource_kind_allowlist": ["Deployment"], "protected_namespaces": ["argocd", "observability"], "max_blast_radius": "medium", "execution_timeout_seconds": 30, "approval_ttl_minutes": 30, "rollback_retention_days": 7, "maintenance_windows_enabled": False, "escalation_minutes": {"t1": 1, "t5": 5, "t10": 10, "t15": 15}, "command_allowlist": ["get", "describe", "logs", "rollout restart", "rollout status"]},
    }

    recommendation = Recommendation(
        recommendation_id="rec-demo-observability-1",
        incident_id="inc-demo-observability-1",
        event_id="evt-demo-observability-1",
        source="prometheus",
        cluster="phoenix-oci-k3s",
        namespace="observability",
        resource={"kind": "ScrapeTarget", "name": "kubernetes-kubelet"},
        severity="medium",
        summary="Prometheus target kubernetes-kubelet is down.",
        rationale="Read-only telemetry shows the target is unavailable.",
        evidence=[
            {"type": "metric", "name": "up", "value": 0, "labels": {"job": "kubernetes-kubelet", "lastError": "server returned HTTP status 403 Forbidden"}},
        ],
        confidence=0.88,
        risk_score=35,
        suggested_actions=[ActionProposal("propose_config_review", "Review the observability path and confirm the target is still intended.", None)],
        requires_human_approval=True,
        rollback_hint="No mutation is expected for this observability-only incident.",
        policy_decision={"known_limitation": False},
        analyzer="demo",
        created_at="2026-06-10T04:00:00Z",
        labels={"scenario": "target_down", "signature": "target_down|observability|ScrapeTarget|kubernetes-kubelet|Prometheus target kubernetes-kubelet is down."},
    )

    incident = create_incident_event(
        source="prometheus",
        scenario="target_down",
        cluster="phoenix-oci-k3s",
        namespace="observability",
        resource_kind="ScrapeTarget",
        resource_name="kubernetes-kubelet",
        severity_hint="medium",
        summary="Prometheus target kubernetes-kubelet is down.",
        evidence=[
            {"type": "metric", "name": "up", "value": 0, "labels": {"job": "kubernetes-kubelet", "lastError": "server returned HTTP status 403 Forbidden"}},
        ],
        max_evidence_items=5,
        observed_at="2026-06-10T04:00:10Z",
    )

    artifacts = IncidentArtifactStore(config["incident_artifacts_path"], config["incident_artifacts"])
    advisory = {"status": "ok", "matched_findings": [{"message": "Kubelet scrape target is unavailable"}]}
    escalation_state = build_escalation_state(recommendation, config)
    timeline = ["incident detected", "prometheus target failure detected", "k8sgpt advisory completed", "recommendation generated"]
    summary = build_markdown_summary(recommendation, advisory=advisory, timeline_entries=timeline, escalation_state=escalation_state, simulation_only=True)
    payload = build_email_payload(recommendation, advisory=advisory, timeline_entries=timeline, escalation_state=escalation_state, simulation_only=True)

    artifacts.persist_summary(recommendation.incident_id, summary)
    artifacts.persist_evidence(recommendation.incident_id, incident, advisory)
    artifacts.persist_recommendation(recommendation.incident_id, recommendation)
    for timestamp, stage, message in [
        ("2026-06-10T04:00:10Z", "detection", "incident detected"),
        ("2026-06-10T04:00:22Z", "evidence", "prometheus target failure detected"),
        ("2026-06-10T04:00:31Z", "advisor", "k8sgpt advisory completed"),
        ("2026-06-10T04:00:40Z", "recommendation", "recommendation generated"),
    ]:
        artifacts.append_timeline(recommendation.incident_id, timestamp=timestamp, stage=stage, message=message)
    notification_result = send_incident_notification(config, payload)
    artifacts.append_notification_log(recommendation.incident_id, timestamp="2026-06-10T04:00:51Z", result=notification_result.to_dict())

    print(json.dumps({
        "incident_id": recommendation.incident_id,
        "artifact_dir": artifacts.artifact_dir(recommendation.incident_id),
        "notification_mode": notification_result.mode,
        "notification_success": notification_result.success,
        "remediation_plan": "none",
    }, indent=2, sort_keys=True))
PY
