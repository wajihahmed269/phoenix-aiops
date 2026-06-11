#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export PYTHONPATH="${ROOT_DIR}/services/ai-remediation"

echo "Phoenix-Ops K8sGPT unavailable demo"

python3 - <<'PY'
import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.collectors.k8sgpt import collect_namespace_advisories
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
        "feature_flags": {"enable_k8sgpt_collector": True},
        "k8sgpt": {"binary": "k8sgpt", "timeout_seconds": 20, "max_output_kb": 256, "namespace_allowlist": ["bankapp", "observability", "argocd"], "filters": ["Pod", "Deployment"], "explicit_kubeconfig": "/home/wajih/.kube/phoenix-k3s-oci.yaml"},
        "namespace_allowlist": ["bankapp", "observability", "argocd"],
    }

    recommendation = Recommendation(
        recommendation_id="rec-demo-k8sgpt-1",
        incident_id="inc-demo-k8sgpt-1",
        event_id="evt-demo-k8sgpt-1",
        source="kubernetes",
        cluster="phoenix-oci-k3s",
        namespace="bankapp",
        resource={"kind": "Deployment", "name": "banking-backend"},
        severity="medium",
        summary="BankApp restart evidence is present, but K8sGPT is unavailable for this run.",
        rationale="The advisory path must continue safely even when the CLI is missing.",
        evidence=[],
        confidence=0.75,
        risk_score=25,
        suggested_actions=[ActionProposal("propose_config_review", "Continue with read-only evidence and note the missing advisor.", None)],
        requires_human_approval=True,
        rollback_hint="No mutation is expected in this demo.",
        policy_decision={"known_limitation": False},
        analyzer="demo",
        created_at="2026-06-10T04:30:00Z",
        labels={"scenario": "deployment_unhealthy", "signature": "deployment_unhealthy|bankapp|Deployment|banking-backend|BankApp restart evidence is present, but K8sGPT is unavailable for this run."},
    )

    incident = create_incident_event(
        source="kubernetes",
        scenario="deployment_unhealthy",
        cluster="phoenix-oci-k3s",
        namespace="bankapp",
        resource_kind="Deployment",
        resource_name="banking-backend",
        severity_hint="medium",
        summary="BankApp restart evidence is present, but K8sGPT is unavailable for this run.",
        evidence=[],
        max_evidence_items=5,
        observed_at="2026-06-10T04:30:10Z",
    )

    with patch("app.collectors.k8sgpt.subprocess.run", side_effect=FileNotFoundError):
        advisory = collect_namespace_advisories(config, ["bankapp"])["bankapp"]

    artifacts = IncidentArtifactStore(config["incident_artifacts_path"], config["incident_artifacts"])
    escalation_state = build_escalation_state(recommendation, config)
    timeline = ["incident detected", "k8sgpt advisory unavailable", "recommendation generated"]
    summary = build_markdown_summary(recommendation, advisory=advisory, timeline_entries=timeline, escalation_state=escalation_state, simulation_only=True)
    payload = build_email_payload(recommendation, advisory=advisory, timeline_entries=timeline, escalation_state=escalation_state, simulation_only=True)

    artifacts.persist_summary(recommendation.incident_id, summary)
    artifacts.persist_evidence(recommendation.incident_id, incident, advisory)
    artifacts.persist_recommendation(recommendation.incident_id, recommendation)
    for timestamp, stage, message in [
        ("2026-06-10T04:30:10Z", "detection", "incident detected"),
        ("2026-06-10T04:30:22Z", "advisor", "k8sgpt advisory unavailable"),
        ("2026-06-10T04:30:40Z", "recommendation", "recommendation generated"),
    ]:
        artifacts.append_timeline(recommendation.incident_id, timestamp=timestamp, stage=stage, message=message)
    notification_result = send_incident_notification(config, payload)
    artifacts.append_notification_log(recommendation.incident_id, timestamp="2026-06-10T04:30:51Z", result=notification_result.to_dict())

    print(json.dumps({
        "incident_id": recommendation.incident_id,
        "artifact_dir": artifacts.artifact_dir(recommendation.incident_id),
        "k8sgpt_status": advisory.get("status"),
        "k8sgpt_error": advisory.get("error"),
        "notification_mode": notification_result.mode,
        "notification_success": notification_result.success,
    }, indent=2, sort_keys=True))
PY
