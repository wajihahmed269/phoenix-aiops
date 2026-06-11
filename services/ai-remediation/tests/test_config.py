from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import os
import tempfile
import unittest

from app.config.loader import CONFIG_PATH_ENV, load_config
from app.config.runtime import load_alerting_settings, load_auto_remediation_settings


class ConfigLoaderTests(unittest.TestCase):
    def test_load_default_config(self) -> None:
        config = load_config()
        self.assertEqual(config["cluster_name"], "phoenix-oci-k3s")
        self.assertEqual(config["auto_remediation"]["enabled"], False)

    def test_env_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.json"
            env_file = Path(tmpdir) / ".env.aiops"
            env_file.write_text(
                "\n".join(
                    [
                        "BREVO_API_KEY=test-secret",
                        "ALERT_FROM_EMAIL=phoenix@example.com",
                        "ALERT_TO_EMAIL=ops@example.com",
                        "ALERT_PROVIDER=brevo",
                        "ALERT_DRY_RUN=true",
                        "AUTO_RESTART_BANKING_BACKEND=true",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            path.write_text(json.dumps(_config_payload(str(env_file), cluster_name="test")), encoding="utf-8")
            previous = os.environ.get(CONFIG_PATH_ENV)
            os.environ[CONFIG_PATH_ENV] = str(path)
            try:
                config = load_config()
                self.assertEqual(config["cluster_name"], "test")
                self.assertTrue(load_alerting_settings(config).dry_run)
                self.assertTrue(load_auto_remediation_settings(config).enabled)
            finally:
                if previous is None:
                    os.environ.pop(CONFIG_PATH_ENV, None)
                else:
                    os.environ[CONFIG_PATH_ENV] = previous

    def test_missing_alerting_env_file_fails_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.json"
            path.write_text(json.dumps(_config_payload(str(Path(tmpdir) / "missing.env"))), encoding="utf-8")
            config = load_config(str(path))
            with self.assertRaises(ValueError):
                load_alerting_settings(config)


def _config_payload(env_file: str, *, cluster_name: str = "test") -> dict:
    return {
        "cluster_name": cluster_name,
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
        "approval_storage_path": "services/ai-remediation/data/runtime/approvals.jsonl",
        "execution_audit_path": "services/ai-remediation/data/runtime/execution-audit.jsonl",
        "incident_artifacts_path": "incident-artifacts",
        "incident_artifacts": {"max_json_bytes": 262144, "max_text_bytes": 65536, "max_timeline_entries": 2000, "timeline_summary_entries": 5},
        "alerting": {"env_file": env_file, "provider_timeout_seconds": 5, "provider_max_retries": 2, "max_notification_log_bytes": 65536},
        "auto_remediation": {"enabled": True, "allowed_actions": ["restart_banking_backend"], "allowed_namespace": "bankapp", "allowed_deployment": "banking-backend", "timeout_minutes": 10, "require_snapshot": True, "verify_rollout": True},
        "feature_flags": {
            "enable_prometheus_collector": False,
            "enable_loki_collector": False,
            "enable_kubernetes_collector": True,
            "enable_argo_collector": True,
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
            "protected_namespaces": ["argocd"],
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
            "namespace_allowlist": ["bankapp"],
            "filters": ["Pod"],
            "explicit_kubeconfig": "/tmp/kubeconfig",
        },
    }


if __name__ == "__main__":
    unittest.main()
