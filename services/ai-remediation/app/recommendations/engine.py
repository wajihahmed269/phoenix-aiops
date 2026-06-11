from __future__ import annotations

from app.analyzers.rules import build_recommendation
from app.models.events import IncidentEvent
from app.models.recommendation import Recommendation
from app.policies.loader import load_policy


def analyze_event(payload: dict, policy: dict | None = None) -> Recommendation:
    event = IncidentEvent.from_dict(payload)
    return analyze_incident(event, policy=policy)


def analyze_incident(event: IncidentEvent, policy: dict | None = None) -> Recommendation:
    active_policy = policy or load_policy()
    return build_recommendation(event, active_policy)
