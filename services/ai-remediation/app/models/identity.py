from __future__ import annotations

from hashlib import sha256

from app.models.events import IncidentEvent


def build_incident_id(
    *,
    cluster: str,
    namespace: str,
    resource_kind: str,
    resource_name: str,
    scenario: str,
) -> str:
    raw = "|".join([cluster, namespace, resource_kind, resource_name, scenario]).encode("utf-8")
    return f"inc-{sha256(raw).hexdigest()[:12]}"


def build_incident_id_for_event(event: IncidentEvent) -> str:
    return build_incident_id(
        cluster=event.cluster,
        namespace=event.namespace,
        resource_kind=event.resource.kind,
        resource_name=event.resource.name,
        scenario=event.scenario,
    )
