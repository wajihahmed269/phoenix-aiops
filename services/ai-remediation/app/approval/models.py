from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ApprovalRecord:
    approval_id: str
    recommendation_id: str
    incident_id: str
    plan_id: str
    remediation_id: str
    resource: dict[str, str]
    status: str
    requested_by: str
    approver: str | None
    requested_at: str
    decided_at: str | None
    reason: str
    scope: str
    expires_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ApprovalRecord":
        return cls(
            approval_id=str(payload["approval_id"]),
            recommendation_id=str(payload["recommendation_id"]),
            incident_id=str(payload["incident_id"]),
            plan_id=str(payload["plan_id"]),
            remediation_id=str(payload["remediation_id"]),
            resource=dict(payload.get("resource", {})),
            status=str(payload["status"]),
            requested_by=str(payload["requested_by"]),
            approver=payload.get("approver"),
            requested_at=str(payload["requested_at"]),
            decided_at=payload.get("decided_at"),
            reason=str(payload.get("reason", "")),
            scope=str(payload.get("scope", "execute")),
            expires_at=str(payload["expires_at"]),
        )
