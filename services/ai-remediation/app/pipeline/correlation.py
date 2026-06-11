from __future__ import annotations

import json
from collections import defaultdict

from app.models.events import EvidenceItem, IncidentEvent


SEVERITY_ORDER = {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "low": 2,
    "info": 1,
}


def correlate_incidents(incidents: list[IncidentEvent], *, max_evidence_items: int) -> list[IncidentEvent]:
    grouped: dict[tuple[str, str, str, str], list[IncidentEvent]] = defaultdict(list)
    for incident in incidents:
        grouped[(incident.cluster, incident.namespace, incident.resource.kind, incident.resource.name)].append(incident)

    correlated: list[IncidentEvent] = []
    for group in grouped.values():
        if len(group) == 1:
            incident = group[0]
            incident.evidence = incident.evidence[:max_evidence_items]
            correlated.append(incident)
            continue

        primary = max(group, key=_rank_incident)
        sources = sorted({item.source for item in group})
        evidence = _merge_evidence(group, max_evidence_items=max_evidence_items)
        summary = primary.summary
        if len(sources) > 1:
            summary = f"{primary.summary} Correlated evidence sources: {', '.join(sources)}."

        correlated.append(
            IncidentEvent(
                event_id=primary.event_id,
                source="correlated",
                scenario=primary.scenario,
                cluster=primary.cluster,
                namespace=primary.namespace,
                resource=primary.resource,
                observed_at=max(item.observed_at for item in group),
                severity_hint=primary.severity_hint,
                summary=summary,
                evidence=evidence,
            )
        )

    return sorted(correlated, key=lambda item: (item.namespace, item.resource.kind, item.resource.name, item.scenario))


def _merge_evidence(incidents: list[IncidentEvent], *, max_evidence_items: int) -> list[EvidenceItem]:
    merged: list[EvidenceItem] = []
    seen: set[str] = set()
    for incident in sorted(incidents, key=_rank_incident, reverse=True):
        for item in incident.evidence:
            signature = json.dumps(
                {
                    "type": item.type,
                    "name": item.name,
                    "value": item.value,
                    "labels": item.labels,
                },
                sort_keys=True,
                default=str,
            )
            if signature in seen:
                continue
            seen.add(signature)
            merged.append(item)
            if len(merged) >= max_evidence_items:
                return merged
    return merged


def _rank_incident(incident: IncidentEvent) -> tuple[int, str]:
    return (SEVERITY_ORDER.get(incident.severity_hint, 0), incident.observed_at)
