from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.models.recommendation import Recommendation
from app.store.json_store import JsonRecommendationStore


@dataclass
class DedupeDecision:
    allow: bool
    signature: str
    reason: str | None = None
    cooldown_applied: bool = False


def evaluate_recommendation(store: JsonRecommendationStore, recommendation: Recommendation, config: dict, policy: dict) -> DedupeDecision:
    signature = build_signature(recommendation)
    recommendation.labels["signature"] = signature
    recommendation.labels["deduped"] = "false"
    recommendation.labels["cooldown_applied"] = "false"
    recommendation.labels["known_limitation"] = str(recommendation.policy_decision.get("known_limitation", False)).lower()

    previous = [item for item in store.list_recommendations() if item.labels.get("signature") == signature or build_signature(item) == signature]
    if not previous:
        return DedupeDecision(allow=True, signature=signature)

    latest = max(previous, key=lambda item: item.created_at)
    created_at = _parse_time(latest.created_at)
    current = _parse_time(recommendation.created_at)
    cooldown_minutes = config["cooldowns"]["known_limitation_minutes"] if recommendation.policy_decision.get("known_limitation") else config["cooldowns"]["default_minutes"]
    policy_cooldown = policy.get("cooldowns", {}).get("known_limitation_minutes") if recommendation.policy_decision.get("known_limitation") else policy.get("cooldowns", {}).get("same_recommendation_minutes")
    effective_cooldown = max(int(cooldown_minutes), int(policy_cooldown or 0))

    if current - created_at < timedelta(minutes=effective_cooldown):
        recommendation.labels["deduped"] = "true"
        recommendation.labels["cooldown_applied"] = "true"
        return DedupeDecision(
            allow=False,
            signature=signature,
            reason=f"suppressed by cooldown; last seen {latest.created_at}",
            cooldown_applied=True,
        )
    return DedupeDecision(allow=True, signature=signature)


def build_signature(recommendation: Recommendation) -> str:
    return "|".join(
        [
            recommendation.labels.get("scenario", ""),
            recommendation.namespace,
            recommendation.resource.get("kind", ""),
            recommendation.resource.get("name", ""),
            recommendation.summary,
        ]
    )


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
