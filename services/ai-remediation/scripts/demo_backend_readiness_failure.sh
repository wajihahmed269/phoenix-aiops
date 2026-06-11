#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export PYTHONPATH="${ROOT_DIR}/services/ai-remediation"
export ALERT_DRY_RUN="${ALERT_DRY_RUN:-true}"
export AUTO_RESTART_BANKING_BACKEND="${AUTO_RESTART_BANKING_BACKEND:-false}"

echo "Phoenix-Ops backend readiness failure demo"
echo "ALERT_DRY_RUN=${ALERT_DRY_RUN}"
echo "AUTO_RESTART_BANKING_BACKEND=${AUTO_RESTART_BANKING_BACKEND}"

python3 - <<'PY'
import json
import tempfile
from pathlib import Path

from app.escalation.workflow import build_escalation_state
from app.models.factory import create_incident_event
from app.models.recommendation import ActionProposal, Recommendation
from app.notifications.formatters import build_email_payload, build_markdown_summary
from app.notifications.service import send_incident_notification
from app.remediation.auto_restart import evaluate_auto_restart_candidate
from app.remediation.planner import generate_plan
from app.store.execution_audit import ExecutionAuditStore
from app.store.incident_artifacts import IncidentArtifactStore
from app.store.json_store import JsonRecommendationStore

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
        "local_storage_path": str(tmp / "recommendations.jsonl"),
        "approval_storage_path": str(tmp / "approvals.jsonl"),
        "execution_audit_path": str(tmp / "execution-audit.jsonl"),
        "incident_artifacts_path": str(tmp / "incident-artifacts"),
        "incident_artifacts": {"max_json_bytes": 262144, "max_text_bytes": 65536, "max_timeline_entries": 2000, "timeline_summary_entries": 5, "max_notification_log_bytes": 65536},
        "namespace_allowlist": ["bankapp", "observability", "argocd"],
        "kubeconfig_path": "/home/wajih/.kube/phoenix-k3s-oci.yaml",
        "request_timeouts": {"kubectl_seconds": 5},
        "feature_flags": {"enable_execution": False},
        "alerting": {"env_file": str(env_file), "provider_timeout_seconds": 5, "provider_max_retries": 2, "max_notification_log_bytes": 65536},
        "auto_remediation": {"enabled": False, "allowed_actions": ["restart_banking_backend"], "allowed_namespace": "bankapp", "allowed_deployment": "banking-backend", "timeout_minutes": 10, "require_snapshot": True, "verify_rollout": True},
        "remediation": {"simulation_only": True, "namespace_allowlist": ["bankapp"], "resource_kind_allowlist": ["Deployment"], "protected_namespaces": ["argocd", "observability"], "max_blast_radius": "medium", "execution_timeout_seconds": 30, "approval_ttl_minutes": 30, "rollback_retention_days": 7, "maintenance_windows_enabled": False, "escalation_minutes": {"t1": 1, "t5": 5, "t10": 10, "t15": 15}, "command_allowlist": ["get", "describe", "logs", "rollout restart", "rollout status"]},
    }

    recommendation = Recommendation(
        recommendation_id="rec-demo-backend-1",
        incident_id="inc-demo-backend-1",
        event_id="evt-demo-backend-1",
        source="kubernetes",
        cluster="phoenix-oci-k3s",
        namespace="bankapp",
        resource={"kind": "Deployment", "name": "banking-backend"},
        severity="high",
        summary="BankApp readiness checks show banking-backend is unhealthy.",
        rationale="Repeated readiness probe failures and reduced availability.",
        evidence=[
            {"type": "metric", "name": "available_replicas", "value": 1, "labels": {"namespace": "bankapp", "deployment": "banking-backend"}},
        ],
        confidence=0.92,
        risk_score=55,
        suggested_actions=[ActionProposal("propose_rollout_restart", "Review the bounded restart policy for banking-backend.", None)],
        requires_human_approval=True,
        rollback_hint="Capture a snapshot before any operator-approved restart.",
        policy_decision={"known_limitation": False},
        analyzer="demo",
        created_at="2026-06-10T03:12:40Z",
        labels={"scenario": "deployment_unhealthy", "signature": "deployment_unhealthy|bankapp|Deployment|banking-backend|BankApp readiness checks show banking-backend is unhealthy."},
    )

    incident = create_incident_event(
        source="kubernetes",
        scenario="deployment_unhealthy",
        cluster="phoenix-oci-k3s",
        namespace="bankapp",
        resource_kind="Deployment",
        resource_name="banking-backend",
        severity_hint="high",
        summary="BankApp readiness checks show banking-backend is unhealthy.",
        evidence=[
            {"type": "metric", "name": "available_replicas", "value": 1, "labels": {"namespace": "bankapp", "deployment": "banking-backend"}},
        ],
        max_evidence_items=5,
        observed_at="2026-06-10T03:12:10Z",
    )

    store = JsonRecommendationStore(config["local_storage_path"])
    audit_store = ExecutionAuditStore(config["execution_audit_path"])
    artifacts = IncidentArtifactStore(config["incident_artifacts_path"], config["incident_artifacts"])
    advisory = {
        "status": "ok",
        "matched_findings": [{"message": "Readiness failures observed for banking-backend"}],
    }

    store.save_recommendation(recommendation)
    escalation_state = build_escalation_state(recommendation, config)
    summary = build_markdown_summary(recommendation, advisory=advisory, timeline_entries=["incident detected", "k8sgpt advisory completed", "recommendation generated"], escalation_state=escalation_state, simulation_only=True)
    payload = build_email_payload(recommendation, advisory=advisory, timeline_entries=["incident detected", "k8sgpt advisory completed", "recommendation generated"], escalation_state=escalation_state, simulation_only=True)
    decision = evaluate_auto_restart_candidate(recommendation, config, store, audit_store)
    plan = generate_plan(recommendation, config)

    artifacts.persist_summary(recommendation.incident_id, summary)
    artifacts.persist_evidence(recommendation.incident_id, incident, advisory)
    artifacts.persist_recommendation(recommendation.incident_id, recommendation)
    artifacts.append_timeline(recommendation.incident_id, timestamp="2026-06-10T03:12:10Z", stage="detection", message="incident detected")
    artifacts.append_timeline(recommendation.incident_id, timestamp="2026-06-10T03:12:31Z", stage="advisor", message="k8sgpt advisory completed")
    artifacts.append_timeline(recommendation.incident_id, timestamp="2026-06-10T03:12:40Z", stage="recommendation", message="recommendation generated")
    notification_result = send_incident_notification(config, payload)
    artifacts.append_notification_log(recommendation.incident_id, timestamp="2026-06-10T03:12:51Z", result=notification_result.to_dict())

    print(json.dumps({
        "incident_id": recommendation.incident_id,
        "plan_id": plan.plan_id,
        "remediation_id": plan.remediation_id,
        "auto_restart_decision": decision.to_dict(),
        "artifact_dir": artifacts.artifact_dir(recommendation.incident_id),
        "notification_mode": notification_result.mode,
        "notification_success": notification_result.success,
    }, indent=2, sort_keys=True))
PY
