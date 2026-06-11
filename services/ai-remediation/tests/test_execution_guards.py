from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tempfile
import unittest
from unittest.mock import patch

from app.approval.models import ApprovalRecord
from app.models.recommendation import ActionProposal, Recommendation
from app.remediation.guards import evaluate_guardrails
from app.remediation.planner import generate_plan
from app.store.execution_audit import ExecutionAuditStore


class ExecutionGuardsTests(unittest.TestCase):
    def test_blocks_without_approval_for_manual_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(tmpdir)
            recommendation = _recommendation()
            plan = generate_plan(recommendation, config)
            audit_store = ExecutionAuditStore(config["execution_audit_path"])
            with patch("app.remediation.guards._cluster_api_reachable", return_value=True):
                decision = evaluate_guardrails(plan, recommendation, config, approval=None, audit_store=audit_store, explicit_execute=False)
            self.assertFalse(decision.allow)
            self.assertIn("valid approval is required before execution", decision.reasons)

    def test_auto_execute_allows_only_banking_backend_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(tmpdir, env_enabled=True)
            recommendation = _recommendation()
            plan = generate_plan(recommendation, config)
            audit_store = ExecutionAuditStore(config["execution_audit_path"])
            with patch("app.remediation.guards._cluster_api_reachable", return_value=True):
                decision = evaluate_guardrails(plan, recommendation, config, approval=None, audit_store=audit_store, explicit_execute=False, auto_execute=True)
            self.assertTrue(decision.allow)

    def test_blocks_duplicate_execution_for_same_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(tmpdir, env_enabled=True)
            recommendation = _recommendation()
            plan = generate_plan(recommendation, config)
            audit_store = ExecutionAuditStore(config["execution_audit_path"])
            audit_store.append({"action": plan.remediation_id, "namespace": plan.namespace, "resource": {"kind": plan.resource_kind, "name": plan.resource_name}, "status": "simulated", "started_at": "2026-06-09T00:00:00Z", "finished_at": "2026-06-09T00:01:00Z"})
            with patch("app.remediation.guards._cluster_api_reachable", return_value=True):
                decision = evaluate_guardrails(plan, recommendation, config, approval=None, audit_store=audit_store, explicit_execute=False, auto_execute=True)
            self.assertFalse(decision.allow)
            self.assertIn("duplicate execution prevented for this remediation target", decision.reasons)


def _recommendation() -> Recommendation:
    return Recommendation(
        recommendation_id="rec-guard-1",
        incident_id="inc-guard-1",
        event_id="evt-guard-1",
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


def _config(tmpdir: str, *, env_enabled: bool = False) -> dict:
    env_file = Path(tmpdir) / ".env.aiops"
    env_file.write_text(
        "\n".join(
            [
                "BREVO_API_KEY=test-secret",
                "ALERT_FROM_EMAIL=phoenix@example.com",
                "ALERT_TO_EMAIL=ops@example.com",
                "ALERT_PROVIDER=brevo",
                "ALERT_DRY_RUN=true",
                f"AUTO_RESTART_BANKING_BACKEND={'true' if env_enabled else 'false'}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "kubeconfig_path": "/home/wajih/.kube/phoenix-k3s-oci.yaml",
        "request_timeouts": {"kubectl_seconds": 5},
        "execution_audit_path": str(Path(tmpdir) / "execution-audit.jsonl"),
        "namespace_allowlist": ["bankapp", "observability", "argocd"],
        "feature_flags": {"enable_execution": False},
        "alerting": {"env_file": str(env_file), "provider_timeout_seconds": 5, "provider_max_retries": 2, "max_notification_log_bytes": 65536},
        "auto_remediation": {"enabled": True, "allowed_actions": ["restart_banking_backend"], "allowed_namespace": "bankapp", "allowed_deployment": "banking-backend", "timeout_minutes": 10, "require_snapshot": True, "verify_rollout": True},
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


def _approval(recommendation: Recommendation, plan_id: str, remediation_id: str) -> ApprovalRecord:
    return ApprovalRecord(
        approval_id="apr-1",
        recommendation_id=recommendation.recommendation_id,
        incident_id=recommendation.incident_id,
        plan_id=plan_id,
        remediation_id=remediation_id,
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


if __name__ == "__main__":
    unittest.main()
