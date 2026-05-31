from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from edd_agent_lab.api.builder import create_app


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
