#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export ALERT_DRY_RUN="${ALERT_DRY_RUN:-true}"
export AUTO_RESTART_BANKING_BACKEND="${AUTO_RESTART_BANKING_BACKEND:-false}"

echo "Phoenix-Ops banking-backend restart policy validation"
echo "ALERT_DRY_RUN=${ALERT_DRY_RUN}"
echo "AUTO_RESTART_BANKING_BACKEND=${AUTO_RESTART_BANKING_BACKEND}"

PYTHONPATH="${ROOT_DIR}/services/ai-remediation" \
python3 - <<'PY'
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.models.recommendation import ActionProposal, Recommendation
from app.remediation.auto_restart import evaluate_auto_restart_candidate
from app.remediation.planner import generate_plan
from app.remediation.runner import execute_plan
from app.store.execution_audit import ExecutionAuditStore
from app.store.json_store import JsonRecommendationStore

with tempfile.TemporaryDirectory() as tmpdir:
    env_file = Path(tmpdir) / ".env.aiops"
    env_file.write_text(
        "\n".join(
            [
                "BREVO_API_KEY=test-secret",
                "ALERT_FROM_EMAIL=phoenix@example.com",
                "ALERT_TO_EMAIL=ops@example.com",
                "ALERT_PROVIDER=brevo",
                "ALERT_DRY_RUN=true",
                f"AUTO_RESTART_BANKING_BACKEND={os.environ.get('AUTO_RESTART_BANKING_BACKEND', 'false')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    config = {
        "local_storage_path": str(Path(tmpdir) / "recommendations.jsonl"),
        "execution_audit_path": str(Path(tmpdir) / "execution-audit.jsonl"),
        "incident_artifacts_path": str(Path(tmpdir) / "incident-artifacts"),
        "incident_artifacts": {"max_json_bytes": 262144, "max_text_bytes": 65536, "max_timeline_entries": 2000, "timeline_summary_entries": 5, "max_notification_log_bytes": 65536},
        "namespace_allowlist": ["bankapp", "observability", "argocd"],
        "kubeconfig_path": "/home/wajih/.kube/phoenix-k3s-oci.yaml",
        "request_timeouts": {"kubectl_seconds": 5},
        "feature_flags": {"enable_execution": False},
        "alerting": {"env_file": str(env_file), "provider_timeout_seconds": 5, "provider_max_retries": 2, "max_notification_log_bytes": 65536},
        "auto_remediation": {"enabled": True, "allowed_actions": ["restart_banking_backend"], "allowed_namespace": "bankapp", "allowed_deployment": "banking-backend", "timeout_minutes": 10, "require_snapshot": True, "verify_rollout": True},
        "remediation": {"simulation_only": True, "namespace_allowlist": ["bankapp"], "resource_kind_allowlist": ["Deployment"], "protected_namespaces": ["argocd", "observability"], "max_blast_radius": "medium", "execution_timeout_seconds": 30, "command_allowlist": ["get", "describe", "logs", "rollout restart", "rollout status"]},
    }
    store = JsonRecommendationStore(config["local_storage_path"])
    audit_store = ExecutionAuditStore(config["execution_audit_path"])

    def recommendation(recommendation_id: str, created_at: str, resource_name: str = "banking-backend"):
        return Recommendation(
            recommendation_id=recommendation_id,
            incident_id=f"inc-{recommendation_id}",
            event_id=f"evt-{recommendation_id}",
            source="kubernetes",
            cluster="phoenix-oci-k3s",
            namespace="bankapp",
            resource={"kind": "Deployment", "name": resource_name},
            severity="medium",
            summary=f"Deployment unhealthy: bankapp/{resource_name}",
            rationale="test",
            evidence=[],
            confidence=0.8,
            risk_score=45,
            suggested_actions=[ActionProposal("propose_rollout_restart", "restart", None)],
            requires_human_approval=True,
            rollback_hint="snapshot",
            policy_decision={"known_limitation": False},
            analyzer="test",
            created_at=created_at,
            labels={"scenario": "deployment_unhealthy", "signature": f"deployment_unhealthy|bankapp|Deployment|{resource_name}|Deployment unhealthy: bankapp/{resource_name}"},
        )

    current = recommendation("rec-now", "2026-06-09T00:20:00Z")
    decision = evaluate_auto_restart_candidate(current, config, store, audit_store)
    assert decision.allow is False
    assert "AUTO_RESTART_BANKING_BACKEND" in decision.reason

    os.environ["AUTO_RESTART_BANKING_BACKEND"] = "true"
    env_file.write_text(env_file.read_text(encoding="utf-8").replace("AUTO_RESTART_BANKING_BACKEND=false", "AUTO_RESTART_BANKING_BACKEND=true"), encoding="utf-8")

    store.save_recommendation(recommendation("rec-prev", "2026-06-09T00:00:00Z"))
    plan = generate_plan(current, config)
    assert plan.remediation_id == "restart_banking_backend"

    decision = evaluate_auto_restart_candidate(current, config, store, audit_store)
    assert decision.allow is True
    assert decision.live_execution is False

    def fake_run(command, **_kwargs):
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="ok\n", stderr="")

    with patch("app.remediation.guards._cluster_api_reachable", return_value=True), patch("app.remediation.snapshot.subprocess.run", side_effect=fake_run):
        result = execute_plan(plan, current, config, approval=None, explicit_execute=False, auto_execute=True)
    assert result.mode == "simulation"
    assert Path(config["execution_audit_path"]).exists()

    try:
        generate_plan(recommendation("rec-frontend", "2026-06-09T00:20:00Z", resource_name="banking-frontend"), config)
    except ValueError:
        pass
    else:
        raise AssertionError("frontend should not be restartable")

    print("backend restart policy validation passed")
PY
