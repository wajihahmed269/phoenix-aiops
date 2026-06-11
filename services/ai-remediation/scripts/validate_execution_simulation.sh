#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

echo "Phoenix-Ops execution simulation validation"

PYTHONPATH="${ROOT_DIR}/services/ai-remediation" \
python3 - <<'PY'
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.approval.models import ApprovalRecord
from app.models.recommendation import ActionProposal, Recommendation
from app.remediation.planner import generate_plan
from app.remediation.runner import execute_plan

with tempfile.TemporaryDirectory() as tmpdir:
    config = {
        "kubeconfig_path": "/home/wajih/.kube/phoenix-k3s-oci.yaml",
        "request_timeouts": {"kubectl_seconds": 5},
        "execution_audit_path": str(Path(tmpdir) / "execution-audit.jsonl"),
        "incident_artifacts_path": str(Path(tmpdir) / "incident-artifacts"),
        "namespace_allowlist": ["bankapp", "observability", "argocd"],
        "feature_flags": {"enable_execution": False},
        "auto_remediation": {
            "enabled": False,
            "allowed_actions": ["restart_banking_backend"],
            "allowed_namespace": "bankapp",
            "allowed_deployment": "banking-backend",
            "timeout_minutes": 10,
            "require_snapshot": True,
            "verify_rollout": True,
        },
        "remediation": {
            "simulation_only": True,
            "namespace_allowlist": ["bankapp"],
            "resource_kind_allowlist": ["Deployment"],
            "protected_namespaces": ["argocd", "observability"],
            "max_blast_radius": "medium",
            "execution_timeout_seconds": 30,
            "command_allowlist": ["get", "describe", "logs", "rollout restart", "rollout status"],
        },
    }
    recommendation = Recommendation(
        recommendation_id="rec-sim-validate-1",
        incident_id="inc-sim-validate-1",
        event_id="evt-sim-validate-1",
        source="kubernetes",
        cluster="phoenix-oci-k3s",
        namespace="bankapp",
        resource={"kind": "Deployment", "name": "banking-backend"},
        severity="medium",
        summary="Deployment unhealthy",
        rationale="test",
        evidence=[],
        confidence=0.8,
        risk_score=45,
        suggested_actions=[ActionProposal("propose_rollout_restart", "restart", None)],
        requires_human_approval=True,
        rollback_hint="snapshot",
        policy_decision={"known_limitation": False},
        analyzer="test",
        created_at="2026-06-09T00:00:00Z",
        labels={"scenario": "deployment_unhealthy"},
    )
    plan = generate_plan(recommendation, config)

    approval = ApprovalRecord(
        approval_id="apr-sim-validate-1",
        recommendation_id=recommendation.recommendation_id,
        incident_id=recommendation.incident_id,
        plan_id=plan.plan_id,
        remediation_id=plan.remediation_id,
        resource={"kind": recommendation.resource["kind"], "name": recommendation.resource["name"]},
        status="approved",
        requested_by="alice",
        approver="bob",
        requested_at="2026-06-09T00:00:00Z",
        decided_at="2026-06-09T00:01:00Z",
        reason="approved",
        scope="execute",
        expires_at="2099-06-09T00:30:00Z",
    )

    def fake_run(command, **_kwargs):
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="ok\n", stderr="")

    with patch("app.remediation.guards._cluster_api_reachable", return_value=True), patch("app.remediation.snapshot.subprocess.run", side_effect=fake_run):
        result = execute_plan(plan, recommendation, config, approval=approval, explicit_execute=False)

    assert result.mode == "simulation"
    assert result.success is True
    assert Path(config["execution_audit_path"]).exists()
    assert Path(config["incident_artifacts_path"], recommendation.incident_id, "rollback").exists()
    print("simulation validation passed")
PY
