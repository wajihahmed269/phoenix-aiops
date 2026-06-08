from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.collectors.k8sgpt import attach_advisory_evidence, collect_namespace_advisories
from app.collectors.argo import collect_argo_events
from app.collectors.kubernetes import collect_kubernetes_events
from app.collectors.loki import collect_log_anomaly_events
from app.collectors.prometheus import collect_target_down_events
from app.models.events import IncidentEvent
from app.models.identity import build_incident_id_for_event
from app.pipeline.correlation import correlate_incidents
from app.pipeline.dedupe import evaluate_recommendation
from app.pipeline.summary import build_incident_summary
from app.policies.loader import load_policy
from app.recommendations.engine import analyze_incident
from app.store.incident_artifacts import IncidentArtifactStore
from app.store.json_store import JsonRecommendationStore


@dataclass
class PollResult:
    collected_events: int = 0
    correlated_events: int = 0
    stored_recommendations: int = 0
    suppressed_recommendations: int = 0
    errors: list[str] = field(default_factory=list)
    recommendations: list[dict] = field(default_factory=list)
    suppressed: list[dict] = field(default_factory=list)
    artifacts: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def run_once(config: dict) -> PollResult:
    policy = load_policy()
    store = JsonRecommendationStore(config["local_storage_path"])
    artifacts = IncidentArtifactStore(config["incident_artifacts_path"])
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
    incidents = correlate_incidents(incidents, max_evidence_items=config["max_evidence_items"])
    result.correlated_events = len(incidents)
    advisory_by_namespace = collect_namespace_advisories(config, [incident.namespace for incident in incidents])

    for incident in incidents:
        incident_id = build_incident_id_for_event(incident)
        _safe_artifact_call(
            result,
            lambda: artifacts.append_timeline(
                incident_id,
                timestamp=incident.observed_at,
                stage="detection",
                message=f"Detected {incident.scenario} for {incident.namespace}/{incident.resource.name}.",
            ),
            incident_id,
            "append detection timeline",
        )
        incident, advisory = attach_advisory_evidence(
            incident,
            advisory_by_namespace.get(incident.namespace),
            max_evidence_items=config["max_evidence_items"],
        )
        _safe_artifact_call(result, lambda: artifacts.persist_evidence(incident_id, incident, advisory), incident_id, "persist evidence")
        _safe_artifact_call(
            result,
            lambda: artifacts.append_timeline(
                incident_id,
                timestamp=incident.observed_at,
                stage="evidence",
                message=f"Persisted correlated evidence with {len(incident.evidence)} bounded evidence items.",
            ),
            incident_id,
            "append evidence timeline",
        )

        recommendation = analyze_incident(incident, policy=policy)
        recommendation.incident_id = incident_id
        recommendation.labels["incident_id"] = incident_id
        summary = build_incident_summary(incident, recommendation, advisory)
        _safe_artifact_call(result, lambda: artifacts.persist_summary(incident_id, summary), incident_id, "persist summary")
        _safe_artifact_call(result, lambda: artifacts.persist_recommendation(incident_id, recommendation), incident_id, "persist recommendation")
        decision = evaluate_recommendation(store, recommendation, config, policy)
        if not decision.allow:
            result.suppressed_recommendations += 1
            _safe_artifact_call(
                result,
                lambda: artifacts.append_timeline(
                    incident_id,
                    timestamp=recommendation.created_at,
                    stage="suppression",
                    message=f"Suppressed recommendation {recommendation.recommendation_id}: {decision.reason or 'dedupe policy'}.",
                ),
                incident_id,
                "append suppression timeline",
            )
            result.suppressed.append(
                {
                    "incident_id": incident_id,
                    "event_id": incident.event_id,
                    "summary": recommendation.summary,
                    "reason": decision.reason,
                    "signature": decision.signature,
                }
            )
            result.artifacts.append({"incident_id": incident_id, "path": artifacts.artifact_dir(incident_id), "status": "suppressed"})
            continue
        store.save_recommendation(recommendation)
        result.stored_recommendations += 1
        _safe_artifact_call(
            result,
            lambda: artifacts.append_timeline(
                incident_id,
                timestamp=recommendation.created_at,
                stage="recommendation",
                message=f"Stored recommendation {recommendation.recommendation_id} with severity {recommendation.severity}.",
            ),
            incident_id,
            "append recommendation timeline",
        )
        result.recommendations.append(recommendation.to_dict())
        result.artifacts.append({"incident_id": incident_id, "path": artifacts.artifact_dir(incident_id), "status": "stored"})

    return result


def _safe_artifact_call(result: PollResult, fn, incident_id: str, action: str) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        result.errors.append(f"incident_artifacts[{incident_id}] {action}: {exc}")
