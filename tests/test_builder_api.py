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


def test_rename_draft_returns_refreshed_draft(tmp_path, monkeypatch) -> None:
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

    renamed = client.put(
        "/api/drafts/contract-review-agent/rename",
        json={"name": "Clause Review Agent"},
    )

    assert renamed.status_code == 200
    assert renamed.json()["agent_key"] == "contract-review-agent"
    assert renamed.json()["target"]["agent_target"]["name"] == "Clause Review Agent"


def test_archive_draft_hides_project(tmp_path, monkeypatch) -> None:
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

    archived = client.post("/api/drafts/contract-review-agent/archive")

    assert archived.status_code == 200
    assert archived.json()["drafts"] == []
    assert workspace_store.draft_workspace_dir("contract-review-agent").is_dir()


def test_update_rules_returns_refreshed_draft(tmp_path, monkeypatch) -> None:
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
    assert client.post("/api/drafts/contract-review-agent/design").status_code == 200

    updated = client.put(
        "/api/drafts/contract-review-agent/rules",
        json={
            "rules": [
                {
                    "id": "state_purpose_and_scope",
                    "severity": "high",
                    "description": "Stay inside contract review scope.",
                    "status": "draft",
                }
            ]
        },
    )

    assert updated.status_code == 200
    rules = updated.json()["artifacts"]["behavior_rules"]["behavior_rules"]
    assert rules[0]["description"] == "Stay inside contract review scope."
    assert "Stay inside contract review scope." in updated.json()["artifact_sources"][
        "behavior_rules"
    ]


def test_update_eval_contract_returns_refreshed_draft(tmp_path, monkeypatch) -> None:
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
    assert client.post("/api/drafts/contract-review-agent/design").status_code == 200

    updated = client.put(
        "/api/drafts/contract-review-agent/eval-contract",
        json={
            "status": "review",
            "metrics": [
                {
                    "id": "scope_alignment",
                    "scale": "0-10",
                    "rules": ["state_purpose_and_scope"],
                }
            ],
            "gates": [
                {
                    "id": "must_stay_in_scope",
                    "type": "hard",
                    "condition": "scope_alignment >= 8",
                }
            ],
        },
    )

    assert updated.status_code == 200
    contract = updated.json()["artifacts"]["eval_contract"]["eval_contract"]
    assert contract["status"] == "review"
    assert contract["metrics"][0]["scale"] == "0-10"
    assert "scope_alignment >= 8" in updated.json()["artifact_sources"]["eval_contract"]


def test_update_information_requirements_returns_refreshed_draft(
    tmp_path, monkeypatch
) -> None:
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
    assert client.post("/api/drafts/contract-review-agent/design").status_code == 200

    updated = client.put(
        "/api/drafts/contract-review-agent/information-requirements",
        json={
            "requirements": [
                {
                    "id": "contract_source",
                    "description": "Original contract language.",
                    "required_for_rules": ["ask_for_missing_information"],
                    "status": "review",
                }
            ]
        },
    )

    assert updated.status_code == 200
    requirements = updated.json()["artifacts"]["information_requirements"][
        "information_requirements"
    ]
    assert requirements[0]["id"] == "contract_source"
    assert "Original contract language." in updated.json()["artifact_sources"][
        "information_requirements"
    ]


def test_update_tool_requirements_returns_refreshed_draft(tmp_path, monkeypatch) -> None:
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
    assert client.post("/api/drafts/contract-review-agent/design").status_code == 200

    updated = client.put(
        "/api/drafts/contract-review-agent/tool-requirements",
        json={
            "tools": [
                {
                    "id": "collect_contract_context",
                    "suggested_tool_name": "request_contract_context",
                    "information_requirements": ["contract_source"],
                    "implementation_status": "planned",
                    "production_blocker": True,
                    "status": "review",
                }
            ]
        },
    )

    assert updated.status_code == 200
    tools = updated.json()["artifacts"]["tool_requirements"]["tool_requirements"]
    assert tools[0]["suggested_tool_name"] == "request_contract_context"
    assert "implementation_status: planned" in updated.json()["artifact_sources"][
        "tool_requirements"
    ]


def test_update_graph_design_returns_refreshed_draft(tmp_path, monkeypatch) -> None:
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
    assert client.post("/api/drafts/contract-review-agent/design").status_code == 200

    updated = client.put(
        "/api/drafts/contract-review-agent/graph-design",
        json={
            "artifact_key": "graph_design",
            "version": "v0-edited",
            "status": "review",
            "nodes": [
                {
                    "id": "understand_request",
                    "purpose": "Collect source context before drafting.",
                    "supports_rules": ["ask_for_missing_information"],
                },
                {
                    "id": "draft_response",
                    "purpose": "Draft a scoped response.",
                    "supports_rules": ["state_purpose_and_scope"],
                },
            ],
            "edges": [{"from": "understand_request", "to": "draft_response"}],
        },
    )

    assert updated.status_code == 200
    graph = updated.json()["artifacts"]["graph_design"]["graph_design"]
    assert graph["version"] == "v0-edited"
    assert graph["status"] == "review"
    assert "Collect source context before drafting." in updated.json()["artifact_sources"][
        "graph_design"
    ]


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
