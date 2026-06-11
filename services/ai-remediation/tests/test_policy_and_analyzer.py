from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import unittest

from app.models.events import IncidentEvent
from app.policies.loader import load_policy
from app.recommendations.engine import analyze_event


class PolicyAndAnalyzerTests(unittest.TestCase):
    def test_known_limitation_suppression(self) -> None:
        recommendation = analyze_event(
            {
                "event_id": "evt-001",
                "source": "prometheus",
                "scenario": "target_down",
                "cluster": "phoenix-oci-k3s",
                "namespace": "observability",
                "resource": {"kind": "ScrapeTarget", "name": "kubernetes-kubelet"},
                "observed_at": "2026-06-08T12:00:00Z",
                "severity_hint": "low",
                "summary": "Prometheus target is down",
                "evidence": [
                    {
                        "type": "metric",
                        "name": "up",
                        "value": 0,
                        "labels": {"job": "kubernetes-kubelet", "lastError": "server returned HTTP status 403 Forbidden"},
                    }
                ],
            }
        )
        self.assertEqual(recommendation.severity, "info")
        self.assertTrue(recommendation.policy_decision["known_limitation"])

    def test_invalid_scenario_rejected(self) -> None:
        with self.assertRaises(ValueError):
            IncidentEvent.from_dict(
                {
                    "event_id": "evt-002",
                    "source": "test",
                    "scenario": "bad_scenario",
                    "cluster": "phoenix",
                    "namespace": "bankapp",
                    "resource": {"kind": "Pod", "name": "x"},
                    "observed_at": "2026-06-08T12:00:00Z",
                    "severity_hint": "low",
                    "summary": "bad",
                    "evidence": [],
                }
            )

    def test_policy_version_loads(self) -> None:
        policy = load_policy()
        self.assertIn("version", policy)


if __name__ == "__main__":
    unittest.main()
