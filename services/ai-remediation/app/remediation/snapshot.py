from __future__ import annotations

import subprocess
import json
from pathlib import Path

from app.models.recommendation import Recommendation
from app.remediation.models import RemediationPlan, SnapshotResult


def capture_snapshot(plan: RemediationPlan, recommendation: Recommendation, config: dict) -> SnapshotResult:
    rollback_dir = Path(config["incident_artifacts_path"]) / recommendation.incident_id / "rollback"
    rollback_dir.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    warnings: list[str] = []
    argo_namespace = str(config.get("argo_namespace", "argocd"))

    commands = {
        "resource.yaml": _kubectl(config, ["-n", recommendation.namespace, "get", _resource_ref(recommendation), "-o", "yaml"]),
        "rollout.txt": _kubectl(config, ["-n", recommendation.namespace, "rollout", "status", _resource_ref(recommendation), f"--timeout={config['remediation']['execution_timeout_seconds']}s"]),
        "describe.txt": _kubectl(config, ["-n", recommendation.namespace, "describe", recommendation.resource.get("kind", "").lower(), recommendation.resource.get("name", "")]),
        "pods.json": _kubectl(config, ["-n", recommendation.namespace, "get", "pods", "-o", "json"]),
        "events.txt": _kubectl(config, ["-n", recommendation.namespace, "get", "events", "--sort-by=.lastTimestamp"]),
        "argo-apps.txt": _kubectl(config, ["--namespace", argo_namespace, "get", "applications.argoproj.io"]),
    }

    for filename, result in commands.items():
        path = rollback_dir / filename
        if result is None:
            warnings.append(f"snapshot command failed for {filename}")
            continue
        path.write_text(result, encoding="utf-8")
        files.append(str(path))

    (rollback_dir / "snapshot-metadata.txt").write_text(
        f"plan_id={plan.plan_id}\nremediation_id={plan.remediation_id}\nresource={_resource_ref(recommendation)}\n",
        encoding="utf-8",
    )
    files.append(str(rollback_dir / "snapshot-metadata.txt"))
    (rollback_dir / "plan.json").write_text(json.dumps(plan.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    files.append(str(rollback_dir / "plan.json"))
    (rollback_dir / "recommendation.json").write_text(json.dumps(recommendation.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    files.append(str(rollback_dir / "recommendation.json"))
    return SnapshotResult(created=bool(files), rollback_path=str(rollback_dir), files=files, warnings=warnings)


def _kubectl(config: dict, args: list[str]) -> str | None:
    command = ["kubectl", "--kubeconfig", config["kubeconfig_path"], *args]
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=config["request_timeouts"]["kubectl_seconds"])
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout or completed.stderr or ""


def _resource_ref(recommendation: Recommendation) -> str:
    return f"{recommendation.resource.get('kind', '').lower()}/{recommendation.resource.get('name', '')}"
