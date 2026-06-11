from __future__ import annotations

from app.models.recommendation import Recommendation


def build_email_payload(
    recommendation: Recommendation,
    *,
    advisory: dict | None,
    timeline_entries: list[str],
    escalation_state: dict,
    simulation_only: bool,
) -> dict:
    subject = (
        f"Phoenix-Ops incident {recommendation.incident_id} "
        f"[{recommendation.severity}] {recommendation.resource.get('kind')}/{recommendation.resource.get('name')}"
    )
    lines = [
        f"Incident: {recommendation.incident_id}",
        f"Resource: {recommendation.resource.get('kind')}/{recommendation.resource.get('name')}",
        f"Namespace: {recommendation.namespace}",
        f"Severity: {recommendation.severity}",
        f"Problem: {recommendation.summary}",
        f"Evidence: {_evidence_summary(recommendation, advisory)}",
        f"Recommendation: {recommendation.summary}",
        f"K8sGPT summary: {_k8sgpt_summary(advisory)}",
        f"Timeline summary: {' | '.join(timeline_entries[-3:]) if timeline_entries else 'No timeline entries recorded yet.'}",
        f"Safe suggested action: {_safe_action_text(recommendation)}",
        f"Action allowed?: {_auto_restart_text(recommendation)}",
        f"Simulation/live mode: {'simulation-only' if simulation_only else 'live-disabled'}",
        f"Approval requirement state: {escalation_state['approval_state']}",
        f"Next operator step: {_next_operator_step(recommendation, escalation_state)}",
    ]
    return {"subject": subject, "body": "\n".join(lines)}


def build_markdown_summary(
    recommendation: Recommendation,
    *,
    advisory: dict | None,
    timeline_entries: list[str],
    escalation_state: dict,
    simulation_only: bool,
) -> str:
    markdown = [
        f"# Incident {recommendation.incident_id}",
        "",
        "## Problem",
        "",
        f"- Resource: `{recommendation.resource.get('kind')}/{recommendation.resource.get('name')}`",
        f"- Namespace: `{recommendation.namespace}`",
        f"- Severity: `{recommendation.severity}`",
        f"- Summary: {recommendation.summary}",
        "",
        "## Evidence",
        "",
        f"- {_evidence_summary(recommendation, advisory)}",
        "",
        "## K8sGPT Summary",
        "",
        _k8sgpt_summary(advisory),
        "",
        "## Recommendation",
        "",
        _safe_action_text(recommendation),
        "",
        "## Policy",
        "",
        f"- Approval requirement: `{escalation_state['approval_state']}`",
        f"- Execution state: `{escalation_state['execution_state']}`",
        f"- Auto-restart status: `{_auto_restart_text(recommendation)}`",
        f"- Mode: `{'simulation-only' if simulation_only else 'live-disabled'}`",
        f"- Next operator step: {_next_operator_step(recommendation, escalation_state)}",
        "",
        "## Timeline Summary",
        "",
    ]
    for entry in timeline_entries[-5:]:
        markdown.append(f"- {entry}")
    return "\n".join(markdown) + "\n"


def _k8sgpt_summary(advisory: dict | None) -> str:
    if not advisory:
        return "K8sGPT advisory did not run."
    if advisory.get("status") != "ok":
        return f"K8sGPT advisory unavailable: {advisory.get('error') or advisory.get('status', 'unknown')}."
    matched = advisory.get("matched_findings", [])
    if matched:
        return matched[0].get("message", "K8sGPT returned a matching finding without details.")
    return "K8sGPT completed without a matching advisory finding for the resource."


def _safe_action_text(recommendation: Recommendation) -> str:
    if recommendation.suggested_actions:
        return recommendation.suggested_actions[0].description
    return "Review the bounded recommendation manually; no live execution is enabled."


def _evidence_summary(recommendation: Recommendation, advisory: dict | None) -> str:
    evidence_count = len(recommendation.evidence)
    if advisory and advisory.get("status") == "ok":
        matched = len(advisory.get("matched_findings", []))
        if matched:
            return f"{evidence_count} evidence item(s), {matched} K8sGPT finding(s) matched."
        return f"{evidence_count} evidence item(s), K8sGPT completed without a direct match."
    if advisory:
        return f"{evidence_count} evidence item(s), K8sGPT unavailable: {advisory.get('error') or advisory.get('status', 'unknown')}."
    return f"{evidence_count} evidence item(s), K8sGPT did not run."


def _auto_restart_text(recommendation: Recommendation) -> str:
    if recommendation.namespace == "bankapp" and recommendation.resource.get("kind") == "Deployment" and recommendation.resource.get("name") == "banking-backend":
        return "Eligible only under the bounded banking-backend policy; execution remains disabled by default."
    return "No auto-restart path is configured for this incident."


def _next_operator_step(recommendation: Recommendation, escalation_state: dict) -> str:
    if recommendation.namespace == "bankapp" and recommendation.resource.get("name") == "banking-backend":
        return "Review the bounded restart policy, then keep monitoring until an operator explicitly authorizes execution."
    if escalation_state.get("approval_state") == "human_approval_required":
        return "Review the incident, validate the evidence, and decide whether to acknowledge or suppress."
    return "Monitor the incident and confirm the report was written correctly."
