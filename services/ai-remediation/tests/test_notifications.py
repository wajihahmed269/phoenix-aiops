from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import tempfile
import unittest
from unittest.mock import patch

from app.config.runtime import load_alerting_settings
from app.models.recommendation import ActionProposal, Recommendation
from app.notifications.formatters import build_email_payload
from app.notifications.service import send_incident_notification
from app.store.incident_artifacts import IncidentArtifactStore


class NotificationTests(unittest.TestCase):
    def test_load_alerting_settings_from_env_file(self) -> None:
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
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            settings = load_alerting_settings(_config(str(env_file)))
            self.assertTrue(settings.dry_run)
            self.assertEqual(settings.provider, "brevo")

    def test_dry_run_notification_returns_success_without_network(self) -> None:
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
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            result = send_incident_notification(_config(str(env_file)), {"subject": "Test", "body": "Body"})
            self.assertTrue(result.success)
            self.assertEqual(result.mode, "dry-run")

    def test_live_brevo_notification_uses_bounded_http_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env.aiops"
            env_file.write_text(
                "\n".join(
                    [
                        "BREVO_API_KEY=test-secret",
                        "ALERT_FROM_EMAIL=phoenix@example.com",
                        "ALERT_TO_EMAIL=ops@example.com",
                        "ALERT_PROVIDER=brevo",
                        "ALERT_DRY_RUN=false",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            class _Response:
                status = 202

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

            with patch("app.notifications.providers.request.urlopen", return_value=_Response()) as mocked_urlopen:
                result = send_incident_notification(_config(str(env_file)), {"subject": "Test", "body": "Body"})
            self.assertTrue(result.success)
            self.assertEqual(result.status_code, 202)
            self.assertEqual(mocked_urlopen.call_args.kwargs["timeout"], 5)

    def test_email_payload_contains_required_fields(self) -> None:
        payload = build_email_payload(
            _recommendation(),
            advisory={"status": "ok", "matched_findings": [{"message": "Repeated readiness failures"}]},
            timeline_entries=["incident detected", "k8sgpt advisory completed", "recommendation generated"],
            escalation_state={"approval_state": "human_approval_required"},
            simulation_only=True,
        )
        body = payload["body"]
        self.assertIn("Incident: inc-test-001", body)
        self.assertIn("Problem: Restarting pods are causing degraded availability.", body)
        self.assertIn("Evidence: 0 evidence item(s)", body)
        self.assertIn("K8sGPT summary: Repeated readiness failures", body)
        self.assertIn("Action allowed?: Eligible only under the bounded banking-backend policy", body)
        self.assertIn("Simulation/live mode: simulation-only", body)
        self.assertIn("Next operator step: Review the bounded restart policy", body)
        self.assertNotIn("test-secret", body)

    def test_notification_log_and_incident_id_sanitization(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = IncidentArtifactStore(tmpdir, {"max_json_bytes": 4096, "max_text_bytes": 4096, "max_timeline_entries": 10, "timeline_summary_entries": 5, "max_notification_log_bytes": 4096})
            store.append_notification_log("../unsafe incident", timestamp="2026-06-10T03:12:51Z", result={"provider": "brevo", "mode": "dry-run", "success": True, "attempts": 0, "status_code": None, "detail": "ok"})
            paths = list(Path(tmpdir).iterdir())
            self.assertEqual(paths[0].name, "unsafe-incident")
            log = json.loads((paths[0] / "notifications.log").read_text(encoding="utf-8").strip())
            self.assertEqual(log["provider"], "brevo")


def _config(env_file: str) -> dict:
    return {
        "alerting": {
            "env_file": env_file,
            "provider_timeout_seconds": 5,
            "provider_max_retries": 2,
            "max_notification_log_bytes": 65536,
        }
    }


def _recommendation() -> Recommendation:
    return Recommendation(
        recommendation_id="rec-1",
        incident_id="inc-test-001",
        event_id="evt-1",
        source="kubernetes",
        cluster="phoenix-oci-k3s",
        namespace="bankapp",
        resource={"kind": "Deployment", "name": "banking-backend"},
        severity="high",
        summary="Restarting pods are causing degraded availability.",
        rationale="Deployment availability is below target.",
        evidence=[],
        confidence=0.8,
        risk_score=30,
        suggested_actions=[ActionProposal("propose_rollout_restart", "Review the deployment and consider a human-approved restart.", None)],
        requires_human_approval=True,
        rollback_hint="Rollback to the previous healthy revision if a future approved restart regresses.",
        policy_decision={},
        analyzer="test",
        created_at="2026-06-10T03:12:40Z",
    )


if __name__ == "__main__":
    unittest.main()
