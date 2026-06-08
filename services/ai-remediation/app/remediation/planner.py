from __future__ import annotations

from hashlib import sha256
from uuid import uuid4

from app.remediation.catalog import load_catalog
from app.remediation.models import CatalogEntry, RemediationPlan
from app.models.recommendation import Recommendation


SCENARIO_TO_REMEDIATION = {
    ("deployment_unhealthy", "Deployment"): "restart_deployment",
    ("repeated_restart", "Deployment"): "restart_deployment",
}


def generate_plan(recommendation: Recommendation, config: dict) -> RemediationPlan:
    catalog = load_catalog()
    remediation_id = _select_remediation_id(recommendation)
    if remediation_id is None:
        raise ValueError("no catalog-approved remediation for this recommendation")

    entry = catalog[remediation_id]
    _validate_catalog_entry(entry, recommendation, config)
    commands = _build_command_preview(entry, recommendation, config)

    return RemediationPlan(
        plan_id=_build_plan_id(recommendation, entry.remediation_id),
        incident_id=recommendation.incident_id,
        recommendation_id=recommendation.recommendation_id,
        remediation_id=entry.remediation_id,
        resource_kind=recommendation.resource.get("kind", ""),
        resource_name=recommendation.resource.get("name", ""),
        description=entry.description,
        namespace=recommendation.namespace,
        resource=dict(recommendation.resource),
        risk_class=entry.risk_class,
        blast_radius=entry.blast_radius,
        rollback_capability=entry.rollback_capability,
        approval_required=True,
        required_approval_level=entry.required_approval_level,
        preflight_checks=[
            "approval_valid",
            "api_reachable",
            "cluster_healthy",
            "cooldown_clear",
            "blast_radius_allowed",
        ],
        validation_steps=[
            "validate_namespace_allowlist",
            "validate_catalog_action",
            "validate_duplicate_execution_prevention",
            "validate_simulation_mode_or_execution_enablement",
        ],
        verification_checks=list(entry.verification_checks),
        command_preview=commands,
        simulation_only=bool(config["remediation"]["simulation_only"]),
        executable=entry.executable,
        notes=[
            f"Generated from recommendation {recommendation.recommendation_id}",
            "Only catalog-approved bounded actions are eligible for execution.",
        ],
        labels={
            "scenario": recommendation.labels.get("scenario", ""),
            "severity": recommendation.severity,
            "cooldown_minutes": str(entry.cooldown_minutes),
        },
    )


def build_remediation_plan(recommendation: Recommendation, config: dict) -> RemediationPlan:
    return generate_plan(recommendation, config)


def _select_remediation_id(recommendation: Recommendation) -> str | None:
    scenario = recommendation.labels.get("scenario", "")
    kind = recommendation.resource.get("kind", "")
    return SCENARIO_TO_REMEDIATION.get((scenario, kind))


def _validate_catalog_entry(entry: CatalogEntry, recommendation: Recommendation, config: dict) -> None:
    if recommendation.namespace not in entry.allowed_namespaces:
        raise ValueError(f"namespace {recommendation.namespace} is not allowed for {entry.remediation_id}")
    if recommendation.namespace not in config["remediation"]["namespace_allowlist"]:
        raise ValueError(f"namespace {recommendation.namespace} is not in remediation namespace allowlist")
    if recommendation.resource.get("kind") not in entry.allowed_resource_kinds:
        raise ValueError(f"resource kind {recommendation.resource.get('kind')} is not allowed for {entry.remediation_id}")
    max_blast_radius = config["remediation"]["max_blast_radius"]
    if _blast_rank(entry.blast_radius) > _blast_rank(max_blast_radius):
        raise ValueError(f"blast radius {entry.blast_radius} exceeds configured maximum {max_blast_radius}")


def _build_command_preview(entry: CatalogEntry, recommendation: Recommendation, config: dict) -> list[list[str]]:
    kubeconfig = config["kubeconfig_path"]
    namespace = recommendation.namespace
    resource_name = recommendation.resource.get("name", "")
    kind = recommendation.resource.get("kind", "")
    if entry.remediation_id == "restart_deployment":
        return [
            ["kubectl", "--kubeconfig", kubeconfig, "-n", namespace, "rollout", "restart", f"deployment/{resource_name}"],
            ["kubectl", "--kubeconfig", kubeconfig, "-n", namespace, "rollout", "status", f"deployment/{resource_name}", f"--timeout={entry.timeout_seconds}s"],
        ]
    if entry.remediation_id in {"cordon_node", "uncordon_node"} and kind == "Node":
        return [["kubectl", "--kubeconfig", kubeconfig, entry.remediation_id.split("_")[0], resource_name]]
    return []


def _blast_rank(value: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(value, 99)


def _build_plan_id(recommendation: Recommendation, remediation_id: str) -> str:
    raw = "|".join(
        [
            recommendation.incident_id,
            recommendation.recommendation_id,
            remediation_id,
            recommendation.namespace,
            recommendation.resource.get("kind", ""),
            recommendation.resource.get("name", ""),
        ]
    ).encode("utf-8")
    return f"plan-{sha256(raw).hexdigest()[:12]}"
