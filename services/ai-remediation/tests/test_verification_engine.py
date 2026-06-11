from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from app.models.recommendation import ActionProposal, Recommendation
from app.remediation.planner import generate_plan
from app.remediation.verify import verify_remediation


class VerificationEngineTests(unittest.TestCase):
    def test_simulated_verification_skips_live_checks(self) -> None:
        recommendation = _recommendation()
        plan = generate_plan(recommendation, _config(tempfile.mkdtemp()))
        result = verify_remediation(plan, recommendation, _config(tempfile.mkdtemp()), simulated=True)
        self.assertTrue(result.success)
        self.assertEqual(result.mode, "simulation")

    def test_live_verification_handles_rollout_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            recommendation = _recommendation()
            config = _config(tmpdir, simulation_only=False)
            plan = generate_plan(recommendation, config)
            responses = [
                subprocess.CompletedProcess(args=["kubectl"], returncode=0, stdout="ok", stderr=""),
                subprocess.CompletedProcess(args=["kubectl"], returncode=0, stdout=json.dumps({"spec": {"replicas": 1}, "status": {"readyReplicas": 1}}), stderr=""),
                subprocess.CompletedProcess(args=["kubectl"], returncode=0, stdout=json.dumps({"items": []}), stderr=""),
            ]
            with patch("app.remediation.verify.subprocess.run", side_effect=responses):
                result = verify_remediation(plan, recommendation, config, simulated=False)
            self.assertTrue(result.success)
            self.assertEqual(result.mode, "live")


def _recommendation() -> Recommendation:
    return Recommendation(
        recommendation_id="rec-verify-1",
        incident_id="inc-verify-1",
        event_id="evt-verify-1",
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


def _config(tmpdir: str, *, simulation_only: bool = True) -> dict:
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
        "namespace_allowlist": ["bankapp", "observability", "argocd"],
        "kubeconfig_path": "/home/wajih/.kube/phoenix-k3s-oci.yaml",
        "alerting": {"env_file": str(env_file), "provider_timeout_seconds": 5, "provider_max_retries": 2, "max_notification_log_bytes": 65536},
        "auto_remediation": {"enabled": False, "allowed_actions": ["restart_banking_backend"], "allowed_namespace": "bankapp", "allowed_deployment": "banking-backend", "timeout_minutes": 10, "require_snapshot": True, "verify_rollout": True},
        "remediation": {
            "execution_timeout_seconds": 30,
            "namespace_allowlist": ["bankapp"],
            "resource_kind_allowlist": ["Deployment"],
            "max_blast_radius": "medium",
            "simulation_only": simulation_only,
        },
    }


if __name__ == "__main__":
    unittest.main()
