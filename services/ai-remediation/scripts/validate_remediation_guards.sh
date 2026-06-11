#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

echo "Phoenix-Ops remediation guard validation"

PYTHONPATH="${ROOT_DIR}/services/ai-remediation" \
python3 - <<'PY'
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.approval.models import ApprovalRecord
from app.models.recommendation import ActionProposal, Recommendation
from app.remediation.guards import evaluate_guardrails
from app.remediation.planner import generate_plan
from app.store.execution_audit import ExecutionAuditStore

with tempfile.TemporaryDirectory() as tmpdir:
    config = {
        "kubeconfig_path": "/home/wajih/.kube/phoenix-k3s-oci.yaml",
        "request_timeouts": {"kubectl_seconds": 5},
        "execution_audit_path": str(Path(tmpdir) / "execution-audit.jsonl"),
        "namespace_allowlist": ["bankapp", "observability", "argocd"],
        "feature_flags": {"enable_execution": False},
        "auto_remediation": {
            "enabled": True,
            "allowed_actions": ["restart_banking_backend"],
            "allowed_namespace": "bankapp",
            "allowed_deployment": "banking-backend",
            "timeout_minutes": 10,
            "require_snapshot": True,
            "verify_rollout": True,
        },
        "remediation": {
            "namespace_allowlist": ["bankapp"],
            "resource_kind_allowlist": ["Deployment"],
            "protected_namespaces": ["argocd", "observability"],
            "max_blast_radius": "medium",
            "simulation_only": True,
            "execution_timeout_seconds": 30,
            "command_allowlist": ["get", "describe", "logs", "rollout restart", "rollout status"],
        },
    }
    recommendation = Recommendation(
        recommendation_id="rec-validate-1",
        incident_id="inc-validate-1",
        event_id="evt-validate-1",
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
    audit_store = ExecutionAuditStore(config["execution_audit_path"])
    with patch("app.remediation.guards._cluster_api_reachable", return_value=True):
        decision = evaluate_guardrails(plan, recommendation, config, approval=None, audit_store=audit_store, explicit_execute=False)
    assert not decision.allow and "valid approval is required before execution" in decision.reasons

    approval = ApprovalRecord(
        approval_id="apr-validate-1",
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
    audit_store.append(
        {
            "plan_id": plan.plan_id,
            "action": plan.remediation_id,
            "namespace": recommendation.namespace,
            "resource_kind": recommendation.resource["kind"],
            "resource": recommendation.resource["name"],
            "status": "simulated",
            "started_at": "2026-06-09T00:00:00Z",
            "finished_at": "2026-06-09T00:01:00Z",
        }
    )
    with patch("app.remediation.guards._cluster_api_reachable", return_value=True):
        decision = evaluate_guardrails(plan, recommendation, config, approval=approval, audit_store=audit_store, explicit_execute=False)
    assert not decision.allow and "duplicate execution prevented for this plan" in decision.reasons
    print("guard validation passed")
PY
