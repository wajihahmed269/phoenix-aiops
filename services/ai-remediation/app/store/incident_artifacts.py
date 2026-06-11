from __future__ import annotations

import json
import re
from pathlib import Path
from threading import Lock
from typing import Any

from app.models.events import IncidentEvent
from app.models.recommendation import Recommendation


class IncidentArtifactStore:
    ALLOWED_FILES = {
        "summary.md",
        "timeline.md",
        "recommendation.json",
        "evidence.json",
        "k8sgpt.json",
        "notifications.log",
        "execution-audit.json",
    }

    def __init__(self, root_path: str, limits: dict[str, int] | None = None) -> None:
        self.root_path = Path(root_path)
        self.root_path.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._limits = limits or {
            "max_json_bytes": 262144,
            "max_text_bytes": 65536,
            "max_timeline_entries": 2000,
            "timeline_summary_entries": 5,
            "max_notification_log_bytes": 65536,
        }

    def append_timeline(self, incident_id: str, *, timestamp: str, stage: str, message: str) -> None:
        _ = stage
        path = self._incident_dir(incident_id) / "timeline.md"
        line = f"[{timestamp}]\n{self._sanitize_text(message)}\n\n"
        with self._lock:
            if self._line_count(path) >= int(self._limits["max_timeline_entries"]) * 3:
                return
            if path.exists() and path.stat().st_size >= int(self._limits["max_text_bytes"]):
                return
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line)

    def persist_evidence(self, incident_id: str, incident: IncidentEvent, advisory: dict | None) -> None:
        payload = {
            "event_id": incident.event_id,
            "scenario": incident.scenario,
            "observed_at": incident.observed_at,
            "namespace": incident.namespace,
            "resource": {"kind": incident.resource.kind, "name": incident.resource.name},
            "evidence": [self._evidence_to_dict(item) for item in incident.evidence],
        }
        self.write_json(incident_id, "evidence.json", payload)
        self.write_json(incident_id, "k8sgpt.json", advisory or {"status": "unavailable", "error": "not_run"})

    def persist_recommendation(self, incident_id: str, recommendation: Recommendation) -> None:
        self.write_json(incident_id, "recommendation.json", recommendation.to_dict())

    def persist_summary(self, incident_id: str, summary: str) -> None:
        self.write_text(incident_id, "summary.md", summary.rstrip() + "\n")

    def append_notification_log(self, incident_id: str, *, timestamp: str, result: dict[str, Any]) -> None:
        path = self._safe_artifact_path(incident_id, "notifications.log")
        line = json.dumps(
            {
                "timestamp": timestamp,
                "provider": result.get("provider"),
                "mode": result.get("mode"),
                "success": result.get("success"),
                "attempts": result.get("attempts"),
                "status_code": result.get("status_code"),
                "detail": self._sanitize_text(str(result.get("detail", ""))),
            },
            sort_keys=True,
        )
        with self._lock:
            if path.exists() and path.stat().st_size >= int(self._limits["max_notification_log_bytes"]):
                return
            with path.open("a", encoding="utf-8") as handle:
                handle.write(self._truncate_text(line, max_bytes=int(self._limits["max_notification_log_bytes"]) // 4) + "\n")

    def write_json(self, incident_id: str, filename: str, payload: Any) -> None:
        path = self._safe_artifact_path(incident_id, filename)
        text = json.dumps(self._sanitize_object(payload), indent=2, sort_keys=True)
        if len(text.encode("utf-8")) > int(self._limits["max_json_bytes"]):
            text = json.dumps(
                {
                    "status": "truncated",
                    "reason": "artifact exceeded max_json_bytes",
                    "excerpt": self._truncate_text(text, max_bytes=int(self._limits["max_json_bytes"]) // 2),
                },
                indent=2,
                sort_keys=True,
            )
        with self._lock:
            path.write_text(text, encoding="utf-8")

    def write_text(self, incident_id: str, filename: str, payload: str) -> None:
        path = self._safe_artifact_path(incident_id, filename)
        with self._lock:
            path.write_text(self._truncate_text(self._sanitize_text(payload), max_bytes=int(self._limits["max_text_bytes"])), encoding="utf-8")

    def artifact_dir(self, incident_id: str) -> str:
        return str(self._incident_dir(incident_id))

    def _incident_dir(self, incident_id: str) -> Path:
        safe_incident_id = self._sanitize_incident_id(incident_id)
        path = (self.root_path / safe_incident_id).resolve()
        root = self.root_path.resolve()
        if root not in path.parents and path != root:
            raise ValueError("incident artifact path escaped root")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _safe_artifact_path(self, incident_id: str, filename: str) -> Path:
        if Path(filename).name != filename or filename not in self.ALLOWED_FILES:
            raise ValueError(f"unsafe artifact filename: {filename}")
        return self._incident_dir(incident_id) / filename

    def _evidence_to_dict(self, item: Any) -> dict[str, Any]:
        return {
            "type": item.type,
            "name": self._sanitize_text(str(item.name)),
            "value": self._sanitize_object(item.value),
            "labels": self._sanitize_object(item.labels),
        }

    def _sanitize_incident_id(self, incident_id: str) -> str:
        sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", incident_id).strip("-.")
        return sanitized or "incident"

    def _sanitize_object(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._sanitize_object(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._sanitize_object(item) for item in value]
        if isinstance(value, str):
            return self._sanitize_text(value)
        return value

    def _sanitize_text(self, value: str) -> str:
        redacted = re.sub(r"(?i)\b(password|token|secret|api[_-]?key)\b\s*[:=]\s*[^\s]+", r"\1=[redacted]", value)
        return self._truncate_text(redacted, max_bytes=int(self._limits["max_text_bytes"]) // 2)

    def _truncate_text(self, value: str, *, max_bytes: int) -> str:
        encoded = value.encode("utf-8")
        if len(encoded) <= max_bytes:
            return value
        return encoded[:max_bytes].decode("utf-8", errors="ignore") + "...[truncated]"

    def _line_count(self, path: Path) -> int:
        if not path.exists():
            return 0
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for _ in handle)
