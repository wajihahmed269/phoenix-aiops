from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from app.models.events import IncidentEvent
from app.models.factory import create_incident_event


def collect_target_down_events(config: dict) -> list[IncidentEvent]:
    url = urllib.parse.urljoin(_base_url(config["prometheus_url"]), "/api/v1/targets")
    payload = _http_get_json(url, timeout=config["request_timeouts"]["http_seconds"])
    events: list[IncidentEvent] = []

    for target in payload.get("data", {}).get("activeTargets", []):
        if target.get("health") == "up":
            continue
        labels = target.get("labels", {})
        namespace = labels.get("namespace", "observability")
        resource_name = labels.get("job") or labels.get("instance") or target.get("scrapeUrl", "unknown-target")
        summary = f"Prometheus target down: {resource_name}"
        evidence = [
            {
                "type": "metric",
                "name": "up",
                "value": 0,
                "labels": {
                    "job": str(labels.get("job", "")),
                    "scrapeUrl": str(target.get("scrapeUrl", "")),
                    "lastError": str(target.get("lastError", "")),
                },
            }
        ]
        events.append(
            create_incident_event(
                source="prometheus",
                scenario="target_down",
                cluster=config["cluster_name"],
                namespace=namespace,
                resource_kind="ScrapeTarget",
                resource_name=resource_name,
                severity_hint="low",
                summary=summary,
                evidence=evidence,
                max_evidence_items=config["max_evidence_items"],
            )
        )
    return events


def _http_get_json(url: str, timeout: int) -> dict:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.URLError as exc:
        raise RuntimeError(f"prometheus collector request failed: {exc}") from exc


def _base_url(url: str) -> str:
    return url.rstrip("/") + "/"
