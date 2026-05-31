from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from edd_agent_lab.api.builder import create_app


def test_runtime_reports_generation_config(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(create_app())

    response = client.get("/api/runtime")

    assert response.status_code == 200
    generation = response.json()["generation"]
    assert generation["default_mode"] == "auto"
    assert generation["resolved_mode"] == "mock"
    assert generation["live_available"] is False
    assert generation["model"]


def test_stream_action_returns_progress_events(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)
    client = TestClient(create_app())

    created = client.post(
        "/api/drafts",
        json={
            "name": "Contract Review Agent",
            "description": "Review contract clauses and surface negotiation risks.",
        },
    )
    assert created.status_code == 200

    streamed = client.post("/api/drafts/contract-review-agent/actions/design/stream")
    assert streamed.status_code == 200

    events = [json.loads(line) for line in streamed.text.splitlines()]

    assert [event["phase"] for event in events] == [
        "starting",
        "running",
        "artifact",
        "artifact",
        "artifact",
        "artifact",
        "artifact",
        "artifact",
        "completed",
    ]
    assert events[0]["step_id"] == "behavior_rules"
    assert events[0]["retry_action"] == "design"
    assert events[0]["retryable"] is True
    assert events[1]["message"] == "Generating design artifacts."
    assert events[2]["artifact_id"] == "behavior_rules"
    assert events[2]["file"] == "behavior-rules.yaml"
    assert events[-1]["retryable"] is False
    assert events[-1]["draft"]["status"]["completed"] == 2
    assert "behavior_rules" in events[-1]["draft"]["artifact_sources"]
    assert events[-1]["draft"]["artifact_validations"]["behavior_rules"]["valid"] is True


def test_stream_action_returns_retryable_failure(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)
    client = TestClient(create_app())

    created = client.post(
        "/api/drafts",
        json={
            "name": "Contract Review Agent",
            "description": "Review contract clauses and surface negotiation risks.",
        },
    )
    assert created.status_code == 200

    streamed = client.post("/api/drafts/contract-review-agent/actions/run-v0/stream")
    assert streamed.status_code == 200

    events = [json.loads(line) for line in streamed.text.splitlines()]

    assert [event["phase"] for event in events] == ["starting", "running", "failed"]
    assert events[-1]["step_id"] == "v0_run"
    assert events[-1]["retry_action"] == "run-v0"
    assert events[-1]["retryable"] is True
    assert "Draft scenario not found" in events[-1]["message"]


def test_update_target_returns_refreshed_draft(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)
    client = TestClient(create_app())

    created = client.post(
        "/api/drafts",
        json={
            "name": "Contract Review Agent",
            "description": "Review contract clauses.",
        },
    )
    assert created.status_code == 200

    updated = client.put(
        "/api/drafts/contract-review-agent/target",
        json={
            "name": "Contract Risk Review Agent",
            "purpose": "Review risky contract clauses.",
            "risk_tolerance": "low",
            "expected_output_format": "risk summary",
        },
    )

    assert updated.status_code == 200
    target = updated.json()["target"]["agent_target"]
    assert target["name"] == "Contract Risk Review Agent"
    assert target["purpose"] == "Review risky contract clauses."
    assert target["risk_tolerance"] == "low"
    assert target["expected_output_format"] == "risk summary"
    assert "risk summary" in updated.json()["artifact_sources"]["target"]


def test_stream_run_action_accepts_generation_mode(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)
    client = TestClient(create_app())

    created = client.post(
        "/api/drafts",
        json={
            "name": "Contract Review Agent",
            "description": "Review contract clauses and surface negotiation risks.",
        },
    )
    assert created.status_code == 200
    assert client.post("/api/drafts/contract-review-agent/design").status_code == 200
    assert (
        client.post(
            "/api/drafts/contract-review-agent/scenario",
            json={"problem": "Review risky payment terms."},
        ).status_code
        == 200
    )

    streamed = client.post(
        "/api/drafts/contract-review-agent/actions/run-v0/stream?generation_mode=mock"
    )
    assert streamed.status_code == 200

    events = [json.loads(line) for line in streamed.text.splitlines()]

    assert events[1]["message"] == "Running v0 candidate. Generation mode: mock."
    assert events[-1]["draft"]["artifacts"]["v0_run"]["run"]["generation_mode"] == "mock"


def test_stream_publish_action_returns_publish_result(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.ui import workspace_store

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)
    client = TestClient(create_app())

    created = client.post(
        "/api/drafts",
        json={
            "name": "Contract Review Agent",
            "description": "Review contract clauses and surface negotiation risks.",
        },
    )
    assert created.status_code == 200

    assert client.post("/api/drafts/contract-review-agent/design").status_code == 200
    assert (
        client.post(
            "/api/drafts/contract-review-agent/scenario",
            json={"problem": "Review risky payment terms."},
        ).status_code
        == 200
    )
    for action in [
        "run-v0",
        "evaluate-v0",
        "fix-plan",
        "v1-graph",
        "run-v1",
        "evaluate-v1",
        "compare",
    ]:
        assert client.post(f"/api/drafts/contract-review-agent/{action}").status_code == 200

    streamed = client.post("/api/drafts/contract-review-agent/actions/publish/stream")
    assert streamed.status_code == 200

    events = [json.loads(line) for line in streamed.text.splitlines()]

    assert [event["phase"] for event in events] == [
        "starting",
        "running",
        "artifact",
        "completed",
    ]
    assert events[2]["artifact_id"] == "publish_result"
    assert events[-1]["draft"]["artifacts"]["publish_result"]["publish_result"]["status"] == (
        "published_local"
    )
