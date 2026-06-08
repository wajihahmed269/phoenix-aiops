from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pathlib import Path
import tempfile
import unittest

from app.models.recommendation import ActionProposal, Recommendation
from app.pipeline.dedupe import evaluate_recommendation
from app.store.json_store import JsonRecommendationStore


class StoreAndDedupeTests(unittest.TestCase):
    def test_store_save_get_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = JsonRecommendationStore(str(Path(tmpdir) / "recommendations.jsonl"))
            recommendation = _sample_recommendation()
            store.save_recommendation(recommendation)
            fetched = store.get_recommendation(recommendation.recommendation_id)
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched.summary, recommendation.summary)
            updated = store.update_status(recommendation.recommendation_id, "acknowledged", updated_at="2026-06-08T12:10:00Z")
            self.assertEqual(updated.status, "acknowledged")

    def test_dedupe_cooldown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = JsonRecommendationStore(str(Path(tmpdir) / "recommendations.jsonl"))
            first = _sample_recommendation()
            first.labels["scenario"] = "target_down"
            store.save_recommendation(first)
            second = _sample_recommendation(recommendation_id="rec-2", event_id="evt-2", created_at="2026-06-08T12:05:00Z")
            second.labels["scenario"] = "target_down"
            decision = evaluate_recommendation(
                store,
                second,
                {"cooldowns": {"default_minutes": 15, "known_limitation_minutes": 360}},
                {"cooldowns": {"same_recommendation_minutes": 15, "known_limitation_minutes": 360}},
            )
            self.assertFalse(decision.allow)
            self.assertTrue(decision.cooldown_applied)


def _sample_recommendation(
    recommendation_id: str = "rec-1",
    event_id: str = "evt-1",
    created_at: str = "2026-06-08T12:00:00Z",
) -> Recommendation:
    return Recommendation(
        recommendation_id=recommendation_id,
        incident_id="inc-test-001",
        event_id=event_id,
        source="prometheus",
        cluster="phoenix-oci-k3s",
        namespace="observability",
        resource={"kind": "ScrapeTarget", "name": "kubernetes-kubelet"},
        severity="low",
        summary="Prometheus target down: kubernetes-kubelet",
        rationale="test rationale",
        evidence=[],
        confidence=0.7,
        risk_score=25,
        suggested_actions=[ActionProposal("query_metrics", "inspect", None)],
        requires_human_approval=True,
        rollback_hint="none",
        policy_decision={"known_limitation": False},
        analyzer="test",
        created_at=created_at,
        labels={"scenario": "target_down"},
    )


if __name__ == "__main__":
    unittest.main()
