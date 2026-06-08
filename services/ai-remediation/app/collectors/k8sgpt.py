from __future__ import annotations

import json
import subprocess
from typing import Any, Iterable

from app.models.events import EvidenceItem, IncidentEvent


SUPPORTED_OUTPUT_LIST_KEYS = ("results", "items", "analysis", "findings")
SUPPRESSED_MESSAGE_FRAGMENTS = (
    "403 forbidden",
    "completed helm job",
    "expected argo drift",
    "expected drift",
)


def collect_namespace_advisories(config: dict, namespaces: Iterable[str]) -> dict[str, dict[str, Any]]:
    namespaces = sorted(set(namespaces))
    if not config["feature_flags"].get("enable_k8sgpt_collector", False):
        return {namespace: _disabled_payload(namespace) for namespace in namespaces}

    results: dict[str, dict[str, Any]] = {}
    allowed = set(config["k8sgpt"]["namespace_allowlist"])
    for namespace in namespaces:
        if namespace not in allowed:
            results[namespace] = _unavailable_payload(namespace, "namespace_not_allowed")
            continue
        results[namespace] = _run_namespace_analysis(config, namespace)
    return results


def collect_k8sgpt_findings(config: dict, namespaces: Iterable[str]) -> dict[str, dict[str, Any]]:
    return collect_namespace_advisories(config, namespaces)


def attach_advisory_evidence(
    incident: IncidentEvent,
    advisory: dict[str, Any] | None,
    *,
    max_evidence_items: int,
) -> tuple[IncidentEvent, dict[str, Any] | None]:
    if advisory is None:
        return incident, None

    matched = _match_findings(incident, advisory.get("findings", []))
    advisory["matched_findings"] = matched
    evidence = list(incident.evidence)

    if advisory.get("status") != "ok":
        evidence.append(
            EvidenceItem(
                type="advisor_status",
                name="advisory_unavailable",
                value=advisory.get("error") or advisory.get("status", "unavailable"),
                labels={"namespace": incident.namespace, "advisor": "k8sgpt"},
            )
        )
    elif matched:
        for finding in matched[:2]:
            evidence.append(
                EvidenceItem(
                    type="advisor",
                    name="k8sgpt_finding",
                    value=finding["message"],
                    labels={
                        "namespace": finding["namespace"],
                        "kind": finding["kind"],
                        "name": finding["name"],
                        "severity": finding["severity"],
                    },
                )
            )
    else:
        evidence.append(
            EvidenceItem(
                type="advisor_status",
                name="advisory_unavailable",
                value="no_matching_findings",
                labels={"namespace": incident.namespace, "advisor": "k8sgpt"},
            )
        )

    incident.evidence = evidence[:max_evidence_items]
    return incident, advisory


def _run_namespace_analysis(config: dict, namespace: str) -> dict[str, Any]:
    command = _build_command(config, namespace)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=int(config["k8sgpt"]["timeout_seconds"]),
        )
    except FileNotFoundError:
        return _unavailable_payload(namespace, "binary_not_found", command=command)
    except subprocess.TimeoutExpired:
        return _unavailable_payload(namespace, "timeout", command=command)
    except OSError as exc:
        return _unavailable_payload(namespace, f"os_error:{exc}", command=command)

    if completed.returncode != 0:
        error_text = _truncate_text((completed.stderr or completed.stdout or "").strip(), config) or f"exit_{completed.returncode}"
        return _unavailable_payload(namespace, error_text, command=command)

    stdout = completed.stdout or ""
    if len(stdout.encode("utf-8")) > int(config["k8sgpt"]["max_output_kb"]) * 1024:
        return _unavailable_payload(namespace, "output_too_large", command=command)

    try:
        payload = json.loads(stdout or "{}")
    except json.JSONDecodeError:
        return _unavailable_payload(namespace, "invalid_json", command=command)

    findings, suppressed = _normalize_findings(namespace, payload)
    return {
        "namespace": namespace,
        "status": "ok",
        "findings": findings,
        "suppressed_findings": suppressed,
        "error": None,
        "command": command,
        "raw_result_count": len(_extract_results(payload)),
    }


def _build_command(config: dict, namespace: str) -> list[str]:
    command = [
        str(config["k8sgpt"]["binary"]),
        "analyze",
        "--kubeconfig",
        str(config["k8sgpt"]["explicit_kubeconfig"]),
        "--namespace",
        namespace,
        "--output",
        "json",
    ]
    for item in config["k8sgpt"]["filters"]:
        command.extend(["--filter", str(item)])
    return command


def _normalize_findings(namespace: str, payload: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    for item in _extract_results(payload):
        finding = {
            "namespace": str(
                item.get("namespace")
                or item.get("resource", {}).get("namespace")
                or item.get("metadata", {}).get("namespace")
                or namespace
            ),
            "kind": str(item.get("kind") or item.get("resource", {}).get("kind") or item.get("object", {}).get("kind") or "Unknown"),
            "name": str(item.get("name") or item.get("resource", {}).get("name") or item.get("metadata", {}).get("name") or "unknown"),
            "message": _message_from_result(item),
            "severity": _normalize_severity(str(item.get("severity", "low"))),
        }
        if _is_suppressed(finding):
            suppressed.append(finding)
            continue
        findings.append(finding)
    return findings, suppressed


def _extract_results(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in SUPPORTED_OUTPUT_LIST_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        if {"kind", "name", "details"} & set(payload):
            return [payload]
    return []


def _message_from_result(item: dict[str, Any]) -> str:
    for key in ("details", "description", "message", "error", "text"):
        value = item.get(key)
        if value:
            return str(value).strip()
    return "K8sGPT returned a finding without a descriptive message."


def _normalize_severity(value: str) -> str:
    lowered = value.lower()
    if lowered in {"critical", "high", "medium", "low", "info"}:
        return lowered
    return "low"


def _is_suppressed(finding: dict[str, Any]) -> bool:
    message = finding["message"].lower()
    return any(fragment in message for fragment in SUPPRESSED_MESSAGE_FRAGMENTS)


def _match_findings(incident: IncidentEvent, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    exact = [
        finding
        for finding in findings
        if finding["namespace"] == incident.namespace
        and finding["kind"].lower() == incident.resource.kind.lower()
        and finding["name"] == incident.resource.name
    ]
    if exact:
        return exact

    namespace_matches = [finding for finding in findings if finding["namespace"] == incident.namespace]
    fuzzy = [
        finding
        for finding in namespace_matches
        if incident.resource.name in finding["name"] or finding["name"] in incident.resource.name
    ]
    return fuzzy or namespace_matches[:2]


def _disabled_payload(namespace: str) -> dict[str, Any]:
    return {
        "namespace": namespace,
        "status": "disabled",
        "findings": [],
        "suppressed_findings": [],
        "error": "collector_disabled",
        "command": [],
        "raw_result_count": 0,
    }


def _unavailable_payload(namespace: str, error: str, *, command: list[str] | None = None) -> dict[str, Any]:
    return {
        "namespace": namespace,
        "status": "unavailable",
        "findings": [],
        "suppressed_findings": [],
        "error": error,
        "command": command or [],
        "raw_result_count": 0,
    }


def _truncate_text(value: str, config: dict) -> str:
    max_bytes = max(64, int(config["k8sgpt"]["max_output_kb"]) * 1024)
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value
    return encoded[:max_bytes].decode("utf-8", errors="ignore") + "...[truncated]"
