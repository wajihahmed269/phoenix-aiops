from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_policy() -> dict[str, Any]:
    policy_path = Path(__file__).with_name("default_policy.json")
    with policy_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
