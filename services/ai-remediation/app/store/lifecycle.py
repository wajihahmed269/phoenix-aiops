from __future__ import annotations

from app.models.factory import utc_now
from app.models.recommendation import Recommendation
from app.store.json_store import JsonRecommendationStore


def acknowledge_recommendation(store: JsonRecommendationStore, recommendation_id: str) -> Recommendation:
    return store.update_status(recommendation_id, "acknowledged", updated_at=utc_now())


def suppress_recommendation(store: JsonRecommendationStore, recommendation_id: str, reason: str | None = None) -> Recommendation:
    return store.update_status(recommendation_id, "suppressed", updated_at=utc_now(), reason=reason)
