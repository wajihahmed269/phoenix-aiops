from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.collectors.k8sgpt import attach_advisory_evidence, collect_namespace_advisories
from app.collectors.argo import collect_argo_events
from app.collectors.kubernetes import collect_kubernetes_events
from app.collectors.loki import collect_log_anomaly_events
from app.collectors.prometheus import collect_target_down_events
from app.escalation.workflow import build_escalation_state
from app.models.events import IncidentEvent
from app.models.factory import utc_now
from app.models.identity import build_incident_id_for_event
from app.notifications.formatters import build_email_payload, build_markdown_summary
from app.notifications.service import send_incident_notification
from app.pipeline.correlation import correlate_incidents
from app.pipeline.dedupe import evaluate_recommendation
from app.pipeline.summary import build_incident_summary
from app.policies.loader import load_policy
from app.recommendations.engine import analyze_incident
from app.remediation.auto_restart import evaluate_auto_restart_candidate
from app.remediation.planner import generate_plan
from app.remediation.runner import execute_plan
from app.store.execution_audit import ExecutionAuditStore
from app.store.incident_artifacts import IncidentArtifactStore
from app.store.json_store import JsonRecommendationStore
from app.store.lifecycle import set_recommendation_status


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
    audit_store = ExecutionAuditStore(config["execution_audit_path"])
    artifact_limits = dict(config["incident_artifacts"])
    artifact_limits["max_notification_log_bytes"] = int(config["alerting"]["max_notification_log_bytes"])
    artifacts = IncidentArtifactStore(config["incident_artifacts_path"], artifact_limits)
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
        timeline_entries: list[str] = []
        _safe_artifact_call(result, lambda: artifacts.append_timeline(incident_id, timestamp=incident.observed_at, stage="detection", message="incident detected"), incident_id, "append detection timeline")
        timeline_entries.append("incident detected")

        incident, advisory = attach_advisory_evidence(incident, advisory_by_namespace.get(incident.namespace), max_evidence_items=config["max_evidence_items"])
        advisory_message = "k8sgpt advisory completed" if advisory and advisory.get("status") == "ok" else "k8sgpt advisory unavailable"
        _safe_artifact_call(result, lambda: artifacts.append_timeline(incident_id, timestamp=utc_now(), stage="advisor", message=advisory_message), incident_id, "append advisory timeline")
        timeline_entries.append(advisory_message)

        _safe_artifact_call(result, lambda: artifacts.persist_evidence(incident_id, incident, advisory), incident_id, "persist evidence")
        evidence_message = f"stored bounded evidence for {incident.resource.kind}/{incident.resource.name}"
        _safe_artifact_call(result, lambda: artifacts.append_timeline(incident_id, timestamp=utc_now(), stage="evidence", message=evidence_message), incident_id, "append evidence timeline")
        timeline_entries.append(evidence_message)

        recommendation = analyze_incident(incident, policy=policy)
        recommendation.incident_id = incident_id
        recommendation.labels["incident_id"] = incident_id
        escalation_state = build_escalation_state(recommendation, config)
        timeline_entries.append("recommendation generated")
        _safe_artifact_call(result, lambda: artifacts.append_timeline(incident_id, timestamp=recommendation.created_at, stage="recommendation", message="recommendation generated"), incident_id, "append recommendation generated timeline")

        summary = build_markdown_summary(
            recommendation,
            advisory=advisory,
            timeline_entries=timeline_entries + [build_incident_summary(incident, recommendation, advisory)],
            escalation_state=escalation_state,
            simulation_only=bool(config["remediation"]["simulation_only"]),
        )
        _safe_artifact_call(result, lambda: artifacts.persist_summary(incident_id, summary), incident_id, "persist summary")
        _safe_artifact_call(result, lambda: artifacts.persist_recommendation(incident_id, recommendation), incident_id, "persist recommendation")

        decision = evaluate_recommendation(store, recommendation, config, policy)
        if not decision.allow:
            result.suppressed_recommendations += 1
            _safe_artifact_call(
                result,
                lambda: artifacts.append_timeline(incident_id, timestamp=recommendation.created_at, stage="suppression", message=f"recommendation suppressed: {decision.reason or 'dedupe policy'}"),
                incident_id,
                "append suppression timeline",
            )
            result.suppressed.append({"incident_id": incident_id, "event_id": incident.event_id, "summary": recommendation.summary, "reason": decision.reason, "signature": decision.signature})
            _maybe_auto_restart(result, config, store, audit_store, artifacts, recommendation, advisory, timeline_entries, stored_recommendation_id=None)
            result.artifacts.append({"incident_id": incident_id, "path": artifacts.artifact_dir(incident_id), "status": "suppressed"})
            continue

        store.save_recommendation(recommendation)
        result.stored_recommendations += 1
        stored_message = f"stored recommendation {recommendation.recommendation_id}"
        _safe_artifact_call(result, lambda: artifacts.append_timeline(incident_id, timestamp=recommendation.created_at, stage="recommendation", message=stored_message), incident_id, "append recommendation timeline")
        timeline_entries.append(stored_message)

        _send_notification(result, config, artifacts, recommendation, advisory, timeline_entries, escalation_state, simulation_only=bool(config["remediation"]["simulation_only"]), notification_suffix=None)
        _maybe_auto_restart(result, config, store, audit_store, artifacts, recommendation, advisory, timeline_entries, stored_recommendation_id=recommendation.recommendation_id)

        result.recommendations.append(recommendation.to_dict())
        result.artifacts.append({"incident_id": incident_id, "path": artifacts.artifact_dir(incident_id), "status": "stored"})

    return result


def _maybe_auto_restart(
    result: PollResult,
    config: dict,
    store: JsonRecommendationStore,
    audit_store: ExecutionAuditStore,
    artifacts: IncidentArtifactStore,
    recommendation,
    advisory: dict | None,
    timeline_entries: list[str],
    *,
    stored_recommendation_id: str | None,
) -> None:
    decision = evaluate_auto_restart_candidate(recommendation, config, store, audit_store)
    if not decision.allow:
        return
    try:
        plan = generate_plan(recommendation, config)
        execution = execute_plan(plan, recommendation, config, approval=None, explicit_execute=decision.live_execution, auto_execute=True)
    except Exception as exc:  # noqa: BLE001
        result.errors.append(f"auto_restart[{recommendation.incident_id}] execution: {exc}")
        return

    target_recommendation_id = stored_recommendation_id or decision.persisted_recommendation_id
    if target_recommendation_id:
        try:
            set_recommendation_status(store, target_recommendation_id, "executed", config=config, reason=execution.mode)
            if execution.verification.get("success"):
                set_recommendation_status(store, target_recommendation_id, "verified", config=config, reason=execution.mode)
        except KeyError:
            result.errors.append(f"auto_restart[{recommendation.incident_id}] recommendation status update failed")

    final_state = dict(build_escalation_state(recommendation, config))
    final_state["approval_state"] = "bounded_auto_restart_policy"
    final_state["execution_state"] = execution.mode
    final_timeline = list(timeline_entries) + ["snapshot captured", f"auto-remediation {execution.mode} completed", f"verification success={str(execution.verification.get('success')).lower()}"]
    notification_suffix = f"Auto-remediation result: {execution.message}"
    _send_notification(result, config, artifacts, recommendation, advisory, final_timeline, final_state, simulation_only=execution.mode == "simulation", notification_suffix=notification_suffix)


def _send_notification(
    result: PollResult,
    config: dict,
    artifacts: IncidentArtifactStore,
    recommendation,
    advisory: dict | None,
    timeline_entries: list[str],
    escalation_state: dict,
    *,
    simulation_only: bool,
    notification_suffix: str | None,
) -> None:
    payload = build_email_payload(
        recommendation,
        advisory=advisory,
        timeline_entries=timeline_entries,
        escalation_state=escalation_state,
        simulation_only=simulation_only,
    )
    if notification_suffix:
        payload["body"] = payload["body"] + "\n" + notification_suffix
    try:
        notification_result = send_incident_notification(config, payload)
    except ValueError as exc:
        result.errors.append(f"notification[{recommendation.incident_id}] configuration: {exc}")
        return
    except Exception as exc:  # noqa: BLE001
        result.errors.append(f"notification[{recommendation.incident_id}] send: {exc}")
        return

    message = "notification email sent" if notification_result.success else "notification email failed"
    _safe_artifact_call(result, lambda: artifacts.append_timeline(recommendation.incident_id, timestamp=utc_now(), stage="notification", message=message), recommendation.incident_id, "append notification timeline")
    _safe_artifact_call(result, lambda: artifacts.append_notification_log(recommendation.incident_id, timestamp=utc_now(), result=notification_result.to_dict()), recommendation.incident_id, "append notification log")


def _safe_artifact_call(result: PollResult, fn, incident_id: str, action: str) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        result.errors.append(f"incident_artifacts[{incident_id}] {action}: {exc}")
