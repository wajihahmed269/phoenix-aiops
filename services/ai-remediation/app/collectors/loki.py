from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime, timedelta

from app.models.events import IncidentEvent
from app.models.factory import create_incident_event


ERROR_PATTERN = re.compile(r"(?i)(error|exception|traceback|failed|timeout|refused|denied)")
PROBE_NOISE_PATTERN = re.compile(r'(?i)(kube-probe|GET / HTTP/1\.1"|/ready|/health|/live|/metrics)')
SECRET_PATTERN = re.compile(r"(?i)(password|token|secret|apikey|api_key)[=:][^\\s]+")


def collect_log_anomaly_events(config: dict) -> list[IncidentEvent]:
    events: list[IncidentEvent] = []
    start_ns = str(int((datetime.now(UTC) - timedelta(minutes=config["max_log_window_minutes"])).timestamp() * 1_000_000_000))
    end_ns = str(int(datetime.now(UTC).timestamp() * 1_000_000_000))

    for namespace in config["namespace_allowlist"]:
        query = f'{{namespace="{namespace}"}} |~ "(?i)(error|exception|traceback|failed|timeout|refused|denied)"'
        url = (
            _base_url(config["loki_url"])
            + "loki/api/v1/query_range?"
            + urllib.parse.urlencode(
                {
                    "query": query,
                    "start": start_ns,
                    "end": end_ns,
                    "limit": config["max_log_lines"],
                    "direction": "BACKWARD",
                }
            )
        )
        payload = _http_get_json(url, timeout=config["request_timeouts"]["http_seconds"])
        streams = payload.get("data", {}).get("result", [])
        messages = _extract_messages(streams)
        grouped = Counter(_normalize_message(message) for message in messages if _is_signal(message))
        for normalized, count in grouped.items():
            if count < 2:
                continue
            sample_stream = streams[0].get("stream", {}) if streams else {}
            events.append(
                create_incident_event(
                    source="loki",
                    scenario="log_anomaly",
                    cluster=config["cluster_name"],
                    namespace=namespace,
                    resource_kind="PodLogStream",
                    resource_name=sample_stream.get("pod", namespace),
                    severity_hint="medium" if count >= 5 else "low",
                    summary=f"Repeated error-like log pattern detected in {namespace}",
                    evidence=[
                        {
                            "type": "log",
                            "name": "repeated_message",
                            "value": normalized,
                            "labels": {
                                "namespace": namespace,
                                "count": str(count),
                                "container": str(sample_stream.get("container", "")),
                            },
                        }
                    ],
                    max_evidence_items=config["max_evidence_items"],
                )
            )
    return events


def _extract_messages(streams: list[dict]) -> list[str]:
    messages: list[str] = []
    for stream in streams:
        for value in stream.get("values", []):
            if len(value) >= 2:
                messages.append(str(value[1]))
    return messages


def _is_signal(message: str) -> bool:
    return bool(ERROR_PATTERN.search(message)) and not PROBE_NOISE_PATTERN.search(message)


def _normalize_message(message: str) -> str:
    sanitized = SECRET_PATTERN.sub(r"\1=<redacted>", message)
    sanitized = re.sub(r"\b[0-9a-f]{32,}\b", "<redacted>", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"\d+", "<n>", sanitized)
    return sanitized[:300]


def _http_get_json(url: str, timeout: int) -> dict:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.URLError as exc:
        raise RuntimeError(f"loki collector request failed: {exc}") from exc


def _base_url(url: str) -> str:
    return url.rstrip("/") + "/"
