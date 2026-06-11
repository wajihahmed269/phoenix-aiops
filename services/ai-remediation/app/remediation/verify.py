from __future__ import annotations

import json
import subprocess

from app.models.recommendation import Recommendation
from app.remediation.models import RemediationPlan, VerificationResult


def verify_remediation(plan: RemediationPlan, recommendation: Recommendation, config: dict, *, simulated: bool) -> VerificationResult:
    if simulated:
        return VerificationResult(
            success=True,
            mode="simulation",
            checks=[{"name": check, "status": "skipped", "reason": "simulation_only"} for check in plan.verification_checks],
            message="Verification skipped because simulation-only mode is enabled.",
        )

    checks: list[dict] = []
    success = True
    if plan.remediation_id == "restart_banking_backend":
        success &= _run_rollout_status_check(plan, recommendation, config, checks)
        success &= _run_deployment_readiness_check(recommendation, config, checks)
        success &= _run_restart_stability_check(recommendation, config, checks)
    return VerificationResult(
        success=success,
        mode="live",
        checks=checks,
        message="Verification completed successfully." if success else "Verification failed; see checks for reasons.",
    )


def _run_rollout_status_check(plan: RemediationPlan, recommendation: Recommendation, config: dict, checks: list[dict]) -> bool:
    command = [
        "kubectl",
        "--kubeconfig",
        config["kubeconfig_path"],
        "-n",
        recommendation.namespace,
        "rollout",
        "status",
        f"deployment/{recommendation.resource.get('name', '')}",
        f"--timeout={config['remediation']['execution_timeout_seconds']}s",
    ]
    return _execute_check(command, checks, "rollout_status", config["remediation"]["execution_timeout_seconds"])


def _run_deployment_readiness_check(recommendation: Recommendation, config: dict, checks: list[dict]) -> bool:
    command = [
        "kubectl",
        "--kubeconfig",
        config["kubeconfig_path"],
        "-n",
        recommendation.namespace,
        "get",
        f"deployment/{recommendation.resource.get('name', '')}",
        "-o",
        "json",
    ]
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=config["remediation"]["execution_timeout_seconds"])
        payload = json.loads(completed.stdout or "{}")
        desired = int(payload.get("spec", {}).get("replicas", 1))
        ready = int(payload.get("status", {}).get("readyReplicas", 0))
        if ready >= desired:
            checks.append({"name": "deployment_readiness", "status": "passed", "ready": ready, "desired": desired})
            return True
        checks.append({"name": "deployment_readiness", "status": "failed", "ready": ready, "desired": desired, "error": "ready replicas below desired"})
        return False
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        checks.append({"name": "deployment_readiness", "status": "failed", "error": str(exc)})
        return False


def _run_restart_stability_check(recommendation: Recommendation, config: dict, checks: list[dict]) -> bool:
    command = [
        "kubectl",
        "--kubeconfig",
        config["kubeconfig_path"],
        "-n",
        recommendation.namespace,
        "get",
        "pods",
        "-o",
        "json",
    ]
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=config["remediation"]["execution_timeout_seconds"])
        payload = json.loads(completed.stdout or "{}")
        name = recommendation.resource.get("name", "")
        matching = [item for item in payload.get("items", []) if name in item.get("metadata", {}).get("name", "")]
        restart_count = sum(status.get("restartCount", 0) for item in matching for status in item.get("status", {}).get("containerStatuses", []))
        if restart_count <= 1:
            checks.append({"name": "restart_stability", "status": "passed", "restart_count": restart_count})
            return True
        checks.append({"name": "restart_stability", "status": "failed", "restart_count": restart_count, "error": "restart count remains elevated"})
        return False
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        checks.append({"name": "restart_stability", "status": "failed", "error": str(exc)})
        return False


def _execute_check(command: list[str], checks: list[dict], name: str, timeout_seconds: int) -> bool:
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout_seconds)
        checks.append({"name": name, "status": "passed"})
        return True
    except subprocess.TimeoutExpired as exc:
        checks.append({"name": name, "status": "failed", "error": f"timed out after {exc.timeout}s"})
        return False
    except (OSError, subprocess.SubprocessError) as exc:
        checks.append({"name": name, "status": "failed", "error": str(exc)})
        return False
