from __future__ import annotations

import json
import subprocess
from typing import Any

from app.models.events import IncidentEvent
from app.models.factory import create_incident_event


ALLOWED_VERBS = {"get", "top", "describe"}


def collect_kubernetes_events(config: dict) -> list[IncidentEvent]:
    events: list[IncidentEvent] = []
    namespaces = set(config["namespace_allowlist"])
    pods = _kubectl_json(config, ["get", "pods", "-A", "-o", "json"])
    deployments = _kubectl_json(config, ["get", "deployments", "-A", "-o", "json"])
    k8s_events = _kubectl_json(config, ["get", "events", "-A", "-o", "json"])
    pod_top = _kubectl_top_pods(config)

    for item in pods.get("items", []):
        namespace = item["metadata"].get("namespace", "")
        if namespace not in namespaces:
            continue
        name = item["metadata"]["name"]
        restart_count = sum(status.get("restartCount", 0) for status in item.get("status", {}).get("containerStatuses", []))
        waiting_reasons = [
            status.get("state", {}).get("waiting", {}).get("reason", "")
            for status in item.get("status", {}).get("containerStatuses", [])
        ]
        if "CrashLoopBackOff" in waiting_reasons or restart_count >= config["restart_thresholds"]["crashloop_restart_count"] and any(reason in {"CrashLoopBackOff", "Error"} for reason in waiting_reasons):
            events.append(
                create_incident_event(
                    source="kubernetes",
                    scenario="pod_crashloop",
                    cluster=config["cluster_name"],
                    namespace=namespace,
                    resource_kind="Pod",
                    resource_name=name,
                    severity_hint="high",
                    summary=f"Pod crashloop detected: {namespace}/{name}",
                    evidence=_pod_evidence(item, restart_count, k8s_events),
                    max_evidence_items=config["max_evidence_items"],
                )
            )
        elif restart_count >= config["restart_thresholds"]["repeated_restart_count"]:
            events.append(
                create_incident_event(
                    source="kubernetes",
                    scenario="repeated_restart",
                    cluster=config["cluster_name"],
                    namespace=namespace,
                    resource_kind="Pod",
                    resource_name=name,
                    severity_hint="medium",
                    summary=f"Repeated pod restarts detected: {namespace}/{name}",
                    evidence=_pod_evidence(item, restart_count, k8s_events),
                    max_evidence_items=config["max_evidence_items"],
                )
            )

        top_entry = pod_top.get((namespace, name))
        if top_entry and top_entry["memory_mib"] >= config["memory_thresholds"]["pod_working_set_mib_warn"]:
            events.append(
                create_incident_event(
                    source="kubernetes",
                    scenario="high_memory",
                    cluster=config["cluster_name"],
                    namespace=namespace,
                    resource_kind="Pod",
                    resource_name=name,
                    severity_hint="medium",
                    summary=f"High pod memory usage detected: {namespace}/{name}",
                    evidence=[
                        {
                            "type": "metric",
                            "name": "pod_memory_mib",
                            "value": top_entry["memory_mib"],
                            "labels": {"namespace": namespace, "pod": name},
                        }
                    ],
                    max_evidence_items=config["max_evidence_items"],
                )
            )

    for item in deployments.get("items", []):
        namespace = item["metadata"].get("namespace", "")
        if namespace not in namespaces:
            continue
        desired = item.get("spec", {}).get("replicas", 1)
        available = item.get("status", {}).get("availableReplicas", 0)
        progressing = next((cond for cond in item.get("status", {}).get("conditions", []) if cond.get("type") == "Progressing"), {})
        if available < desired or progressing.get("status") == "False":
            name = item["metadata"]["name"]
            events.append(
                create_incident_event(
                    source="kubernetes",
                    scenario="deployment_unhealthy",
                    cluster=config["cluster_name"],
                    namespace=namespace,
                    resource_kind="Deployment",
                    resource_name=name,
                    severity_hint="medium",
                    summary=f"Deployment unhealthy: {namespace}/{name}",
                    evidence=[
                        {
                            "type": "state",
                            "name": "deployment_status",
                            "value": {"desired": desired, "available": available},
                            "labels": {"condition_reason": str(progressing.get("reason", ""))},
                        }
                    ],
                    max_evidence_items=config["max_evidence_items"],
                )
            )

    return events


def _pod_evidence(pod: dict[str, Any], restart_count: int, events_payload: dict[str, Any]) -> list[dict]:
    namespace = pod["metadata"]["namespace"]
    name = pod["metadata"]["name"]
    related = [
        event
        for event in events_payload.get("items", [])
        if event.get("involvedObject", {}).get("kind") == "Pod"
        and event.get("involvedObject", {}).get("name") == name
        and event.get("metadata", {}).get("namespace") == namespace
    ]
    evidence = [
        {
            "type": "state",
            "name": "restart_count",
            "value": restart_count,
            "labels": {"pod_phase": str(pod.get("status", {}).get("phase", ""))},
        }
    ]
    for event in related[:2]:
        evidence.append(
            {
                "type": "event",
                "name": str(event.get("reason", "pod_event")),
                "value": str(event.get("note") or event.get("message") or ""),
                "labels": {"type": str(event.get("type", ""))},
            }
        )
    return evidence


def _kubectl_json(config: dict, args: list[str]) -> dict[str, Any]:
    _validate_args(args)
    command = ["kubectl", "--kubeconfig", config["kubeconfig_path"], *args]
    completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=config["request_timeouts"]["kubectl_seconds"])
    return json.loads(completed.stdout or "{}")


def _kubectl_top_pods(config: dict) -> dict[tuple[str, str], dict[str, int]]:
    command = ["kubectl", "--kubeconfig", config["kubeconfig_path"], "top", "pods", "-A", "--no-headers"]
    completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=config["request_timeouts"]["kubectl_seconds"])
    usage: dict[tuple[str, str], dict[str, int]] = {}
    for line in completed.stdout.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        namespace, name, _cpu, memory = parts[:4]
        usage[(namespace, name)] = {"memory_mib": _parse_memory_to_mib(memory)}
    return usage


def _parse_memory_to_mib(value: str) -> int:
    if value.endswith("Mi"):
        return int(value[:-2])
    if value.endswith("Gi"):
        return int(float(value[:-2]) * 1024)
    if value.endswith("Ki"):
        return max(1, int(int(value[:-2]) / 1024))
    return int(value)


def _validate_args(args: list[str]) -> None:
    if not args or args[0] not in ALLOWED_VERBS:
        raise ValueError("unsupported kubectl command")
