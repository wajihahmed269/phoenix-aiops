from __future__ import annotations

import json
from typing import Callable
from wsgiref.simple_server import WSGIServer, make_server

from app.approval.store import ApprovalStore
from app.approval.workflow import approve_recommendation, latest_valid_approval, reject_recommendation, request_approval
from app.config.loader import load_config
from app.escalation.workflow import build_escalation_state
from app.models.factory import utc_now
from app.policies.loader import load_policy
from app.pipeline.poller import run_once
from app.recommendations.engine import analyze_event
from app.remediation.planner import generate_plan
from app.remediation.runner import execute_plan
from app.store.json_store import JsonRecommendationStore
from app.store.lifecycle import acknowledge_recommendation, set_recommendation_status, suppress_recommendation


def build_server(host: str = "127.0.0.1", port: int = 8081) -> WSGIServer:
    return make_server(host, port, application)


def application(environ: dict, start_response: Callable) -> list[bytes]:
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/")

    if method == "GET" and path == "/healthz":
        config = load_config()
        return _json_response(
            start_response,
            200,
            {
                "status": "ok",
                "service": "ai-remediation",
                "policy_version": load_policy()["version"],
                "cluster_name": config["cluster_name"],
                "storage_path": config["local_storage_path"],
                "time": utc_now(),
            },
        )

    if method == "GET" and path == "/v1/policies/current":
        return _json_response(start_response, 200, load_policy())

    if method == "GET" and path == "/v1/recommendations":
        store = _build_store()
        return _json_response(start_response, 200, {"items": [item.to_dict() for item in store.list_recommendations()]})

    if method == "POST" and path == "/v1/poll-once":
        config = load_config()
        return _json_response(start_response, 200, run_once(config).to_dict())

    if method == "POST" and path == "/v1/analyze":
        try:
            length = int(environ.get("CONTENT_LENGTH") or "0")
            raw_body = environ["wsgi.input"].read(length)
            payload = json.loads(raw_body or b"{}")
            recommendation = analyze_event(payload)
            return _json_response(start_response, 200, recommendation.to_dict())
        except ValueError as exc:
            return _json_response(start_response, 400, {"error": str(exc)})
        except KeyError as exc:
            return _json_response(start_response, 400, {"error": f"missing field: {exc.args[0]}"})
        except json.JSONDecodeError:
            return _json_response(start_response, 400, {"error": "invalid json"})

    route_match = _match_recommendation_route(path)
    if route_match:
        recommendation_id, action = route_match
        store = _build_store()
        approval_store = _build_approval_store()
        if method == "GET" and action is None:
            recommendation = store.get_recommendation(recommendation_id)
            if recommendation is None:
                return _json_response(start_response, 404, {"error": "recommendation not found"})
            return _json_response(start_response, 200, recommendation.to_dict())
        if method == "GET" and action == "plan":
            recommendation = store.get_recommendation(recommendation_id)
            if recommendation is None:
                return _json_response(start_response, 404, {"error": "recommendation not found"})
            try:
                return _json_response(start_response, 200, generate_plan(recommendation, load_config()).to_dict())
            except ValueError as exc:
                return _json_response(start_response, 400, {"error": str(exc)})
        if method == "GET" and action == "approval":
            recommendation = store.get_recommendation(recommendation_id)
            if recommendation is None:
                return _json_response(start_response, 404, {"error": "recommendation not found"})
            try:
                plan = generate_plan(recommendation, load_config())
            except ValueError as exc:
                return _json_response(start_response, 400, {"error": str(exc)})
            approval = approval_store.latest_for_plan(recommendation_id, plan.plan_id, plan.remediation_id, {"kind": plan.resource_kind, "name": plan.resource_name})
            if approval is None:
                return _json_response(start_response, 404, {"error": "approval not found"})
            return _json_response(start_response, 200, approval.to_dict())
        if method == "GET" and action == "escalation":
            recommendation = store.get_recommendation(recommendation_id)
            if recommendation is None:
                return _json_response(start_response, 404, {"error": "recommendation not found"})
            return _json_response(start_response, 200, build_escalation_state(recommendation, load_config()))
        if method == "POST" and action == "acknowledge":
            try:
                return _json_response(start_response, 200, acknowledge_recommendation(store, recommendation_id, load_config()).to_dict())
            except KeyError:
                return _json_response(start_response, 404, {"error": "recommendation not found"})
        if method == "POST" and action == "suppress":
            try:
                return _json_response(start_response, 200, suppress_recommendation(store, recommendation_id, "suppressed via API", load_config()).to_dict())
            except KeyError:
                return _json_response(start_response, 404, {"error": "recommendation not found"})
        if method == "POST" and action == "approval-request":
            recommendation = store.get_recommendation(recommendation_id)
            if recommendation is None:
                return _json_response(start_response, 404, {"error": "recommendation not found"})
            payload = _read_json_body(environ)
            try:
                plan = generate_plan(recommendation, load_config())
            except ValueError as exc:
                return _json_response(start_response, 400, {"error": str(exc)})
            record = request_approval(
                approval_store,
                store,
                recommendation,
                plan,
                requested_by=str(payload.get("requested_by", "operator")),
                reason=str(payload.get("reason", "human approval requested")),
                scope=str(payload.get("scope", "execute")),
                config=load_config(),
            )
            return _json_response(start_response, 200, record.to_dict())
        if method == "POST" and action == "approve":
            recommendation = store.get_recommendation(recommendation_id)
            if recommendation is None:
                return _json_response(start_response, 404, {"error": "recommendation not found"})
            payload = _read_json_body(environ)
            try:
                plan = generate_plan(recommendation, load_config())
            except ValueError as exc:
                return _json_response(start_response, 400, {"error": str(exc)})
            try:
                record = approve_recommendation(
                    approval_store,
                    store,
                    recommendation,
                    plan,
                    approver=str(payload.get("approver", "operator")),
                    reason=str(payload.get("reason", "approved")),
                    config=load_config(),
                )
            except KeyError:
                return _json_response(start_response, 404, {"error": "approval request not found"})
            return _json_response(start_response, 200, record.to_dict())
        if method == "POST" and action == "reject":
            recommendation = store.get_recommendation(recommendation_id)
            if recommendation is None:
                return _json_response(start_response, 404, {"error": "recommendation not found"})
            payload = _read_json_body(environ)
            try:
                plan = generate_plan(recommendation, load_config())
            except ValueError as exc:
                return _json_response(start_response, 400, {"error": str(exc)})
            try:
                record = reject_recommendation(
                    approval_store,
                    store,
                    recommendation,
                    plan,
                    approver=str(payload.get("approver", "operator")),
                    reason=str(payload.get("reason", "rejected")),
                    config=load_config(),
                )
            except KeyError:
                return _json_response(start_response, 404, {"error": "approval request not found"})
            return _json_response(start_response, 200, record.to_dict())
        if method == "POST" and action == "execute":
            recommendation = store.get_recommendation(recommendation_id)
            if recommendation is None:
                return _json_response(start_response, 404, {"error": "recommendation not found"})
            config = load_config()
            payload = _read_json_body(environ)
            try:
                plan = generate_plan(recommendation, config)
            except ValueError as exc:
                return _json_response(start_response, 400, {"error": str(exc)})
            approval = latest_valid_approval(approval_store, recommendation_id, plan)
            result = execute_plan(plan, recommendation, config, approval=approval, explicit_execute=bool(payload.get("explicit_execute", False)))
            if result.success:
                set_recommendation_status(store, recommendation_id, "executed", config=config, reason=result.mode)
                if result.verification.get("success"):
                    set_recommendation_status(store, recommendation_id, "verified", config=config, reason=result.mode)
            return _json_response(start_response, 200, result.to_dict())

    return _json_response(start_response, 404, {"error": "not found"})


def _build_store() -> JsonRecommendationStore:
    config = load_config()
    return JsonRecommendationStore(config["local_storage_path"])


def _build_approval_store() -> ApprovalStore:
    config = load_config()
    return ApprovalStore(config["approval_storage_path"])


def _match_recommendation_route(path: str) -> tuple[str, str | None] | None:
    prefix = "/v1/recommendations/"
    if not path.startswith(prefix):
        return None
    remainder = path[len(prefix) :]
    if not remainder:
        return None
    parts = [part for part in remainder.split("/") if part]
    if len(parts) == 1:
        return parts[0], None
    if len(parts) == 2 and parts[1] in {"acknowledge", "suppress", "plan", "approval", "approval-request", "approve", "reject", "execute", "escalation"}:
        return parts[0], parts[1]
    return None


def _read_json_body(environ: dict) -> dict:
    length = int(environ.get("CONTENT_LENGTH") or "0")
    raw_body = environ["wsgi.input"].read(length)
    if not raw_body:
        return {}
    return json.loads(raw_body)


def _json_response(start_response: Callable, status_code: int, payload: dict) -> list[bytes]:
    body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    status_text = {
        200: "200 OK",
        400: "400 Bad Request",
        404: "404 Not Found",
    }[status_code]
    headers = [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(body))),
    ]
    start_response(status_text, headers)
    return [body]
