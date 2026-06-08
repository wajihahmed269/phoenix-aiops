from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.models.events import EvidenceItem, IncidentEvent, ResourceRef


def create_incident_event(
    *,
    source: str,
    scenario: str,
    cluster: str,
    namespace: str,
    resource_kind: str,
    resource_name: str,
    severity_hint: str,
    summary: str,
    evidence: list[dict],
    max_evidence_items: int,
    observed_at: str | None = None,
) -> IncidentEvent:
    trimmed_evidence = evidence[:max_evidence_items]
    normalized_evidence = [
        EvidenceItem(
            type=str(item["type"]),
            name=str(item["name"]),
            value=item.get("value"),
            labels={str(k): str(v) for k, v in item.get("labels", {}).items()},
        )
        for item in trimmed_evidence
    ]

    return IncidentEvent(
        event_id=f"evt-{uuid4()}",
        source=source,
        scenario=scenario,
        cluster=cluster,
        namespace=namespace,
        resource=ResourceRef(kind=resource_kind, name=resource_name),
        observed_at=observed_at or utc_now(),
        severity_hint=severity_hint,
        summary=summary,
        evidence=normalized_evidence,
    )


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
