from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import subprocess
import tempfile
import unittest
from unittest.mock import patch

from app.approval.models import ApprovalRecord
from app.models.recommendation import ActionProposal, Recommendation
from app.remediation.planner import generate_plan
from app.remediation.runner import execute_plan


class ExecutionSimulationTests(unittest.TestCase):
    def test_simulation_only_enforced_and_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(tmpdir)
            recommendation = _recommendation()
            plan = generate_plan(recommendation, config)
            approval = _approval(recommendation, plan.plan_id, plan.remediation_id)

            def fake_run(command, **_kwargs):
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="ok\n", stderr="")

            with patch("app.remediation.guards._cluster_api_reachable", return_value=True), patch("app.remediation.snapshot.subprocess.run", side_effect=fake_run):
                result = execute_plan(plan, recommendation, config, approval=approval, explicit_execute=False)

            self.assertTrue(result.success)
            self.assertEqual(result.mode, "simulation")
            self.assertTrue(Path(config["execution_audit_path"]).exists())
            self.assertTrue(Path(config["incident_artifacts_path"], recommendation.incident_id, "rollback").exists())


def _recommendation() -> Recommendation:
    return Recommendation(
        recommendation_id="rec-sim-1",
        incident_id="inc-sim-1",
        event_id="evt-sim-1",
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


def _approval(recommendation: Recommendation, plan_id: str, remediation_id: str) -> ApprovalRecord:
    return ApprovalRecord(
        approval_id="apr-sim-1",
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
        "kubeconfig_path": "/home/wajih/.kube/phoenix-k3s-oci.yaml",
        "request_timeouts": {"kubectl_seconds": 5},
        "execution_audit_path": str(Path(tmpdir) / "execution-audit.jsonl"),
        "incident_artifacts_path": str(Path(tmpdir) / "incident-artifacts"),
        "namespace_allowlist": ["bankapp", "observability", "argocd"],
        "feature_flags": {"enable_execution": False},
        "alerting": {"env_file": str(env_file), "provider_timeout_seconds": 5, "provider_max_retries": 2, "max_notification_log_bytes": 65536},
        "auto_remediation": {"enabled": False, "allowed_actions": ["restart_banking_backend"], "allowed_namespace": "bankapp", "allowed_deployment": "banking-backend", "timeout_minutes": 10, "require_snapshot": True, "verify_rollout": True},
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


if __name__ == "__main__":
    unittest.main()
