from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from app.models.recommendation import Recommendation


VALID_STATUSES = {"proposed", "acknowledged", "suppressed", "approved", "rejected", "executed", "verified", "rolled_back", "expired"}


class JsonRecommendationStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def save_recommendation(self, recommendation: Recommendation) -> Recommendation:
        self._append(recommendation)
        return recommendation

    def list_recommendations(self) -> list[Recommendation]:
        records: dict[str, Recommendation] = {}
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                recommendation = Recommendation.from_dict(json.loads(line))
                records[recommendation.recommendation_id] = recommendation
        return sorted(records.values(), key=lambda item: item.created_at, reverse=True)

    def get_recommendation(self, recommendation_id: str) -> Recommendation | None:
        for recommendation in self.list_recommendations():
            if recommendation.recommendation_id == recommendation_id:
                return recommendation
        return None

    def update_status(self, recommendation_id: str, status: str, *, updated_at: str, reason: str | None = None) -> Recommendation:
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid recommendation status: {status}")
        recommendation = self.get_recommendation(recommendation_id)
        if recommendation is None:
            raise KeyError(recommendation_id)
        recommendation.status = status
        recommendation.updated_at = updated_at
        recommendation.status_reason = reason
        self._append(recommendation)
        return recommendation

    def find_by_signature(self, signature: str) -> list[Recommendation]:
        return [item for item in self.list_recommendations() if item.labels.get("signature") == signature]

    def _append(self, recommendation: Recommendation) -> None:
        payload = json.dumps(recommendation.to_dict(), sort_keys=True)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(payload + "\n")
