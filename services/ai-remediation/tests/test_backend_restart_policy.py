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
from app.notifications.formatters import build_email_payload
from app.notifications.service import send_incident_notification
from app.remediation.auto_restart import evaluate_auto_restart_candidate
from app.remediation.planner import generate_plan
from app.remediation.runner import execute_plan
from app.store.execution_audit import ExecutionAuditStore
from app.store.json_store import JsonRecommendationStore


class BackendRestartPolicyTests(unittest.TestCase):
    def test_auto_restart_disabled_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(tmpdir, config_enabled=False, env_enabled=False)
            store = JsonRecommendationStore(config["local_storage_path"])
            audit_store = ExecutionAuditStore(config["execution_audit_path"])
            recommendation = _recommendation(created_at="2026-06-09T00:20:00Z")
            store.save_recommendation(_recommendation(recommendation_id="rec-prev", created_at="2026-06-09T00:00:00Z"))
            decision = evaluate_auto_restart_candidate(recommendation, config, store, audit_store)
            self.assertFalse(decision.allow)

    def test_only_banking_backend_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(tmpdir)
            plan = generate_plan(_recommendation(), config)
            self.assertEqual(plan.remediation_id, "restart_banking_backend")

    def test_mysql_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(tmpdir)
            with self.assertRaises(ValueError):
                generate_plan(_recommendation(resource_kind="StatefulSet", resource_name="bankapp-mysql"), config)

    def test_frontend_rejected_for_now(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(tmpdir)
            with self.assertRaises(ValueError):
                generate_plan(_recommendation(resource_name="banking-frontend"), config)

    def test_arbitrary_deployment_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(tmpdir)
            with self.assertRaises(ValueError):
                generate_plan(_recommendation(resource_name="other-service"), config)

    def test_snapshot_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(tmpdir, require_snapshot=False)
            store = JsonRecommendationStore(config["local_storage_path"])
            audit_store = ExecutionAuditStore(config["execution_audit_path"])
            store.save_recommendation(_recommendation(recommendation_id="rec-prev", created_at="2026-06-09T00:00:00Z"))
            decision = evaluate_auto_restart_candidate(_recommendation(created_at="2026-06-09T00:20:00Z"), config, store, audit_store)
            self.assertFalse(decision.allow)
            self.assertIn("snapshot", decision.reason)

    def test_rollout_verification_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(tmpdir, verify_rollout=False)
            store = JsonRecommendationStore(config["local_storage_path"])
            audit_store = ExecutionAuditStore(config["execution_audit_path"])
            store.save_recommendation(_recommendation(recommendation_id="rec-prev", created_at="2026-06-09T00:00:00Z"))
            decision = evaluate_auto_restart_candidate(_recommendation(created_at="2026-06-09T00:20:00Z"), config, store, audit_store)
            self.assertFalse(decision.allow)
            self.assertIn("rollout", decision.reason)

    def test_audit_written_for_simulated_auto_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(tmpdir)
            store = JsonRecommendationStore(config["local_storage_path"])
            audit_store = ExecutionAuditStore(config["execution_audit_path"])
            store.save_recommendation(_recommendation(recommendation_id="rec-prev", created_at="2026-06-09T00:00:00Z"))
            recommendation = _recommendation(created_at="2026-06-09T00:20:00Z")
            decision = evaluate_auto_restart_candidate(recommendation, config, store, audit_store)
            self.assertTrue(decision.allow)
            plan = generate_plan(recommendation, config)

            def fake_run(command, **_kwargs):
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="ok\n", stderr="")

            with patch("app.remediation.guards._cluster_api_reachable", return_value=True), patch("app.remediation.snapshot.subprocess.run", side_effect=fake_run):
                result = execute_plan(plan, recommendation, config, approval=None, explicit_execute=False, auto_execute=True)
            self.assertTrue(result.success)
            self.assertEqual(result.mode, "simulation")
            self.assertTrue(Path(config["execution_audit_path"]).exists())

    def test_dry_run_notification_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _config(tmpdir)
            payload = build_email_payload(
                _recommendation(),
                advisory={"status": "ok", "matched_findings": [{"message": "backend unhealthy"}]},
                timeline_entries=["incident detected", "notification sent"],
                escalation_state={"approval_state": "bounded_auto_restart_policy"},
                simulation_only=True,
            )
            result = send_incident_notification(config, payload)
            self.assertTrue(result.success)
            self.assertEqual(result.mode, "dry-run")

    def test_no_secrets_printed(self) -> None:
        payload = build_email_payload(
            _recommendation(),
            advisory={"status": "ok", "matched_findings": [{"message": "backend unhealthy"}]},
            timeline_entries=["incident detected", "notification sent"],
            escalation_state={"approval_state": "bounded_auto_restart_policy"},
            simulation_only=True,
        )
        self.assertNotIn("test-secret", payload["body"])


def _recommendation(
    recommendation_id: str = "rec-auto-1",
    *,
    created_at: str = "2026-06-09T00:20:00Z",
    resource_kind: str = "Deployment",
    resource_name: str = "banking-backend",
) -> Recommendation:
    return Recommendation(
        recommendation_id=recommendation_id,
        incident_id=f"inc-{recommendation_id}",
        event_id=f"evt-{recommendation_id}",
        source="kubernetes",
        cluster="phoenix-oci-k3s",
        namespace="bankapp",
        resource={"kind": resource_kind, "name": resource_name},
        severity="medium",
        summary="Deployment unhealthy: bankapp/banking-backend",
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
        labels={"scenario": "deployment_unhealthy", "signature": f"deployment_unhealthy|bankapp|{resource_kind}|{resource_name}|Deployment unhealthy: bankapp/{resource_name}"},
    )


def _config(
    tmpdir: str,
    *,
    config_enabled: bool = True,
    env_enabled: bool = True,
    require_snapshot: bool = True,
    verify_rollout: bool = True,
) -> dict:
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
        "local_storage_path": str(Path(tmpdir) / "recommendations.jsonl"),
        "execution_audit_path": str(Path(tmpdir) / "execution-audit.jsonl"),
        "incident_artifacts_path": str(Path(tmpdir) / "incident-artifacts"),
        "incident_artifacts": {"max_json_bytes": 262144, "max_text_bytes": 65536, "max_timeline_entries": 2000, "timeline_summary_entries": 5, "max_notification_log_bytes": 65536},
        "namespace_allowlist": ["bankapp", "observability", "argocd"],
        "kubeconfig_path": "/home/wajih/.kube/phoenix-k3s-oci.yaml",
        "request_timeouts": {"kubectl_seconds": 5},
        "feature_flags": {"enable_execution": False},
        "alerting": {"env_file": str(env_file), "provider_timeout_seconds": 5, "provider_max_retries": 2, "max_notification_log_bytes": 65536},
        "auto_remediation": {"enabled": config_enabled, "allowed_actions": ["restart_banking_backend"], "allowed_namespace": "bankapp", "allowed_deployment": "banking-backend", "timeout_minutes": 10, "require_snapshot": require_snapshot, "verify_rollout": verify_rollout},
        "remediation": {"simulation_only": True, "namespace_allowlist": ["bankapp"], "resource_kind_allowlist": ["Deployment"], "protected_namespaces": ["argocd", "observability"], "max_blast_radius": "medium", "execution_timeout_seconds": 30, "command_allowlist": ["get", "describe", "logs", "rollout restart", "rollout status"]},
    }


if __name__ == "__main__":
    unittest.main()
