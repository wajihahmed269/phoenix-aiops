from __future__ import annotations

import json
import subprocess

from app.models.events import IncidentEvent
from app.models.factory import create_incident_event


def collect_argo_events(config: dict) -> list[IncidentEvent]:
    command = [
        "kubectl",
        "--kubeconfig",
        config["kubeconfig_path"],
        "get",
        "applications.argoproj.io",
        "-A",
        "-o",
        "json",
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=config["request_timeouts"]["kubectl_seconds"])
    payload = json.loads(completed.stdout or "{}")
    events: list[IncidentEvent] = []
    for item in payload.get("items", []):
        namespace = item["metadata"].get("namespace", config["argo_namespace"])
        name = item["metadata"]["name"]
        sync_status = item.get("status", {}).get("sync", {}).get("status", "Unknown")
        health_status = item.get("status", {}).get("health", {}).get("status", "Unknown")
        if sync_status == "Synced" and health_status == "Healthy":
            continue
        scenario = "deployment_unhealthy" if health_status != "Healthy" else "target_down"
        severity = "medium" if health_status != "Healthy" else "low"
        events.append(
            create_incident_event(
                source="argocd",
                scenario=scenario,
                cluster=config["cluster_name"],
                namespace=namespace,
                resource_kind="Application",
                resource_name=name,
                severity_hint=severity,
                summary=f"Argo CD application not healthy/synced: {namespace}/{name}",
                evidence=[
                    {
                        "type": "state",
                        "name": "application_status",
                        "value": {"sync": sync_status, "health": health_status},
                        "labels": {
                            "revision": str(item.get("status", {}).get("sync", {}).get("revision", "")),
                            "project": str(item.get("spec", {}).get("project", "")),
                        },
                    }
                ],
                max_evidence_items=config["max_evidence_items"],
            )
        )
    return events
