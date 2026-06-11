from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from app.config.runtime import AutoRemediationSettings, load_auto_remediation_settings
from app.models.recommendation import Recommendation
from app.store.execution_audit import ExecutionAuditStore
from app.store.json_store import JsonRecommendationStore


@dataclass
class AutoRestartDecision:
    allow: bool
    reason: str
    live_execution: bool
    persisted_recommendation_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_auto_restart_candidate(
    recommendation: Recommendation,
    config: dict,
    recommendation_store: JsonRecommendationStore,
    audit_store: ExecutionAuditStore,
    *,
    now: str | None = None,
) -> AutoRestartDecision:
    settings = load_auto_remediation_settings(config)
    target_check = _validate_target(recommendation, settings)
    if target_check is not None:
        return target_check

    if not settings.config_enabled:
        return AutoRestartDecision(False, "auto_remediation_disabled", False)
    if not settings.env_enabled:
        return AutoRestartDecision(False, "AUTO_RESTART_BANKING_BACKEND is not enabled", False)
    if not settings.require_snapshot:
        return AutoRestartDecision(False, "snapshot_required", False)
    if not settings.verify_rollout:
        return AutoRestartDecision(False, "rollout_verification_required", False)
    if "restart_banking_backend" not in settings.allowed_actions:
        return AutoRestartDecision(False, "restart_banking_backend not present in allowed_actions", False)

    signature = recommendation.labels.get("signature", "")
    if not signature:
        return AutoRestartDecision(False, "recommendation signature missing", False)

    previous = [item for item in recommendation_store.find_by_signature(signature) if item.recommendation_id != recommendation.recommendation_id]
    if not previous:
        return AutoRestartDecision(False, "timeout window not satisfied yet", False)

    oldest = min(previous, key=lambda item: item.created_at)
    current = _parse_time(now or recommendation.created_at)
    age_minutes = int((current - _parse_time(oldest.created_at)).total_seconds() / 60)
    if age_minutes < settings.timeout_minutes:
        return AutoRestartDecision(False, f"timeout window not satisfied yet ({age_minutes}m/{settings.timeout_minutes}m)", False)

    latest_audit = audit_store.latest_for_target("restart_banking_backend", recommendation.namespace, recommendation.resource.get("kind", ""), recommendation.resource.get("name", ""))
    if latest_audit and latest_audit.get("status") in {"simulated", "succeeded"}:
        return AutoRestartDecision(False, "auto-remediation already attempted for this target", False)

    live_execution = bool(config["feature_flags"].get("enable_execution", False) and not config["remediation"]["simulation_only"])
    return AutoRestartDecision(True, "eligible", live_execution, persisted_recommendation_id=oldest.recommendation_id)


def _validate_target(recommendation: Recommendation, settings: AutoRemediationSettings) -> AutoRestartDecision | None:
    if recommendation.resource.get("kind") != "Deployment":
        return AutoRestartDecision(False, "only Deployment resources are eligible", False)
    if recommendation.namespace != settings.allowed_namespace:
        return AutoRestartDecision(False, "only bankapp namespace is eligible", False)
    if recommendation.resource.get("name") != settings.allowed_deployment:
        return AutoRestartDecision(False, "only deployment/banking-backend is eligible", False)
    if recommendation.labels.get("scenario") not in {"deployment_unhealthy", "repeated_restart"}:
        return AutoRestartDecision(False, "scenario is not eligible for auto restart", False)
    return None


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
