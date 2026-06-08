from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config.loader import load_config
from app.approval.store import ApprovalStore
from app.approval.workflow import approve_recommendation, reject_recommendation, request_approval
from app.escalation.workflow import build_escalation_state
from app.models.factory import utc_now
from app.pipeline.poller import run_once
from app.policies.loader import load_policy
from app.recommendations.engine import analyze_event
from app.remediation.planner import generate_plan
from app.remediation.runner import execute_plan
from app.store.json_store import JsonRecommendationStore
from app.store.lifecycle import acknowledge_recommendation, suppress_recommendation


def main() -> None:
    parser = argparse.ArgumentParser(description="Phoenix-Ops AI remediation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("health")
    subparsers.add_parser("analyze-sample")
    subparsers.add_parser("poll-once")
    subparsers.add_parser("list-recommendations")

    build_plan = subparsers.add_parser("build-plan")
    build_plan.add_argument("recommendation_id")

    approval_request = subparsers.add_parser("request-approval")
    approval_request.add_argument("recommendation_id")
    approval_request.add_argument("--requested-by", default="operator")
    approval_request.add_argument("--reason", default="human approval requested")

    approve = subparsers.add_parser("approve")
    approve.add_argument("recommendation_id")
    approve.add_argument("--approver", default="operator")
    approve.add_argument("--reason", default="approved")

    reject = subparsers.add_parser("reject")
    reject.add_argument("recommendation_id")
    reject.add_argument("--approver", default="operator")
    reject.add_argument("--reason", default="rejected")

    execute = subparsers.add_parser("execute")
    execute.add_argument("recommendation_id")
    execute.add_argument("--explicit-execute", action="store_true")

    escalation = subparsers.add_parser("escalation")
    escalation.add_argument("recommendation_id")

    acknowledge = subparsers.add_parser("acknowledge")
    acknowledge.add_argument("recommendation_id")

    suppress = subparsers.add_parser("suppress")
    suppress.add_argument("recommendation_id")
    suppress.add_argument("--reason", default="operator suppressed")

    args = parser.parse_args()
    config = load_config()
    store = JsonRecommendationStore(config["local_storage_path"])
    approval_store = ApprovalStore(config["approval_storage_path"])

    if args.command == "health":
        print(json.dumps({"status": "ok", "time": utc_now(), "policy_version": load_policy()["version"]}, indent=2))
        return

    if args.command == "analyze-sample":
        sample = {
            "event_id": "evt-sample",
            "source": "prometheus",
            "scenario": "target_down",
            "cluster": config["cluster_name"],
            "namespace": "observability",
            "resource": {"kind": "ScrapeTarget", "name": "kubernetes-kubelet"},
            "observed_at": utc_now(),
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
        print(json.dumps(analyze_event(sample).to_dict(), indent=2, sort_keys=True))
        return

    if args.command == "poll-once":
        print(json.dumps(run_once(config).to_dict(), indent=2, sort_keys=True))
        return

    if args.command == "list-recommendations":
        print(json.dumps([item.to_dict() for item in store.list_recommendations()], indent=2, sort_keys=True))
        return

    if args.command == "build-plan":
        recommendation = store.get_recommendation(args.recommendation_id)
        if recommendation is None:
            raise KeyError(args.recommendation_id)
        print(json.dumps(generate_plan(recommendation, config).to_dict(), indent=2, sort_keys=True))
        return

    if args.command == "request-approval":
        recommendation = store.get_recommendation(args.recommendation_id)
        if recommendation is None:
            raise KeyError(args.recommendation_id)
        plan = generate_plan(recommendation, config)
        print(json.dumps(request_approval(approval_store, store, recommendation, plan, requested_by=args.requested_by, reason=args.reason, config=config).to_dict(), indent=2, sort_keys=True))
        return

    if args.command == "approve":
        recommendation = store.get_recommendation(args.recommendation_id)
        if recommendation is None:
            raise KeyError(args.recommendation_id)
        plan = generate_plan(recommendation, config)
        print(json.dumps(approve_recommendation(approval_store, store, recommendation, plan, approver=args.approver, reason=args.reason, config=config).to_dict(), indent=2, sort_keys=True))
        return

    if args.command == "reject":
        recommendation = store.get_recommendation(args.recommendation_id)
        if recommendation is None:
            raise KeyError(args.recommendation_id)
        plan = generate_plan(recommendation, config)
        print(json.dumps(reject_recommendation(approval_store, store, recommendation, plan, approver=args.approver, reason=args.reason, config=config).to_dict(), indent=2, sort_keys=True))
        return

    if args.command == "execute":
        recommendation = store.get_recommendation(args.recommendation_id)
        if recommendation is None:
            raise KeyError(args.recommendation_id)
        from app.approval.workflow import latest_valid_approval

        plan = generate_plan(recommendation, config)
        approval = latest_valid_approval(approval_store, args.recommendation_id, plan)
        result = execute_plan(plan, recommendation, config, approval=approval, explicit_execute=args.explicit_execute)
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return

    if args.command == "escalation":
        recommendation = store.get_recommendation(args.recommendation_id)
        if recommendation is None:
            raise KeyError(args.recommendation_id)
        print(json.dumps(build_escalation_state(recommendation, config), indent=2, sort_keys=True))
        return

    if args.command == "acknowledge":
        print(json.dumps(acknowledge_recommendation(store, args.recommendation_id, config).to_dict(), indent=2, sort_keys=True))
        return

    if args.command == "suppress":
        print(json.dumps(suppress_recommendation(store, args.recommendation_id, args.reason, config).to_dict(), indent=2, sort_keys=True))
        return


if __name__ == "__main__":
    main()
