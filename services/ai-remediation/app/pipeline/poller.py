from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.collectors.argo import collect_argo_events
from app.collectors.kubernetes import collect_kubernetes_events
from app.collectors.loki import collect_log_anomaly_events
from app.collectors.prometheus import collect_target_down_events
from app.models.events import IncidentEvent
from app.pipeline.dedupe import evaluate_recommendation
from app.policies.loader import load_policy
from app.recommendations.engine import analyze_incident
from app.store.json_store import JsonRecommendationStore


@dataclass
class PollResult:
    collected_events: int = 0
    stored_recommendations: int = 0
    suppressed_recommendations: int = 0
    errors: list[str] = field(default_factory=list)
    recommendations: list[dict] = field(default_factory=list)
    suppressed: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def run_once(config: dict) -> PollResult:
    policy = load_policy()
    store = JsonRecommendationStore(config["local_storage_path"])
    result = PollResult()
    incidents: list[IncidentEvent] = []

    collectors = [
        ("enable_prometheus_collector", collect_target_down_events),
        ("enable_loki_collector", collect_log_anomaly_events),
        ("enable_kubernetes_collector", collect_kubernetes_events),
        ("enable_argo_collector", collect_argo_events),
    ]
    for flag, collector in collectors:
        if not config["feature_flags"].get(flag, False):
            continue
        try:
            incidents.extend(collector(config))
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"{collector.__name__}: {exc}")

    result.collected_events = len(incidents)

    for incident in incidents:
        recommendation = analyze_incident(incident, policy=policy)
        decision = evaluate_recommendation(store, recommendation, config, policy)
        if not decision.allow:
            result.suppressed_recommendations += 1
            result.suppressed.append(
                {
                    "event_id": incident.event_id,
                    "summary": recommendation.summary,
                    "reason": decision.reason,
                    "signature": decision.signature,
                }
            )
            continue
        store.save_recommendation(recommendation)
        result.stored_recommendations += 1
        result.recommendations.append(recommendation.to_dict())

    return result
