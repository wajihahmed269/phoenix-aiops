from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL_KEYS = {
    "cluster_name",
    "namespace_allowlist",
    "prometheus_url",
    "loki_url",
    "kubernetes_mode",
    "kubeconfig_path",
    "argo_namespace",
    "polling_intervals",
    "request_timeouts",
    "max_log_lines",
    "max_log_window_minutes",
    "max_evidence_items",
    "memory_thresholds",
    "restart_thresholds",
    "cooldowns",
    "local_storage_path",
    "approval_storage_path",
    "execution_audit_path",
    "incident_artifacts_path",
    "incident_artifacts",
    "alerting",
    "auto_remediation",
    "feature_flags",
    "remediation",
    "k8sgpt",
}

REQUIRED_K8SGPT_KEYS = {
    "binary",
    "timeout_seconds",
    "max_output_kb",
    "namespace_allowlist",
    "filters",
    "explicit_kubeconfig",
}

REQUIRED_ALERTING_KEYS = {
    "env_file",
    "provider_timeout_seconds",
    "provider_max_retries",
    "max_notification_log_bytes",
}

REQUIRED_INCIDENT_ARTIFACT_KEYS = {
    "max_json_bytes",
    "max_text_bytes",
    "max_timeline_entries",
    "timeline_summary_entries",
}

REQUIRED_AUTO_REMEDIATION_KEYS = {
    "enabled",
    "allowed_actions",
    "allowed_namespace",
    "allowed_deployment",
    "timeout_minutes",
    "require_snapshot",
    "verify_rollout",
}

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "default.json"
CONFIG_PATH_ENV = "AIOPS_CONFIG_PATH"


def load_config(config_path: str | None = None) -> dict[str, Any]:
    resolved = Path(config_path or os.environ.get(CONFIG_PATH_ENV) or DEFAULT_CONFIG_PATH)
    with resolved.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    config["_config_path"] = str(resolved.resolve())
    _normalize_config(config)
    _validate_config(config)
    return config


def _normalize_config(config: dict[str, Any]) -> None:
    for key in ("kubeconfig_path", "local_storage_path", "approval_storage_path", "execution_audit_path", "incident_artifacts_path"):
        if key in config and isinstance(config[key], str):
            config[key] = str(Path(config[key]).expanduser())
    if "k8sgpt" in config and isinstance(config["k8sgpt"], dict):
        kubeconfig = config["k8sgpt"].get("explicit_kubeconfig")
        if isinstance(kubeconfig, str):
            config["k8sgpt"]["explicit_kubeconfig"] = str(Path(kubeconfig).expanduser())
    if "alerting" in config and isinstance(config["alerting"], dict):
        env_file = config["alerting"].get("env_file")
        if isinstance(env_file, str):
            config["alerting"]["env_file"] = str(Path(env_file).expanduser())


def _validate_config(config: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_TOP_LEVEL_KEYS - set(config))
    if missing:
        raise ValueError(f"missing config keys: {', '.join(missing)}")

    if config["kubernetes_mode"] != "kubectl":
        raise ValueError("only kubectl mode is supported in this phase")

    if not isinstance(config["namespace_allowlist"], list) or not config["namespace_allowlist"]:
        raise ValueError("namespace_allowlist must be a non-empty list")

    remediation = config["remediation"]
    required_remediation_keys = {
        "simulation_only",
        "execution_timeout_seconds",
        "approval_ttl_minutes",
        "namespace_allowlist",
        "resource_kind_allowlist",
        "protected_namespaces",
        "max_blast_radius",
        "rollback_retention_days",
        "maintenance_windows_enabled",
        "escalation_minutes",
        "command_allowlist",
    }
    missing_remediation = sorted(required_remediation_keys - set(remediation))
    if missing_remediation:
        raise ValueError(f"missing remediation config keys: {', '.join(missing_remediation)}")
    if not isinstance(remediation["namespace_allowlist"], list) or not remediation["namespace_allowlist"]:
        raise ValueError("remediation.namespace_allowlist must be a non-empty list")
    if not isinstance(remediation["resource_kind_allowlist"], list) or not remediation["resource_kind_allowlist"]:
        raise ValueError("remediation.resource_kind_allowlist must be a non-empty list")
    if not set(remediation["namespace_allowlist"]).issubset(set(config["namespace_allowlist"])):
        raise ValueError("remediation.namespace_allowlist must stay within namespace_allowlist")
    if remediation["max_blast_radius"] not in {"low", "medium", "high"}:
        raise ValueError("remediation.max_blast_radius must be low, medium, or high")
    if int(remediation["execution_timeout_seconds"]) <= 0:
        raise ValueError("remediation.execution_timeout_seconds must be positive")
    if int(remediation["approval_ttl_minutes"]) <= 0:
        raise ValueError("remediation.approval_ttl_minutes must be positive")
    if not isinstance(remediation["command_allowlist"], list) or not remediation["command_allowlist"]:
        raise ValueError("remediation.command_allowlist must be a non-empty list")
    if remediation["resource_kind_allowlist"] != ["Deployment"]:
        raise ValueError("remediation.resource_kind_allowlist must remain limited to Deployment in this phase")
    if config["feature_flags"].get("enable_execution") and remediation["simulation_only"]:
        raise ValueError("enable_execution cannot be true while remediation.simulation_only is true")
    escalation = remediation["escalation_minutes"]
    for key in ("t1", "t5", "t10", "t15"):
        if key not in escalation:
            raise ValueError(f"remediation.escalation_minutes missing key: {key}")

    k8sgpt_config = config["k8sgpt"]
    missing_k8sgpt = sorted(REQUIRED_K8SGPT_KEYS - set(k8sgpt_config))
    if missing_k8sgpt:
        raise ValueError(f"missing k8sgpt config keys: {', '.join(missing_k8sgpt)}")
    if not isinstance(k8sgpt_config["namespace_allowlist"], list) or not k8sgpt_config["namespace_allowlist"]:
        raise ValueError("k8sgpt.namespace_allowlist must be a non-empty list")
    if not set(k8sgpt_config["namespace_allowlist"]).issubset(set(config["namespace_allowlist"])):
        raise ValueError("k8sgpt.namespace_allowlist must stay within namespace_allowlist")
    if not isinstance(k8sgpt_config["filters"], list) or not k8sgpt_config["filters"]:
        raise ValueError("k8sgpt.filters must be a non-empty list")
    if int(k8sgpt_config["timeout_seconds"]) <= 0:
        raise ValueError("k8sgpt.timeout_seconds must be positive")
    if int(k8sgpt_config["max_output_kb"]) <= 0:
        raise ValueError("k8sgpt.max_output_kb must be positive")
    if not str(k8sgpt_config["explicit_kubeconfig"]).strip():
        raise ValueError("k8sgpt.explicit_kubeconfig is required")

    artifact_limits = config["incident_artifacts"]
    missing_artifact_limits = sorted(REQUIRED_INCIDENT_ARTIFACT_KEYS - set(artifact_limits))
    if missing_artifact_limits:
        raise ValueError(f"missing incident artifact config keys: {', '.join(missing_artifact_limits)}")
    for key in REQUIRED_INCIDENT_ARTIFACT_KEYS:
        if int(artifact_limits[key]) <= 0:
            raise ValueError(f"incident_artifacts.{key} must be positive")

    alerting = config["alerting"]
    missing_alerting = sorted(REQUIRED_ALERTING_KEYS - set(alerting))
    if missing_alerting:
        raise ValueError(f"missing alerting config keys: {', '.join(missing_alerting)}")
    if int(alerting["provider_timeout_seconds"]) <= 0:
        raise ValueError("alerting.provider_timeout_seconds must be positive")
    if int(alerting["provider_max_retries"]) < 0:
        raise ValueError("alerting.provider_max_retries must be zero or positive")
    if int(alerting["max_notification_log_bytes"]) <= 0:
        raise ValueError("alerting.max_notification_log_bytes must be positive")
    if not str(alerting["env_file"]).strip():
        raise ValueError("alerting.env_file is required")

    auto_remediation = config["auto_remediation"]
    missing_auto = sorted(REQUIRED_AUTO_REMEDIATION_KEYS - set(auto_remediation))
    if missing_auto:
        raise ValueError(f"missing auto_remediation config keys: {', '.join(missing_auto)}")
    if not isinstance(auto_remediation["allowed_actions"], list) or not auto_remediation["allowed_actions"]:
        raise ValueError("auto_remediation.allowed_actions must be a non-empty list")
    if set(auto_remediation["allowed_actions"]) != {"restart_banking_backend"}:
        raise ValueError("auto_remediation.allowed_actions must only contain restart_banking_backend")
    if auto_remediation["allowed_namespace"] != "bankapp":
        raise ValueError("auto_remediation.allowed_namespace must remain bankapp in this phase")
    if auto_remediation["allowed_deployment"] != "banking-backend":
        raise ValueError("auto_remediation.allowed_deployment must remain banking-backend in this phase")
    if int(auto_remediation["timeout_minutes"]) <= 0:
        raise ValueError("auto_remediation.timeout_minutes must be positive")
    if not isinstance(auto_remediation["require_snapshot"], bool):
        raise ValueError("auto_remediation.require_snapshot must be a boolean")
    if not isinstance(auto_remediation["verify_rollout"], bool):
        raise ValueError("auto_remediation.verify_rollout must be a boolean")
