from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tempfile
import unittest

from app.approval.store import ApprovalStore
from app.approval.workflow import approve_recommendation, latest_valid_approval, reject_recommendation, request_approval
from app.models.recommendation import ActionProposal, Recommendation
from app.remediation.planner import generate_plan
from app.store.json_store import JsonRecommendationStore


class ApprovalWorkflowTests(unittest.TestCase):
    def test_request_and_approve_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(tmpdir)
            rec_store = JsonRecommendationStore(config["local_storage_path"])
            approval_store = ApprovalStore(config["approval_storage_path"])
            recommendation = _recommendation()
            rec_store.save_recommendation(recommendation)
            plan = generate_plan(recommendation, config)

            requested = request_approval(approval_store, rec_store, recommendation, plan, requested_by="alice", reason="review required", config=config)
            self.assertEqual(requested.status, "requested")
            self.assertEqual(requested.plan_id, plan.plan_id)

            approved = approve_recommendation(approval_store, rec_store, recommendation, plan, approver="bob", reason="safe to simulate", config=config)
            self.assertEqual(approved.status, "approved")
            self.assertIsNotNone(latest_valid_approval(approval_store, recommendation.recommendation_id, plan, now=approved.decided_at))

    def test_reject_and_expiry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(tmpdir)
            rec_store = JsonRecommendationStore(config["local_storage_path"])
            approval_store = ApprovalStore(config["approval_storage_path"])
            recommendation = _recommendation()
            rec_store.save_recommendation(recommendation)
            plan = generate_plan(recommendation, config)

            request_approval(approval_store, rec_store, recommendation, plan, requested_by="alice", reason="review required", config=config)
            rejected = reject_recommendation(approval_store, rec_store, recommendation, plan, approver="bob", reason="too risky", config=config)
            self.assertEqual(rejected.status, "rejected")
            self.assertIsNone(latest_valid_approval(approval_store, recommendation.recommendation_id, plan))


def _recommendation() -> Recommendation:
    return Recommendation(
        recommendation_id="rec-approval-1",
        incident_id="inc-approval-1",
        event_id="evt-approval-1",
        source="kubernetes",
        cluster="phoenix-oci-k3s",
        namespace="bankapp",
        resource={"kind": "Deployment", "name": "banking-backend"},
        severity="medium",
        summary="Deployment unhealthy: bankapp/banking-backend",
        rationale="test rationale",
        evidence=[],
        confidence=0.8,
        risk_score=45,
        suggested_actions=[ActionProposal("propose_rollout_restart", "restart", "kubectl rollout restart deployment/banking-backend")],
        requires_human_approval=True,
        rollback_hint="snapshot",
        policy_decision={"known_limitation": False},
        analyzer="test",
        created_at="2026-06-09T00:00:00Z",
        labels={"scenario": "deployment_unhealthy"},
    )


def _config(tmpdir: str) -> dict:
    env_file = Path(tmpdir) / ".env.aiops"
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
    return {
        "local_storage_path": str(Path(tmpdir) / "recommendations.jsonl"),
        "approval_storage_path": str(Path(tmpdir) / "approvals.jsonl"),
        "incident_artifacts_path": str(Path(tmpdir) / "incident-artifacts"),
        "kubeconfig_path": "/home/wajih/.kube/phoenix-k3s-oci.yaml",
        "alerting": {"env_file": str(env_file), "provider_timeout_seconds": 5, "provider_max_retries": 2, "max_notification_log_bytes": 65536},
        "auto_remediation": {"enabled": False, "allowed_actions": ["restart_banking_backend"], "allowed_namespace": "bankapp", "allowed_deployment": "banking-backend", "timeout_minutes": 10, "require_snapshot": True, "verify_rollout": True},
        "remediation": {
            "approval_ttl_minutes": 30,
            "simulation_only": True,
            "execution_timeout_seconds": 30,
            "namespace_allowlist": ["bankapp"],
            "resource_kind_allowlist": ["Deployment"],
            "protected_namespaces": ["argocd", "observability"],
            "max_blast_radius": "medium",
            "rollback_retention_days": 7,
            "maintenance_windows_enabled": False,
            "escalation_minutes": {"t1": 1, "t5": 5, "t10": 10, "t15": 15},
            "command_allowlist": ["get", "describe", "logs", "rollout restart", "rollout status"],
        },
    }


if __name__ == "__main__":
    unittest.main()
