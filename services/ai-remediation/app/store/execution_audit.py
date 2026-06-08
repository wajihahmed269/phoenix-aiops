from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any


class ExecutionAuditStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def append(self, payload: dict[str, Any]) -> dict[str, Any]:
        record = json.dumps(payload, sort_keys=True)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(record + "\n")
        return payload

    def list_records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
        return records

    def latest_for_plan(self, plan_id: str) -> dict[str, Any] | None:
        matching = [item for item in self.list_records() if item.get("plan_id") == plan_id]
        if not matching:
            return None
        return max(matching, key=lambda item: item.get("finished_at") or item.get("started_at") or "")
