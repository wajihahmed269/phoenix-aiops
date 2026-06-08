from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config.loader import load_config
from app.models.factory import utc_now
from app.pipeline.poller import run_once
from app.policies.loader import load_policy
from app.recommendations.engine import analyze_event
from app.store.json_store import JsonRecommendationStore
from app.store.lifecycle import acknowledge_recommendation, suppress_recommendation


def main() -> None:
    parser = argparse.ArgumentParser(description="Phoenix-Ops AI remediation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("health")
    subparsers.add_parser("analyze-sample")
    subparsers.add_parser("poll-once")
    subparsers.add_parser("list-recommendations")

    acknowledge = subparsers.add_parser("acknowledge")
    acknowledge.add_argument("recommendation_id")

    suppress = subparsers.add_parser("suppress")
    suppress.add_argument("recommendation_id")
    suppress.add_argument("--reason", default="operator suppressed")

    args = parser.parse_args()
    config = load_config()
    store = JsonRecommendationStore(config["local_storage_path"])

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

    if args.command == "acknowledge":
        print(json.dumps(acknowledge_recommendation(store, args.recommendation_id).to_dict(), indent=2, sort_keys=True))
        return

    if args.command == "suppress":
        print(json.dumps(suppress_recommendation(store, args.recommendation_id, args.reason).to_dict(), indent=2, sort_keys=True))
        return


if __name__ == "__main__":
    main()
