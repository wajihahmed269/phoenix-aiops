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
    "feature_flags",
}

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "default.json"
CONFIG_PATH_ENV = "AIOPS_CONFIG_PATH"


def load_config(config_path: str | None = None) -> dict[str, Any]:
    resolved = Path(config_path or os.environ.get(CONFIG_PATH_ENV) or DEFAULT_CONFIG_PATH)
    with resolved.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    _validate_config(config)
    return config


def _validate_config(config: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_TOP_LEVEL_KEYS - set(config))
    if missing:
        raise ValueError(f"missing config keys: {', '.join(missing)}")

    if config["kubernetes_mode"] != "kubectl":
        raise ValueError("only kubectl mode is supported in this phase")

    if not isinstance(config["namespace_allowlist"], list) or not config["namespace_allowlist"]:
        raise ValueError("namespace_allowlist must be a non-empty list")

    if config["feature_flags"].get("enable_execution"):
        raise ValueError("enable_execution must remain false in this phase")
