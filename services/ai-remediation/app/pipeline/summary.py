from __future__ import annotations

from app.models.events import IncidentEvent
from app.models.recommendation import Recommendation


IMPACT_BY_SCENARIO = {
    "pod_crashloop": "Likely impact is reduced pod availability and repeated failed restarts.",
    "deployment_unhealthy": "Likely impact is reduced deployment availability or stalled rollout progress.",
    "repeated_restart": "Likely impact is intermittent instability and elevated error rates.",
    "target_down": "Likely impact is degraded observability coverage or an unreachable scrape endpoint.",
    "high_memory": "Likely impact is resource pressure and possible workload eviction risk.",
    "log_anomaly": "Likely impact is application instability requiring bounded log review.",
}


def build_incident_summary(incident: IncidentEvent, recommendation: Recommendation, advisory: dict | None) -> str:
    evidence_text = _summarize_evidence(incident)
    impact = IMPACT_BY_SCENARIO.get(incident.scenario, "Likely impact is degraded workload health.")
    k8sgpt_text = _summarize_advisory(advisory)
    return " ".join(
        part
        for part in [
            f"{incident.resource.kind} {incident.resource.name} in namespace {incident.namespace} is experiencing {incident.scenario.replace('_', ' ')}.",
            impact,
            evidence_text,
            k8sgpt_text,
            f"Recommendation rationale: {recommendation.rationale}",
        ]
        if part
    )


def _summarize_evidence(incident: IncidentEvent) -> str:
    snippets: list[str] = []
    for item in incident.evidence[:3]:
        if item.type == "metric":
            snippets.append(f"{item.name}={item.value}")
        elif item.type in {"event", "log"}:
            snippets.append(f"{item.name}: {item.value}")
        elif item.type == "state":
            snippets.append(f"{item.name} observed")
    if not snippets:
        return ""
    return f"Observed evidence includes {'; '.join(snippets)}."


def _summarize_advisory(advisory: dict | None) -> str:
    if not advisory:
        return ""
    if advisory.get("status") != "ok":
        reason = advisory.get("error") or advisory.get("status", "unavailable")
        return f"K8sGPT advisory evidence was unavailable ({reason})."
    findings = advisory.get("matched_findings", [])[:1]
    if not findings:
        return "K8sGPT did not return a matching advisory finding for this resource."
    finding = findings[0]
    return f"K8sGPT reported {finding['message']}."
