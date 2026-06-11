from __future__ import annotations

from datetime import UTC, datetime

from app.models.recommendation import Recommendation


def build_escalation_state(recommendation: Recommendation, config: dict, *, now: str | None = None) -> dict:
    current = _parse_time(now or recommendation.created_at)
    created = _parse_time(recommendation.created_at)
    age_minutes = int((current - created).total_seconds() / 60)
    timings = config["remediation"]["escalation_minutes"]
    stage = "t0_initial_recommendation"
    if age_minutes >= timings["t15"]:
        stage = "t15_bounded_execution_candidate"
    elif age_minutes >= timings["t10"]:
        stage = "t10_prepare_fallback_candidates"
    elif age_minutes >= timings["t5"]:
        stage = "t5_escalation_summary_update"
    elif age_minutes >= timings["t1"]:
        stage = "t1_k8sgpt_and_human_summary"
    return {
        "recommendation_id": recommendation.recommendation_id,
        "incident_id": recommendation.incident_id,
        "age_minutes": age_minutes,
        "stage": stage,
        "execution_state": "disabled",
        "approval_required": recommendation.requires_human_approval,
        "approval_state": "human_approval_required" if recommendation.requires_human_approval else "not_required",
        "fallback_candidate_allowed": age_minutes >= timings["t10"],
        "bounded_execution_window_open": age_minutes >= timings["t15"],
    }


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
