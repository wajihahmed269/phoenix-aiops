from __future__ import annotations

from app.approval.models import ApprovalRecord
from app.models.recommendation import Recommendation
from app.remediation.models import RemediationPlan


def build_email_payload(recommendation: Recommendation, plan: RemediationPlan | None = None, *, approval: ApprovalRecord | None = None, fallback_candidate: bool = False) -> dict:
    subject = f"Phoenix-Ops incident {recommendation.incident_id}: {recommendation.summary}"
    evidence_summary = ", ".join(item.get("name", "evidence") for item in recommendation.evidence[:3])
    lines = [
        f"Incident: {recommendation.incident_id}",
        f"Recommendation: {recommendation.recommendation_id}",
        f"Namespace: {recommendation.namespace}",
        f"Resource: {recommendation.resource.get('kind')}/{recommendation.resource.get('name')}",
        f"Severity: {recommendation.severity}",
        f"Summary: {recommendation.summary}",
        f"Evidence summary: {evidence_summary}",
        f"Rationale: {recommendation.rationale}",
    ]
    if plan is not None:
        lines.extend(
            [
                f"Proposed remediation: {plan.remediation_id}",
                f"Risk class: {plan.risk_class}",
                f"Simulation only: {plan.simulation_only}",
                f"Fallback candidate: {str(fallback_candidate).lower()}",
            ]
        )
    if approval is not None:
        lines.append(f"Approval status: {approval.status} by {approval.approver or 'pending'}")
    return {"subject": subject, "body": "\n".join(lines)}


def build_markdown_summary(recommendation: Recommendation, plan: RemediationPlan | None = None, *, approval: ApprovalRecord | None = None, fallback_candidate: bool = False) -> str:
    markdown = [
        f"# Incident {recommendation.incident_id}",
        "",
        f"- Recommendation: `{recommendation.recommendation_id}`",
        f"- Resource: `{recommendation.resource.get('kind')}/{recommendation.resource.get('name')}`",
        f"- Namespace: `{recommendation.namespace}`",
        f"- Severity: `{recommendation.severity}`",
        f"- Summary: {recommendation.summary}",
        f"- Evidence Summary: {', '.join(item.get('name', 'evidence') for item in recommendation.evidence[:3])}",
    ]
    if plan is not None:
        markdown.extend(
            [
                f"- Planned remediation: `{plan.remediation_id}`",
                f"- Approval required: `{str(plan.approval_required).lower()}`",
                f"- Simulation only: `{str(plan.simulation_only).lower()}`",
                f"- Fallback candidate: `{str(fallback_candidate).lower()}`",
            ]
        )
    if approval is not None:
        markdown.append(f"- Approval status: `{approval.status}`")
    return "\n".join(markdown) + "\n"
