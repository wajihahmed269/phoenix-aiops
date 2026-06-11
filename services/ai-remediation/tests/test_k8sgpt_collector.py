from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import subprocess
import unittest
from unittest.mock import patch

from app.collectors.k8sgpt import attach_advisory_evidence, collect_namespace_advisories
from app.models.factory import create_incident_event


BASE_CONFIG = {
    "cluster_name": "phoenix-oci-k3s",
    "namespace_allowlist": ["bankapp", "observability", "argocd"],
    "prometheus_url": "http://127.0.0.1:9090",
    "loki_url": "http://127.0.0.1:3100",
    "kubernetes_mode": "kubectl",
    "kubeconfig_path": "/home/wajih/.kube/phoenix-k3s-oci.yaml",
    "argo_namespace": "argocd",
    "polling_intervals": {"prometheus_seconds": 60, "loki_seconds": 120, "kubernetes_seconds": 60, "argo_seconds": 90},
    "request_timeouts": {"http_seconds": 5, "kubectl_seconds": 10},
    "max_log_lines": 25,
    "max_log_window_minutes": 15,
    "max_evidence_items": 5,
    "memory_thresholds": {"pod_working_set_mib_warn": 400},
    "restart_thresholds": {"repeated_restart_count": 3, "crashloop_restart_count": 2},
    "cooldowns": {"default_minutes": 15, "known_limitation_minutes": 360},
    "local_storage_path": "services/ai-remediation/data/runtime/test.jsonl",
    "approval_storage_path": "services/ai-remediation/data/runtime/test-approvals.jsonl",
    "execution_audit_path": "services/ai-remediation/data/runtime/test-audit.jsonl",
    "incident_artifacts_path": "incident-artifacts",
    "incident_artifacts": {
        "max_json_bytes": 262144,
        "max_text_bytes": 65536,
        "max_timeline_entries": 2000,
        "timeline_summary_entries": 5,
    },
    "alerting": {
        "env_file": "/tmp/.env.aiops",
        "provider_timeout_seconds": 5,
        "provider_max_retries": 2,
        "max_notification_log_bytes": 65536,
    },
    "auto_remediation": {
        "enabled": False,
        "allowed_actions": ["restart_banking_backend"],
        "allowed_namespace": "bankapp",
        "allowed_deployment": "banking-backend",
        "timeout_minutes": 10,
        "require_snapshot": True,
        "verify_rollout": True,
    },
    "feature_flags": {
        "enable_prometheus_collector": False,
        "enable_loki_collector": False,
        "enable_kubernetes_collector": False,
        "enable_argo_collector": False,
        "enable_k8sgpt_collector": True,
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


class K8sGPTCollectorTests(unittest.TestCase):
    def test_missing_binary_gracefully_degrades(self) -> None:
        with patch("app.collectors.k8sgpt.subprocess.run", side_effect=FileNotFoundError):
            result = collect_namespace_advisories(_config(), ["bankapp"])
        self.assertEqual(result["bankapp"]["status"], "unavailable")
        self.assertEqual(result["bankapp"]["error"], "binary_not_found")

    def test_invalid_json_gracefully_degrades(self) -> None:
        completed = subprocess.CompletedProcess(args=["k8sgpt"], returncode=0, stdout="{bad json", stderr="")
        with patch("app.collectors.k8sgpt.subprocess.run", return_value=completed):
            result = collect_namespace_advisories(_config(), ["bankapp"])
        self.assertEqual(result["bankapp"]["error"], "invalid_json")

    def test_timeout_gracefully_degrades(self) -> None:
        with patch("app.collectors.k8sgpt.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["k8sgpt"], timeout=20)):
            result = collect_namespace_advisories(_config(), ["bankapp"])
        self.assertEqual(result["bankapp"]["error"], "timeout")

    def test_namespace_not_allowed_is_blocked(self) -> None:
        result = collect_namespace_advisories(_config(), ["kube-system"])
        self.assertEqual(result["kube-system"]["error"], "namespace_not_allowed")

    def test_evidence_normalization_and_suppression(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["k8sgpt"],
            returncode=0,
            stdout='{"results":[{"kind":"Deployment","name":"banking-backend","namespace":"bankapp","details":"Repeated readiness failures","severity":"high"},{"kind":"Pod","name":"helm-hook-123","namespace":"bankapp","details":"Completed Helm Job","severity":"low"}]}',
            stderr="",
        )
        with patch("app.collectors.k8sgpt.subprocess.run", return_value=completed):
            result = collect_namespace_advisories(_config(), ["bankapp"])

        self.assertEqual(result["bankapp"]["status"], "ok")
        self.assertEqual(len(result["bankapp"]["findings"]), 1)
        self.assertEqual(len(result["bankapp"]["suppressed_findings"]), 1)

        incident = create_incident_event(
            source="kubernetes",
            scenario="deployment_unhealthy",
            cluster="phoenix-oci-k3s",
            namespace="bankapp",
            resource_kind="Deployment",
            resource_name="banking-backend",
            severity_hint="high",
            summary="Deployment unhealthy: bankapp/banking-backend",
            evidence=[],
            max_evidence_items=5,
            observed_at="2026-06-09T00:00:00Z",
        )
        enriched, advisory = attach_advisory_evidence(incident, result["bankapp"], max_evidence_items=5)
        self.assertEqual(advisory["matched_findings"][0]["message"], "Repeated readiness failures")
        self.assertEqual(enriched.evidence[-1].type, "advisor")

    def test_disabled_collector_returns_disabled_status(self) -> None:
        config = _config()
        config["feature_flags"]["enable_k8sgpt_collector"] = False
        result = collect_namespace_advisories(config, ["bankapp"])
        self.assertEqual(result["bankapp"]["status"], "disabled")

    def test_unexpected_schema_gracefully_degrades(self) -> None:
        completed = subprocess.CompletedProcess(args=["k8sgpt"], returncode=0, stdout='{"unexpected":"shape"}', stderr="")
        with patch("app.collectors.k8sgpt.subprocess.run", return_value=completed):
            result = collect_namespace_advisories(_config(), ["bankapp"])
        self.assertEqual(result["bankapp"]["error"], "unexpected_schema")


def _config() -> dict:
    return {
        **BASE_CONFIG,
        "feature_flags": dict(BASE_CONFIG["feature_flags"]),
        "k8sgpt": {
            **BASE_CONFIG["k8sgpt"],
            "filters": list(BASE_CONFIG["k8sgpt"]["filters"]),
            "namespace_allowlist": list(BASE_CONFIG["k8sgpt"]["namespace_allowlist"]),
        },
    }


if __name__ == "__main__":
    unittest.main()
