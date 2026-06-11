from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app.api.server import application


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.tempdir.name) / "config.json"
        env_file = Path(self.tempdir.name) / ".env.aiops"
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
        self.config_path.write_text(json.dumps(_config_payload(self.tempdir.name, str(env_file))), encoding="utf-8")
        os.environ["AIOPS_CONFIG_PATH"] = str(self.config_path)

    def tearDown(self) -> None:
        os.environ.pop("AIOPS_CONFIG_PATH", None)
        self.tempdir.cleanup()

    def test_health_endpoint(self) -> None:
        status, payload = _call("GET", "/healthz")
        self.assertEqual(status, "200 OK")
        self.assertEqual(payload["status"], "ok")

    def test_analyze_and_recommendation_lifecycle(self) -> None:
        status, payload = _call(
            "POST",
            "/v1/analyze",
            {
                "event_id": "evt-001",
                "source": "prometheus",
                "scenario": "target_down",
                "cluster": "phoenix-oci-k3s",
                "namespace": "observability",
                "resource": {"kind": "ScrapeTarget", "name": "kubernetes-kubelet"},
                "observed_at": "2026-06-08T12:00:00Z",
                "severity_hint": "low",
                "summary": "Prometheus target is down",
                "evidence": [{"type": "metric", "name": "up", "value": 0, "labels": {"job": "kubernetes-kubelet", "lastError": "server returned HTTP status 403 Forbidden"}}],
            },
        )
        self.assertEqual(status, "200 OK")
        recommendation_id = payload["recommendation_id"]

        from app.models.recommendation import Recommendation
        from app.store.json_store import JsonRecommendationStore

        store = JsonRecommendationStore(str(Path(self.tempdir.name) / "recommendations.jsonl"))
        store.save_recommendation(Recommendation.from_dict(payload))

        status, listed = _call("GET", "/v1/recommendations")
        self.assertEqual(status, "200 OK")
        self.assertEqual(len(listed["items"]), 1)

        status, fetched = _call("GET", f"/v1/recommendations/{recommendation_id}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(fetched["recommendation_id"], recommendation_id)

        status, acknowledged = _call("POST", f"/v1/recommendations/{recommendation_id}/acknowledge")
        self.assertEqual(status, "200 OK")
        self.assertEqual(acknowledged["status"], "acknowledged")

    def test_plan_approval_and_simulation_execution(self) -> None:
        status, payload = _call(
            "POST",
            "/v1/analyze",
            {
                "event_id": "evt-010",
                "source": "kubernetes",
                "scenario": "deployment_unhealthy",
                "cluster": "phoenix-oci-k3s",
                "namespace": "bankapp",
                "resource": {"kind": "Deployment", "name": "banking-backend"},
                "observed_at": "2026-06-08T12:00:00Z",
                "severity_hint": "medium",
                "summary": "Deployment unhealthy: bankapp/banking-backend",
                "evidence": [{"type": "state", "name": "deployment_status", "value": {"desired": 2, "available": 1}, "labels": {}}],
            },
        )
        self.assertEqual(status, "200 OK")
        recommendation_id = payload["recommendation_id"]

        from app.models.recommendation import Recommendation
        from app.store.json_store import JsonRecommendationStore

        store = JsonRecommendationStore(str(Path(self.tempdir.name) / "recommendations.jsonl"))
        store.save_recommendation(Recommendation.from_dict(payload))

        status, plan = _call("GET", f"/v1/recommendations/{recommendation_id}/plan")
        self.assertEqual(status, "200 OK")
        self.assertEqual(plan["remediation_id"], "restart_banking_backend")

        status, requested = _call("POST", f"/v1/recommendations/{recommendation_id}/approval-request", {"requested_by": "wajih", "reason": "safe restart review"})
        self.assertEqual(status, "200 OK")
        self.assertEqual(requested["status"], "requested")
        self.assertEqual(requested["plan_id"], plan["plan_id"])

        status, approved = _call("POST", f"/v1/recommendations/{recommendation_id}/approve", {"approver": "wajih", "reason": "approved for simulation"})
        self.assertEqual(status, "200 OK")
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["plan_id"], plan["plan_id"])

        with patch("app.remediation.guards._cluster_api_reachable", return_value=True), patch("app.remediation.snapshot.subprocess.run") as mocked_run:
            mocked_run.return_value.stdout = "ok\n"
            mocked_run.return_value.stderr = ""
            status, execution = _call("POST", f"/v1/recommendations/{recommendation_id}/execute", {"explicit_execute": False})
        self.assertEqual(status, "200 OK")
        self.assertEqual(execution["mode"], "simulation")
        self.assertTrue(execution["success"])
        self.assertTrue(Path(self.tempdir.name, "execution-audit.jsonl").exists())

    def test_poll_once_with_no_events_returns_success(self) -> None:
        with patch("app.pipeline.poller.collect_target_down_events", return_value=[]), patch("app.pipeline.poller.collect_log_anomaly_events", return_value=[]), patch("app.pipeline.poller.collect_kubernetes_events", return_value=[]), patch("app.pipeline.poller.collect_argo_events", return_value=[]):
            status, payload = _call("POST", "/v1/poll-once")
        self.assertEqual(status, "200 OK")
        self.assertEqual(payload["stored_recommendations"], 0)


def _config_payload(tmpdir: str, env_file: str) -> dict:
    return {
        "cluster_name": "phoenix-oci-k3s",
        "namespace_allowlist": ["bankapp", "observability", "argocd"],
        "prometheus_url": "http://127.0.0.1:9090",
        "loki_url": "http://127.0.0.1:3100",
        "kubernetes_mode": "kubectl",
        "kubeconfig_path": "/home/wajih/.kube/phoenix-k3s-oci.yaml",
        "argo_namespace": "argocd",
        "polling_intervals": {"prometheus_seconds": 60, "loki_seconds": 120, "kubernetes_seconds": 60, "argo_seconds": 90},
        "request_timeouts": {"http_seconds": 1, "kubectl_seconds": 1},
        "max_log_lines": 25,
        "max_log_window_minutes": 15,
        "max_evidence_items": 5,
        "memory_thresholds": {"pod_working_set_mib_warn": 400},
        "restart_thresholds": {"repeated_restart_count": 3, "crashloop_restart_count": 2},
        "cooldowns": {"default_minutes": 15, "known_limitation_minutes": 360},
        "local_storage_path": str(Path(tmpdir) / "recommendations.jsonl"),
        "approval_storage_path": str(Path(tmpdir) / "approvals.jsonl"),
        "execution_audit_path": str(Path(tmpdir) / "execution-audit.jsonl"),
        "incident_artifacts_path": str(Path(tmpdir) / "incident-artifacts"),
        "incident_artifacts": {"max_json_bytes": 262144, "max_text_bytes": 65536, "max_timeline_entries": 2000, "timeline_summary_entries": 5},
        "alerting": {"env_file": env_file, "provider_timeout_seconds": 5, "provider_max_retries": 2, "max_notification_log_bytes": 65536},
        "auto_remediation": {"enabled": False, "allowed_actions": ["restart_banking_backend"], "allowed_namespace": "bankapp", "allowed_deployment": "banking-backend", "timeout_minutes": 10, "require_snapshot": True, "verify_rollout": True},
        "feature_flags": {
            "enable_prometheus_collector": False,
            "enable_loki_collector": False,
            "enable_kubernetes_collector": False,
            "enable_argo_collector": False,
            "enable_k8sgpt_collector": False,
            "enable_remediation_planner": True,
            "enable_approval_workflow": True,
            "enable_snapshot_capture": True,
            "enable_verification": True,
            "enable_ollama_summary": False,
            "enable_execution": False,
        },
        "remediation": {
            "simulation_only": True,
            "execution_timeout_seconds": 30,
            "approval_ttl_minutes": 30,
            "namespace_allowlist": ["bankapp"],
            "resource_kind_allowlist": ["Deployment"],
            "protected_namespaces": ["argocd", "observability"],
            "max_blast_radius": "medium",
            "rollback_retention_days": 7,
            "maintenance_windows_enabled": False,
            "escalation_minutes": {"t1": 1, "t5": 5, "t10": 10, "t15": 15},
            "command_allowlist": ["get", "describe", "logs", "rollout restart", "rollout status"],
        },
        "k8sgpt": {
            "binary": "k8sgpt",
            "timeout_seconds": 20,
            "max_output_kb": 256,
            "namespace_allowlist": ["bankapp", "observability", "argocd"],
            "filters": ["Pod", "Deployment"],
            "explicit_kubeconfig": "/home/wajih/.kube/phoenix-k3s-oci.yaml",
        },
    }


def _call(method: str, path: str, payload: dict | None = None) -> tuple[str, dict]:
    raw = json.dumps(payload or {}).encode("utf-8")
    environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "CONTENT_LENGTH": str(len(raw)) if method == "POST" else "0", "wsgi.input": io.BytesIO(raw)}
    response: dict = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        response["status"] = status
        response["headers"] = headers

    body = b"".join(application(environ, start_response))
    return response["status"], json.loads(body.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
