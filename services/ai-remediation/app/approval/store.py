from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from app.approval.models import ApprovalRecord


class ApprovalStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def save(self, record: ApprovalRecord) -> ApprovalRecord:
        payload = json.dumps(record.to_dict(), sort_keys=True)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(payload + "\n")
        return record

    def list_records(self) -> list[ApprovalRecord]:
        if not self.path.exists():
            return []
        records: list[ApprovalRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                records.append(ApprovalRecord.from_dict(json.loads(line)))
        return sorted(records, key=lambda item: item.requested_at)

    def latest_for_plan(self, recommendation_id: str, plan_id: str, remediation_id: str, resource: dict[str, str]) -> ApprovalRecord | None:
        records = [
            item
            for item in self.list_records()
            if item.recommendation_id == recommendation_id
            and item.plan_id == plan_id
            and item.remediation_id == remediation_id
            and item.resource == resource
        ]
        if not records:
            return None
        status_rank = {"requested": 1, "rejected": 2, "approved": 3, "expired": 4}
        return max(records, key=lambda item: (item.decided_at or item.requested_at, status_rank.get(item.status, 0)))
