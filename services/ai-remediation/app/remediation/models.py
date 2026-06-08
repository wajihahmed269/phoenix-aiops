from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CatalogEntry:
    remediation_id: str
    description: str
    allowed_namespaces: list[str]
    allowed_resource_kinds: list[str]
    risk_class: str
    blast_radius: str
    rollback_capability: str
    required_evidence: list[str]
    verification_checks: list[str]
    cooldown_minutes: int
    timeout_seconds: int
    required_approval_level: str
    executable: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RemediationPlan:
    plan_id: str
    incident_id: str
    recommendation_id: str
    remediation_id: str
    resource_kind: str
    resource_name: str
    description: str
    namespace: str
    resource: dict[str, str]
    risk_class: str
    blast_radius: str
    rollback_capability: str
    approval_required: bool
    required_approval_level: str
    preflight_checks: list[str]
    validation_steps: list[str]
    verification_checks: list[str]
    command_preview: list[list[str]]
    simulation_only: bool
    executable: bool
    status: str = "planned"
    notes: list[str] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GuardDecision:
    allow: bool
    reasons: list[str]
    checks: list[str]
    approval_scope_valid: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SnapshotResult:
    created: bool
    rollback_path: str
    files: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationResult:
    success: bool
    mode: str
    checks: list[dict[str, Any]]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionResult:
    success: bool
    mode: str
    message: str
    commands: list[list[str]]
    guard_decision: dict[str, Any]
    snapshot: dict[str, Any]
    verification: dict[str, Any]
    audit_id: str
    started_at: str
    finished_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
