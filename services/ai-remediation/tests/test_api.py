from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from app.api.server import application


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.tempdir.name) / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
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
                    "local_storage_path": str(Path(self.tempdir.name) / "recommendations.jsonl"),
                    "feature_flags": {
                        "enable_prometheus_collector": False,
                        "enable_loki_collector": False,
                        "enable_kubernetes_collector": False,
                        "enable_argo_collector": False,
                        "enable_ollama_summary": False,
                        "enable_execution": False
                    }
                }
            ),
            encoding="utf-8",
        )
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
                "evidence": [
                    {
                        "type": "metric",
                        "name": "up",
                        "value": 0,
                        "labels": {"job": "kubernetes-kubelet", "lastError": "server returned HTTP status 403 Forbidden"},
                    }
                ],
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


def _call(method: str, path: str, payload: dict | None = None) -> tuple[str, dict]:
    raw = json.dumps(payload or {}).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(raw)) if method == "POST" else "0",
        "wsgi.input": io.BytesIO(raw),
    }
    response: dict = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        response["status"] = status
        response["headers"] = headers

    body = b"".join(application(environ, start_response))
    return response["status"], json.loads(body.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
