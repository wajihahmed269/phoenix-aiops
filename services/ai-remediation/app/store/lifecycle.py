from __future__ import annotations

from app.config.loader import load_config
from app.models.factory import utc_now
from app.models.recommendation import Recommendation
from app.store.incident_artifacts import IncidentArtifactStore
from app.store.json_store import JsonRecommendationStore


def acknowledge_recommendation(store: JsonRecommendationStore, recommendation_id: str, config: dict | None = None) -> Recommendation:
    return set_recommendation_status(store, recommendation_id, "acknowledged", config=config)


def suppress_recommendation(store: JsonRecommendationStore, recommendation_id: str, reason: str | None = None, config: dict | None = None) -> Recommendation:
    return set_recommendation_status(store, recommendation_id, "suppressed", config=config, reason=reason)


def set_recommendation_status(
    store: JsonRecommendationStore,
    recommendation_id: str,
    status: str,
    *,
    config: dict | None = None,
    reason: str | None = None,
) -> Recommendation:
    recommendation = store.update_status(recommendation_id, status, updated_at=utc_now(), reason=reason)
    _append_status_timeline(recommendation, status, config=config, reason=reason)
    return recommendation


def _append_status_timeline(
    recommendation: Recommendation,
    status: str,
    *,
    config: dict | None = None,
    reason: str | None = None,
) -> None:
    active_config = config or load_config()
    artifacts = IncidentArtifactStore(active_config["incident_artifacts_path"])
    suffix = f" ({reason})" if reason else ""
    try:
        artifacts.append_timeline(
            recommendation.incident_id,
            timestamp=recommendation.updated_at or utc_now(),
            stage="recommendation_state",
            message=f"Recommendation {recommendation.recommendation_id} marked {status}{suffix}.",
        )
    except OSError:
        return
