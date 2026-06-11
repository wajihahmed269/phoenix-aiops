from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


REQUIRED_ENV_KEYS = {
    "ALERT_PROVIDER",
    "ALERT_DRY_RUN",
    "ALERT_FROM_EMAIL",
    "ALERT_TO_EMAIL",
}


@dataclass(frozen=True)
class AlertingSettings:
    provider: str
    dry_run: bool
    from_email: str
    to_email: str
    api_key: str | None
    timeout_seconds: int
    max_retries: int
    max_notification_log_bytes: int


@dataclass(frozen=True)
class AutoRemediationSettings:
    config_enabled: bool
    env_enabled: bool
    allowed_actions: list[str]
    allowed_namespace: str
    allowed_deployment: str
    timeout_minutes: int
    require_snapshot: bool
    verify_rollout: bool

    @property
    def enabled(self) -> bool:
        return self.config_enabled and self.env_enabled


def load_runtime_environment(config: dict) -> dict[str, str]:
    env_values = _load_env_file(config["alerting"]["env_file"])
    return {**env_values, **os.environ}


def load_alerting_settings(config: dict) -> AlertingSettings:
    merged = load_runtime_environment(config)
    missing = sorted(key for key in REQUIRED_ENV_KEYS if not str(merged.get(key, "")).strip())
    if missing:
        raise ValueError(f"missing alerting environment variables: {', '.join(missing)}")

    provider = str(merged["ALERT_PROVIDER"]).strip().lower()
    if provider not in {"brevo"}:
        raise ValueError("ALERT_PROVIDER must be brevo")

    dry_run = parse_bool(merged["ALERT_DRY_RUN"], key="ALERT_DRY_RUN")
    api_key = str(merged.get("BREVO_API_KEY", "")).strip() or None
    if not dry_run and not api_key:
        raise ValueError("BREVO_API_KEY is required when ALERT_DRY_RUN is false")

    return AlertingSettings(
        provider=provider,
        dry_run=dry_run,
        from_email=str(merged["ALERT_FROM_EMAIL"]).strip(),
        to_email=str(merged["ALERT_TO_EMAIL"]).strip(),
        api_key=api_key,
        timeout_seconds=int(config["alerting"]["provider_timeout_seconds"]),
        max_retries=int(config["alerting"]["provider_max_retries"]),
        max_notification_log_bytes=int(config["alerting"]["max_notification_log_bytes"]),
    )


def load_auto_remediation_settings(config: dict) -> AutoRemediationSettings:
    merged = load_runtime_environment(config)
    return AutoRemediationSettings(
        config_enabled=bool(config["auto_remediation"]["enabled"]),
        env_enabled=parse_bool(str(merged.get("AUTO_RESTART_BANKING_BACKEND", "false")), key="AUTO_RESTART_BANKING_BACKEND"),
        allowed_actions=list(config["auto_remediation"]["allowed_actions"]),
        allowed_namespace=str(config["auto_remediation"]["allowed_namespace"]),
        allowed_deployment=str(config["auto_remediation"]["allowed_deployment"]),
        timeout_minutes=int(config["auto_remediation"]["timeout_minutes"]),
        require_snapshot=bool(config["auto_remediation"]["require_snapshot"]),
        verify_rollout=bool(config["auto_remediation"]["verify_rollout"]),
    )


def _load_env_file(env_file: str) -> dict[str, str]:
    path = Path(env_file).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.is_file():
        raise ValueError(f"alerting env file is missing: {path}")

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def parse_bool(value: str, *, key: str) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    raise ValueError(f"{key} must be true or false")
