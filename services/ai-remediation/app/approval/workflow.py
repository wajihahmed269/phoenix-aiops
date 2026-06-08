from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.approval.models import ApprovalRecord
from app.approval.store import ApprovalStore
from app.config.loader import load_config
from app.models.factory import utc_now
from app.models.recommendation import Recommendation
from app.remediation.models import RemediationPlan
from app.store.incident_artifacts import IncidentArtifactStore
from app.store.json_store import JsonRecommendationStore


def request_approval(
    approval_store: ApprovalStore,
    recommendation_store: JsonRecommendationStore,
    recommendation: Recommendation,
    plan: RemediationPlan,
    *,
    requested_by: str,
    reason: str,
    config: dict | None = None,
    scope: str = "execute",
) -> ApprovalRecord:
    active_config = config or load_config()
    requested_at = utc_now()
    expires_at = _expires_at(requested_at, active_config["remediation"]["approval_ttl_minutes"])
    record = ApprovalRecord(
        approval_id=f"apr-{uuid4()}",
        recommendation_id=recommendation.recommendation_id,
        incident_id=recommendation.incident_id,
        plan_id=plan.plan_id,
        remediation_id=plan.remediation_id,
        resource={"kind": plan.resource_kind, "name": plan.resource_name},
        status="requested",
        requested_by=requested_by,
        approver=None,
        requested_at=requested_at,
        decided_at=None,
        reason=reason,
        scope=scope,
        expires_at=expires_at,
    )
    approval_store.save(record)
    _append_timeline(active_config, recommendation.incident_id, requested_at, "approval", f"Approval requested by {requested_by} for {scope}.")
    recommendation_store.update_status(recommendation.recommendation_id, "acknowledged", updated_at=requested_at, reason="approval requested")
    return record


def approve_recommendation(
    approval_store: ApprovalStore,
    recommendation_store: JsonRecommendationStore,
    recommendation: Recommendation,
    plan: RemediationPlan,
    *,
    approver: str,
    reason: str,
    config: dict | None = None,
) -> ApprovalRecord:
    active_config = config or load_config()
    latest = approval_store.latest_for_plan(recommendation.recommendation_id, plan.plan_id, plan.remediation_id, {"kind": plan.resource_kind, "name": plan.resource_name})
    if latest is None:
        raise KeyError("approval request not found")
    decided_at = utc_now()
    record = ApprovalRecord(
        approval_id=latest.approval_id,
        recommendation_id=latest.recommendation_id,
        incident_id=latest.incident_id,
        plan_id=latest.plan_id,
        remediation_id=latest.remediation_id,
        resource=latest.resource,
        status="approved",
        requested_by=latest.requested_by,
        approver=approver,
        requested_at=latest.requested_at,
        decided_at=decided_at,
        reason=reason,
        scope=latest.scope,
        expires_at=latest.expires_at,
    )
    approval_store.save(record)
    recommendation_store.update_status(recommendation.recommendation_id, "approved", updated_at=decided_at, reason=reason)
    _append_timeline(active_config, recommendation.incident_id, decided_at, "approval", f"Recommendation approved by {approver}.")
    return record


def reject_recommendation(
    approval_store: ApprovalStore,
    recommendation_store: JsonRecommendationStore,
    recommendation: Recommendation,
    plan: RemediationPlan,
    *,
    approver: str,
    reason: str,
    config: dict | None = None,
) -> ApprovalRecord:
    active_config = config or load_config()
    latest = approval_store.latest_for_plan(recommendation.recommendation_id, plan.plan_id, plan.remediation_id, {"kind": plan.resource_kind, "name": plan.resource_name})
    if latest is None:
        raise KeyError("approval request not found")
    decided_at = utc_now()
    record = ApprovalRecord(
        approval_id=latest.approval_id,
        recommendation_id=latest.recommendation_id,
        incident_id=latest.incident_id,
        plan_id=latest.plan_id,
        remediation_id=latest.remediation_id,
        resource=latest.resource,
        status="rejected",
        requested_by=latest.requested_by,
        approver=approver,
        requested_at=latest.requested_at,
        decided_at=decided_at,
        reason=reason,
        scope=latest.scope,
        expires_at=latest.expires_at,
    )
    approval_store.save(record)
    recommendation_store.update_status(recommendation.recommendation_id, "rejected", updated_at=decided_at, reason=reason)
    _append_timeline(active_config, recommendation.incident_id, decided_at, "approval", f"Recommendation rejected by {approver}: {reason}.")
    return record


def latest_valid_approval(
    approval_store: ApprovalStore,
    recommendation_id: str,
    plan: RemediationPlan,
    *,
    now: str | None = None,
) -> ApprovalRecord | None:
    latest = approval_store.latest_for_plan(recommendation_id, plan.plan_id, plan.remediation_id, {"kind": plan.resource_kind, "name": plan.resource_name})
    if latest is None:
        return None
    if latest.status != "approved":
        return None
    current = _parse_time(now or utc_now())
    if current > _parse_time(latest.expires_at):
        return None
    return latest


def _expires_at(started_at: str, ttl_minutes: int) -> str:
    return (_parse_time(started_at) + timedelta(minutes=int(ttl_minutes))).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _append_timeline(config: dict, incident_id: str, timestamp: str, stage: str, message: str) -> None:
    IncidentArtifactStore(config["incident_artifacts_path"]).append_timeline(incident_id, timestamp=timestamp, stage=stage, message=message)
