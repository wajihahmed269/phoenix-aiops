from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta

from app.approval.models import ApprovalRecord
from app.config.runtime import load_auto_remediation_settings
from app.models.recommendation import Recommendation
from app.remediation.models import GuardDecision, RemediationPlan
from app.store.execution_audit import ExecutionAuditStore


def evaluate_guardrails(
    plan: RemediationPlan,
    recommendation: Recommendation,
    config: dict,
    *,
    approval: ApprovalRecord | None,
    audit_store: ExecutionAuditStore,
    explicit_execute: bool,
    auto_execute: bool = False,
) -> GuardDecision:
    reasons: list[str] = []
    checks: list[str] = []
    approval_scope_valid = False

    if recommendation.namespace not in config["remediation"]["namespace_allowlist"]:
        reasons.append("namespace not allowed for remediation")
    checks.append("namespace_allowlist_checked")

    if recommendation.resource.get("kind") not in config["remediation"]["resource_kind_allowlist"]:
        reasons.append("resource kind not allowed for remediation")
    checks.append("resource_kind_allowlist_checked")

    if recommendation.namespace in config["remediation"].get("protected_namespaces", []):
        reasons.append("protected namespace cannot be mutated in this phase")
    checks.append("protected_namespace_checked")

    if auto_execute:
        approval_scope_valid = _evaluate_auto_execute_policy(plan, recommendation, config, reasons)
    else:
        approval_scope_valid = _evaluate_manual_approval(plan, approval, reasons)
    checks.append("approval_or_auto_policy_checked")

    if not _cluster_api_reachable(config):
        reasons.append("cluster API unreachable")
    checks.append("cluster_reachability_checked")

    latest_target = audit_store.latest_for_target(plan.remediation_id, plan.namespace, plan.resource_kind, plan.resource_name)
    if latest_target and latest_target.get("status") in {"simulated", "succeeded"}:
        reasons.append("duplicate execution prevented for this remediation target")
    checks.append("duplicate_execution_checked")

    if _blast_rank(plan.blast_radius) > _blast_rank(config["remediation"]["max_blast_radius"]):
        reasons.append("blast radius exceeds configured maximum")
    checks.append("blast_radius_checked")

    if not plan.executable:
        reasons.append("plan is not executable in this phase")
    checks.append("catalog_executable_checked")

    if not _commands_allowed(plan.command_preview, config["remediation"]["command_allowlist"]):
        reasons.append("command preview contains disallowed remediation actions")
    checks.append("command_allowlist_checked")

    if explicit_execute and not config["feature_flags"].get("enable_execution", False):
        reasons.append("execution feature flag disabled")
    checks.append("execution_flag_checked")

    if _cooldown_active(plan, audit_store):
        reasons.append("cooldown active for this remediation target")
    checks.append("cooldown_checked")

    if config["remediation"].get("maintenance_windows_enabled", False):
        reasons.append("maintenance window enforcement not implemented for this phase")
    checks.append("maintenance_window_checked")

    if explicit_execute and config["remediation"]["simulation_only"]:
        reasons.append("simulation-only mode is enabled")
    checks.append("simulation_mode_checked")

    return GuardDecision(allow=not reasons, reasons=reasons, checks=checks, approval_scope_valid=approval_scope_valid)


def _evaluate_manual_approval(plan: RemediationPlan, approval: ApprovalRecord | None, reasons: list[str]) -> bool:
    if approval is None:
        reasons.append("valid approval is required before execution")
        return False
    approval_scope_valid = False
    if approval.plan_id != plan.plan_id or approval.remediation_id != plan.remediation_id or approval.resource != {"kind": plan.resource_kind, "name": plan.resource_name}:
        reasons.append("approval scope does not match remediation plan")
    else:
        approval_scope_valid = True
    expires_at = _parse_time(approval.expires_at)
    if _parse_time(datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")) > expires_at:
        reasons.append("approval expired")
    return approval_scope_valid


def _evaluate_auto_execute_policy(plan: RemediationPlan, recommendation: Recommendation, config: dict, reasons: list[str]) -> bool:
    settings = load_auto_remediation_settings(config)
    if not settings.config_enabled:
        reasons.append("auto-remediation policy disabled")
    if not settings.env_enabled:
        reasons.append("AUTO_RESTART_BANKING_BACKEND is not enabled")
    if plan.remediation_id != "restart_banking_backend":
        reasons.append("plan is not the allowed banking-backend restart action")
    if recommendation.namespace != settings.allowed_namespace:
        reasons.append("auto-remediation namespace is not allowed")
    if recommendation.resource.get("kind") != "Deployment":
        reasons.append("auto-remediation is only allowed for Deployment resources")
    if recommendation.resource.get("name") != settings.allowed_deployment:
        reasons.append("auto-remediation is only allowed for deployment/banking-backend")
    if "restart_banking_backend" not in settings.allowed_actions:
        reasons.append("restart_banking_backend is not present in allowed_actions")
    if not settings.require_snapshot:
        reasons.append("snapshot required")
    if not settings.verify_rollout:
        reasons.append("rollout verification required")
    if "rollout_status" not in plan.verification_checks or "deployment_readiness" not in plan.verification_checks:
        reasons.append("verification checks are incomplete for auto-remediation")
    return not reasons


def _cluster_api_reachable(config: dict) -> bool:
    command = ["kubectl", "--kubeconfig", config["kubeconfig_path"], "cluster-info"]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=config["request_timeouts"]["kubectl_seconds"])
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def _cooldown_active(plan: RemediationPlan, audit_store: ExecutionAuditStore) -> bool:
    cooldown_minutes = max(0, int(plan.labels.get("cooldown_minutes", "0") or 0))
    if cooldown_minutes == 0:
        return False
    latest = audit_store.latest_for_target(plan.remediation_id, plan.namespace, plan.resource_kind, plan.resource_name)
    if latest is None:
        return False
    finished_at = latest.get("finished_at") or latest.get("started_at")
    if not finished_at:
        return False
    return datetime.now(UTC) - _parse_time(finished_at) < timedelta(minutes=cooldown_minutes)


def _blast_rank(value: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(value, 99)


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _commands_allowed(commands: list[list[str]], allowlist: list[str]) -> bool:
    normalized_allowlist = tuple(item.lower() for item in allowlist)
    for command in commands:
        joined = " ".join(command).lower()
        if not any(item in joined for item in normalized_allowlist):
            return False
    return True
