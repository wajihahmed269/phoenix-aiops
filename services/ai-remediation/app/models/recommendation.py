from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ActionProposal:
    action_type: str
    description: str
    command_hint: str | None


@dataclass
class Recommendation:
    recommendation_id: str
    event_id: str
    source: str
    cluster: str
    namespace: str
    resource: dict[str, str]
    severity: str
    summary: str
    rationale: str
    evidence: list[dict[str, Any]]
    confidence: float
    risk_score: int
    suggested_actions: list[ActionProposal]
    requires_human_approval: bool
    rollback_hint: str
    policy_decision: dict[str, Any]
    analyzer: str
    created_at: str
    status: str = "proposed"
    updated_at: str | None = None
    status_reason: str | None = None
    labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["suggested_actions"] = [asdict(action) for action in self.suggested_actions]
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Recommendation":
        return cls(
            recommendation_id=str(payload["recommendation_id"]),
            event_id=str(payload["event_id"]),
            source=str(payload["source"]),
            cluster=str(payload["cluster"]),
            namespace=str(payload["namespace"]),
            resource=dict(payload["resource"]),
            severity=str(payload["severity"]),
            summary=str(payload["summary"]),
            rationale=str(payload["rationale"]),
            evidence=list(payload.get("evidence", [])),
            confidence=float(payload["confidence"]),
            risk_score=int(payload["risk_score"]),
            suggested_actions=[ActionProposal(**action) for action in payload.get("suggested_actions", [])],
            requires_human_approval=bool(payload["requires_human_approval"]),
            rollback_hint=str(payload["rollback_hint"]),
            policy_decision=dict(payload.get("policy_decision", {})),
            analyzer=str(payload["analyzer"]),
            created_at=str(payload["created_at"]),
            status=str(payload.get("status", "proposed")),
            updated_at=payload.get("updated_at"),
            status_reason=payload.get("status_reason"),
            labels=dict(payload.get("labels", {})),
        )
