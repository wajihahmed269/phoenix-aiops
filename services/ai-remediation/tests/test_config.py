from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import os
from pathlib import Path
import tempfile
import unittest

from app.config.loader import CONFIG_PATH_ENV, load_config


class ConfigLoaderTests(unittest.TestCase):
    def test_load_default_config(self) -> None:
        config = load_config()
        self.assertEqual(config["cluster_name"], "phoenix-oci-k3s")
        self.assertEqual(config["feature_flags"]["enable_execution"], False)

    def test_env_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "cluster_name": "test",
                        "namespace_allowlist": ["bankapp"],
                        "prometheus_url": "http://127.0.0.1:9090",
                        "loki_url": "http://127.0.0.1:3100",
                        "kubernetes_mode": "kubectl",
                        "kubeconfig_path": "/tmp/kubeconfig",
                        "argo_namespace": "argocd",
                        "polling_intervals": {"prometheus_seconds": 60, "loki_seconds": 60, "kubernetes_seconds": 60, "argo_seconds": 60},
                        "request_timeouts": {"http_seconds": 5, "kubectl_seconds": 5},
                        "max_log_lines": 10,
                        "max_log_window_minutes": 5,
                        "max_evidence_items": 3,
                        "memory_thresholds": {"pod_working_set_mib_warn": 400},
                        "restart_thresholds": {"repeated_restart_count": 3, "crashloop_restart_count": 2},
                        "cooldowns": {"default_minutes": 15, "known_limitation_minutes": 60},
                        "local_storage_path": "services/ai-remediation/data/runtime/test.jsonl",
                        "feature_flags": {
                            "enable_prometheus_collector": False,
                            "enable_loki_collector": False,
                            "enable_kubernetes_collector": True,
                            "enable_argo_collector": True,
                            "enable_ollama_summary": False,
                            "enable_execution": False
                        }
                    }
                ),
                encoding="utf-8",
            )
            previous = os.environ.get(CONFIG_PATH_ENV)
            os.environ[CONFIG_PATH_ENV] = str(path)
            try:
                config = load_config()
                self.assertEqual(config["cluster_name"], "test")
            finally:
                if previous is None:
                    os.environ.pop(CONFIG_PATH_ENV, None)
                else:
                    os.environ[CONFIG_PATH_ENV] = previous


if __name__ == "__main__":
    unittest.main()
