from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.models.events import IncidentEvent
from app.models.identity import build_incident_id_for_event
from app.models.recommendation import ActionProposal, Recommendation


def build_recommendation(event: IncidentEvent, policy: dict) -> Recommendation:
    action_map = {
        "pod_crashloop": [
            ActionProposal("collect_evidence", "Capture describe output, events, and last logs.", None),
            ActionProposal("propose_rollout_restart", "Review the owning workload and consider a manual rollout restart after root-cause review.", "kubectl rollout restart <workload>"),
        ],
        "high_memory": [
            ActionProposal("query_metrics", "Inspect recent memory growth and node pressure before any scaling decision.", None),
            ActionProposal("propose_config_review", "Review memory requests, limits, and possible leak indicators.", None),
        ],
        "deployment_unhealthy": [
            ActionProposal("collect_evidence", "Check rollout status, unavailable replicas, and recent events.", None),
            ActionProposal("open_runbook", "Use the deployment recovery runbook before considering a restart.", None),
        ],
        "target_down": [
            ActionProposal("query_metrics", "Validate target labels, scrape URL, and last error against recent config changes.", None),
            ActionProposal("propose_config_review", "If this is a known limitation, suppress it in configuration rather than weakening security.", None),
        ],
        "log_anomaly": [
            ActionProposal("query_logs", "Collect a bounded sample of repeated errors for operator review.", None),
            ActionProposal("summarize_incident", "Create a concise incident summary with suspected cause and affected resource.", None),
        ],
        "repeated_restart": [
            ActionProposal("collect_evidence", "Compare restart frequency with rollout history and pod events.", None),
            ActionProposal("propose_config_review", "Inspect probes, dependencies, and startup sequencing.", None),
        ],
    }

    rationale_map = {
        "pod_crashloop": "Crashloops are usually caused by startup, config, dependency, or image issues. The safe first step is evidence collection, not restart automation.",
        "high_memory": "Memory pressure needs context from recent usage and limits before any scaling or restart suggestion.",
        "deployment_unhealthy": "Unhealthy deployments often reflect rollout, probe, or config regressions and should be reviewed against GitOps state first.",
        "target_down": "A down target can be a real outage or an accepted scrape limitation. Recommendation should distinguish those cases before any action is proposed.",
        "log_anomaly": "Log spikes need bounded summarization so operators can review the actual symptom without reading raw log streams end to end.",
        "repeated_restart": "Repeated restarts need correlation with rollouts and events to avoid treating normal changes as incidents.",
    }

    known_limitation = _known_limitation_decision(event, policy)
    labels = {"scenario": event.scenario}
    if known_limitation:
        labels["known_limitation"] = "true"

    severity = _normalize_severity(event.severity_hint, known_limitation)
    risk_score = {"info": 10, "low": 25, "medium": 45, "high": 65, "critical": 85}[severity]
    requires_human_approval = any(action.action_type.startswith("propose_") for action in action_map[event.scenario])

    return Recommendation(
        recommendation_id=f"rec-{uuid4()}",
        incident_id=build_incident_id_for_event(event),
        event_id=event.event_id,
        source=event.source,
        cluster=event.cluster,
        namespace=event.namespace,
        resource={"kind": event.resource.kind, "name": event.resource.name},
        severity=severity,
        summary=event.summary,
        rationale=rationale_map[event.scenario],
        evidence=[
            {
                "type": item.type,
                "name": item.name,
                "value": item.value,
                "labels": item.labels,
            }
            for item in event.evidence
        ],
        confidence=0.7 if not known_limitation else 0.9,
        risk_score=risk_score,
        suggested_actions=action_map[event.scenario],
        requires_human_approval=requires_human_approval,
        rollback_hint="No action is executed in this phase. Any future mutation must support rollback or bounded verification.",
        policy_decision={
            "policy_version": policy["version"],
            "mutating_actions_require_human_approval": policy["approval"]["mutating_actions_require_human_approval"],
            "known_limitation": known_limitation,
        },
        analyzer="deterministic-rules-v1",
        created_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        labels=labels,
    )


def _normalize_severity(severity_hint: str, known_limitation: bool) -> str:
    if known_limitation:
        return "info"
    if severity_hint in {"info", "low", "medium", "high", "critical"}:
        return severity_hint
    return "low"


def _known_limitation_decision(event: IncidentEvent, policy: dict) -> bool:
    if event.scenario != "target_down":
        return False
    for evidence in event.evidence:
        job = evidence.labels.get("job", "")
        last_error = evidence.labels.get("lastError", "")
        for rule in policy.get("known_limitations", []):
            match = rule.get("match", {})
            if match.get("job") == job and match.get("lastError_contains", "") in last_error:
                return True
    return False
