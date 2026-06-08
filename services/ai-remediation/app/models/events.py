from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SUPPORTED_SCENARIOS = {
    "pod_crashloop",
    "high_memory",
    "deployment_unhealthy",
    "target_down",
    "log_anomaly",
    "repeated_restart",
}


@dataclass
class ResourceRef:
    kind: str
    name: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResourceRef":
        return cls(kind=str(payload["kind"]), name=str(payload["name"]))

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class EvidenceItem:
    type: str
    name: str
    value: Any
    labels: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceItem":
        return cls(
            type=str(payload["type"]),
            name=str(payload["name"]),
            value=payload.get("value"),
            labels={str(k): str(v) for k, v in payload.get("labels", {}).items()},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IncidentEvent:
    event_id: str
    source: str
    scenario: str
    cluster: str
    namespace: str
    resource: ResourceRef
    observed_at: str
    severity_hint: str
    summary: str
    evidence: list[EvidenceItem]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "IncidentEvent":
        scenario = str(payload["scenario"])
        if scenario not in SUPPORTED_SCENARIOS:
            raise ValueError(f"unsupported scenario: {scenario}")
        return cls(
            event_id=str(payload["event_id"]),
            source=str(payload["source"]),
            scenario=scenario,
            cluster=str(payload["cluster"]),
            namespace=str(payload["namespace"]),
            resource=ResourceRef.from_dict(payload["resource"]),
            observed_at=str(payload["observed_at"]),
            severity_hint=str(payload.get("severity_hint", "low")),
            summary=str(payload["summary"]),
            evidence=[EvidenceItem.from_dict(item) for item in payload.get("evidence", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "source": self.source,
            "scenario": self.scenario,
            "cluster": self.cluster,
            "namespace": self.namespace,
            "resource": self.resource.to_dict(),
            "observed_at": self.observed_at,
            "severity_hint": self.severity_hint,
            "summary": self.summary,
            "evidence": [item.to_dict() for item in self.evidence],
        }
