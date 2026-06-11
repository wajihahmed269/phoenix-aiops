from __future__ import annotations

import subprocess
from uuid import uuid4

from app.approval.models import ApprovalRecord
from app.models.factory import utc_now
from app.models.recommendation import Recommendation
from app.remediation.guards import evaluate_guardrails
from app.remediation.models import ExecutionResult, RemediationPlan
from app.remediation.snapshot import capture_snapshot
from app.remediation.verify import verify_remediation
from app.store.execution_audit import ExecutionAuditStore
from app.store.incident_artifacts import IncidentArtifactStore


def execute_plan(
    plan: RemediationPlan,
    recommendation: Recommendation,
    config: dict,
    *,
    approval: ApprovalRecord | None,
    explicit_execute: bool,
    auto_execute: bool = False,
) -> ExecutionResult:
    audit_store = ExecutionAuditStore(config["execution_audit_path"])
    started_at = utc_now()
    guard_decision = evaluate_guardrails(
        plan,
        recommendation,
        config,
        approval=approval,
        audit_store=audit_store,
        explicit_execute=explicit_execute,
        auto_execute=auto_execute,
    )
    artifacts = IncidentArtifactStore(config["incident_artifacts_path"], config.get("incident_artifacts"))
    snapshot = capture_snapshot(plan, recommendation, config)
    artifacts.append_timeline(plan.incident_id, timestamp=started_at, stage="snapshot", message="snapshot captured before remediation")

    simulated = True
    commands = list(plan.command_preview)
    success = False
    message = "Execution blocked by guardrails."
    if guard_decision.allow and explicit_execute and not config["remediation"]["simulation_only"]:
        simulated = False
        success, message = _run_commands(commands, timeout_seconds=config["remediation"]["execution_timeout_seconds"])
    elif guard_decision.allow:
        success = True
        message = "Simulation-only mode preserved. No mutation executed."

    verification = verify_remediation(plan, recommendation, config, simulated=simulated or not success)
    audit_id = f"aud-{uuid4()}"
    finished_at = utc_now()
    record = {
        "audit_id": audit_id,
        "incident_id": plan.incident_id,
        "recommendation_id": plan.recommendation_id,
        "plan_id": plan.plan_id,
        "action": plan.remediation_id,
        "namespace": plan.namespace,
        "resource": {"kind": plan.resource_kind, "name": plan.resource_name},
        "status": "simulated" if simulated else ("succeeded" if success else "failed"),
        "mode": "simulation" if simulated else "live",
        "auto_execute": auto_execute,
        "approved_by": approval.approver if approval else None,
        "command_preview": commands,
        "started_at": started_at,
        "finished_at": finished_at,
        "verification": verification.to_dict(),
        "rollback_path": snapshot.rollback_path,
        "message": message,
    }
    audit_store.append(record)
    artifacts.append_timeline(
        plan.incident_id,
        timestamp=finished_at,
        stage="execution",
        message=f"Remediation {plan.remediation_id} completed in {'simulation' if simulated else 'live'} mode with status {record['status']}.",
    )
    artifacts.write_json(plan.incident_id, "execution-audit.json", record)
    return ExecutionResult(
        success=success,
        mode="simulation" if simulated else "live",
        message=message,
        commands=commands,
        guard_decision=guard_decision.to_dict(),
        snapshot=snapshot.to_dict(),
        verification=verification.to_dict(),
        audit_id=audit_id,
        started_at=started_at,
        finished_at=finished_at,
    )


def _run_commands(commands: list[list[str]], *, timeout_seconds: int) -> tuple[bool, str]:
    for command in commands:
        _validate_command(command)
        try:
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout_seconds)
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"command failed: {exc}"
    return True, "Commands executed successfully."


def _validate_command(command: list[str]) -> None:
    if not command or command[0] != "kubectl":
        raise ValueError("only kubectl commands are allowed")
    joined = " ".join(command)
    allowed = (" rollout restart ", " rollout status ", " get ", " describe ", " logs ")
    if not any(token in f" {joined} " for token in allowed):
        raise ValueError("kubectl command is not in the explicit allowlist")
