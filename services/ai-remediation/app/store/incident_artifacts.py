from __future__ import annotations

import json
import re
from pathlib import Path
from threading import Lock
from typing import Any

from app.models.events import IncidentEvent
from app.models.recommendation import Recommendation


class IncidentArtifactStore:
    def __init__(self, root_path: str) -> None:
        self.root_path = Path(root_path)
        self.root_path.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def append_timeline(self, incident_id: str, *, timestamp: str, stage: str, message: str) -> None:
        path = self._incident_dir(incident_id) / "timeline.md"
        line = f"- {timestamp} [{stage}] {message}\n"
        with self._lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line)

    def persist_evidence(self, incident_id: str, incident: IncidentEvent, advisory: dict | None) -> None:
        metrics = [self._evidence_to_dict(item) for item in incident.evidence if item.type == "metric"]
        log_lines = [
            f"[{item.type}] {item.name}: {item.value}"
            for item in incident.evidence
            if item.type in {"log", "event", "advisor", "advisor_status"}
        ]
        if advisory:
            self.write_json(incident_id, "k8sgpt-analysis.json", advisory)
        self.write_json(incident_id, "metrics.json", metrics)
        self.write_text(incident_id, "logs.txt", "\n".join(log_lines).strip() + ("\n" if log_lines else ""))

    def persist_recommendation(self, incident_id: str, recommendation: Recommendation) -> None:
        self.write_json(incident_id, "recommendations.json", recommendation.to_dict())

    def persist_summary(self, incident_id: str, summary: str) -> None:
        self.write_text(incident_id, "incident-summary.md", summary.rstrip() + "\n")

    def write_json(self, incident_id: str, filename: str, payload: Any) -> None:
        path = self._safe_artifact_path(incident_id, filename)
        with self._lock:
            path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def write_text(self, incident_id: str, filename: str, payload: str) -> None:
        path = self._safe_artifact_path(incident_id, filename)
        with self._lock:
            path.write_text(payload, encoding="utf-8")

    def artifact_dir(self, incident_id: str) -> str:
        return str(self._incident_dir(incident_id))

    def _incident_dir(self, incident_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", incident_id):
            raise ValueError(f"unsafe incident_id: {incident_id}")
        path = (self.root_path / incident_id).resolve()
        root = self.root_path.resolve()
        if root not in path.parents and path != root:
            raise ValueError("incident artifact path escaped root")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _safe_artifact_path(self, incident_id: str, filename: str) -> Path:
        if Path(filename).name != filename:
            raise ValueError(f"unsafe artifact filename: {filename}")
        return self._incident_dir(incident_id) / filename

    def _evidence_to_dict(self, item: Any) -> dict[str, Any]:
        return {
            "type": item.type,
            "name": item.name,
            "value": item.value,
            "labels": item.labels,
        }
