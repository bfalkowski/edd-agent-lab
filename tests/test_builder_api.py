from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from edd_agent_lab.api.builder import (
    _live_create_progress_messages,
    _live_progress_messages,
    create_app,
)


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
    assert response.json()["platform"]["configured"] is False
    assert response.json()["platform"]["auth_configured"] is False


def test_live_progress_messages_describe_blocking_model_steps(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    assert _live_create_progress_messages("live") == [
        "Preparing initial agent intent for the model.",
        "Will validate and normalize the target before writing YAML.",
        "Waiting for the live target draft.",
    ]
    messages = _live_progress_messages("design", "live")

    assert messages == [
        "Preparing target context for the model.",
        "Will validate and normalize model JSON before writing YAML.",
        "Waiting for live design artifacts.",
    ]
    assert _live_progress_messages("compare", "live") == []
    assert _live_progress_messages("design", "mock") == []


def test_stream_create_draft_returns_progress_events(tmp_path, monkeypatch) -> None:
    from types import SimpleNamespace

    from edd_agent_lab.ui import workspace_store

    class FakeModel:
        def invoke(self, messages):
            assert "Expand this initial agent idea" in messages[1]["content"]
            return SimpleNamespace(
                content=json.dumps(
                    {
                        "name": "Contract Risk Review Agent",
                        "purpose": "Review contract clauses and surface risks.",
                        "intended_users": ["legal operations"],
                        "primary_goals": ["identify risky clauses"],
                        "non_goals": ["provide legal advice"],
                        "allowed_tool_categories": ["local_files"],
                        "risk_tolerance": "low",
                        "expected_output_format": "risk summary",
                        "example_scenarios": ["Review a vendor clause."],
                    }
                )
            )

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)
    monkeypatch.setattr(workspace_store, "get_chat_model", lambda temperature: FakeModel())
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = TestClient(create_app())

    streamed = client.post(
        "/api/drafts/create/stream",
        json={
            "name": "Contract Review Agent",
            "description": "Review contract clauses.",
            "generation_mode": "live",
        },
    )
    assert streamed.status_code == 200

    events = [json.loads(line) for line in streamed.text.splitlines()]

    assert [event["phase"] for event in events] == [
        "starting",
        "running",
        "running",
        "running",
        "running",
        "artifact",
        "completed",
    ]
    assert events[1]["message"] == "Creating draft target. Generation mode: live."
    assert events[4]["message"] == "Waiting for the live target draft."
    assert events[-1]["draft"]["target"]["agent_target"]["name"] == (
        "Contract Risk Review Agent"
    )


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
    assert events[1]["message"] == "Generating design artifacts. Generation mode: mock."
    assert events[2]["artifact_id"] == "behavior_rules"
    assert events[2]["file"] == "behavior-rules.yaml"
    assert events[-1]["retryable"] is False
    assert events[-1]["draft"]["status"]["completed"] == 2
    assert "behavior_rules" in events[-1]["draft"]["artifact_sources"]
    assert events[-1]["draft"]["artifact_validations"]["behavior_rules"]["valid"] is True


def test_stream_action_includes_live_progress_events(tmp_path, monkeypatch) -> None:
    from edd_agent_lab.api import builder
    from edd_agent_lab.ui import workspace_store

    def fake_live_step(agent_key: str) -> None:
        path = workspace_store.draft_workspace_dir(agent_key) / "behavior-rules.yaml"
        path.write_text(
            "behavior_rules:\n"
            "  - id: stay_in_scope\n"
            "    description: Stay inside the target scope.\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)
    monkeypatch.setitem(builder.ACTION_HANDLERS, "design", fake_live_step)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = TestClient(create_app())

    created = client.post(
        "/api/drafts",
        json={
            "name": "Contract Review Agent",
            "description": "Review contract clauses and surface negotiation risks.",
        },
    )
    assert created.status_code == 200

    streamed = client.post(
        "/api/drafts/contract-review-agent/actions/design/stream?generation_mode=live"
    )
    assert streamed.status_code == 200

    messages = [json.loads(line)["message"] for line in streamed.text.splitlines()]

    assert messages[:5] == [
        "Starting design.",
        "Generating design artifacts. Generation mode: live.",
        "Preparing target context for the model.",
        "Will validate and normalize model JSON before writing YAML.",
        "Waiting for live design artifacts.",
    ]


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


def test_draft_create_list_load_and_delete_api(tmp_path, monkeypatch) -> None:
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
    assert created.json()["agent_key"] == "contract-review-agent"

    listed = client.get("/api/drafts")
    assert listed.status_code == 200
    assert listed.json()["drafts"][0]["agent_key"] == "contract-review-agent"

    loaded = client.get("/api/drafts/contract-review-agent")
    assert loaded.status_code == 200
    assert loaded.json()["target"]["agent_target"]["purpose"] == "Review contract clauses."

    deleted = client.delete("/api/drafts/contract-review-agent")
    assert deleted.status_code == 200
    assert deleted.json()["drafts"] == []
    assert not workspace_store.draft_workspace_dir("contract-review-agent").parent.exists()


def test_draft_create_can_use_live_target_generation(tmp_path, monkeypatch) -> None:
    from types import SimpleNamespace

    from edd_agent_lab.ui import workspace_store

    class FakeModel:
        def invoke(self, messages):
            assert "Expand this initial agent idea" in messages[1]["content"]
            return SimpleNamespace(
                content=json.dumps(
                    {
                        "name": "Contract Risk Review Agent",
                        "purpose": "Review contract clauses and surface risks.",
                        "intended_users": ["legal operations"],
                        "primary_goals": ["identify risky clauses"],
                        "non_goals": ["provide legal advice"],
                        "allowed_tool_categories": ["local_files"],
                        "risk_tolerance": "low",
                        "expected_output_format": "risk summary",
                        "example_scenarios": ["Review a vendor clause."],
                    }
                )
            )

    monkeypatch.setattr(workspace_store, "LAB_RUNS_DIR", tmp_path)
    monkeypatch.setattr(workspace_store, "get_chat_model", lambda temperature: FakeModel())
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = TestClient(create_app())

    created = client.post(
        "/api/drafts",
        json={
            "name": "Contract Review Agent",
            "description": "Review contract clauses.",
            "generation_mode": "live",
        },
    )

    assert created.status_code == 200
    target = created.json()["target"]["agent_target"]
    assert created.json()["agent_key"] == "contract-review-agent"
    assert target["name"] == "Contract Risk Review Agent"
    assert target["risk_tolerance"] == "low"


def test_draft_export_and_import_api(tmp_path, monkeypatch) -> None:
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

    exported = client.get("/api/drafts/contract-review-agent/export")
    archive_path = tmp_path / "_exports" / "contract-review-agent.zip"
    assert exported.status_code == 200
    assert exported.headers["content-type"] == "application/zip"
    assert archive_path.is_file()

    assert client.delete("/api/drafts/contract-review-agent").status_code == 200
    imported = client.post("/api/drafts/import", json={"archive_path": str(archive_path)})

    assert imported.status_code == 200
    assert imported.json()["agent_key"] == "contract-review-agent"
    assert imported.json()["artifact_validations"]["target"]["valid"] is True
    assert "behavior_rules" in imported.json()["artifacts"]


def test_load_draft_reports_corrupt_artifact_yaml(tmp_path, monkeypatch) -> None:
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
    workspace_store.draft_workspace_dir("contract-review-agent").joinpath(
        "behavior-rules.yaml"
    ).write_text("behavior_rules: [unterminated", encoding="utf-8")

    loaded = client.get("/api/drafts/contract-review-agent")

    assert loaded.status_code == 400
    assert "Invalid YAML in behavior-rules.yaml" in loaded.json()["detail"]


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


def test_save_scenario_returns_generated_variants(tmp_path, monkeypatch) -> None:
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

    updated = client.post(
        "/api/drafts/contract-review-agent/scenario",
        json={"problem": "Review risky payment terms."},
    )

    assert updated.status_code == 200
    artifacts = updated.json()["artifacts"]
    assert artifacts["scenario"]["scenario"]["problem"] == "Review risky payment terms."
    assert artifacts["scenario_variants"]["scenario_variants"][0]["mutation_type"] == (
        "missing_context"
    )
    cards = {card["id"]: card for card in updated.json()["artifact_cards"]}
    assert cards["scenario_variants"]["status"] == "ready"


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


def test_update_and_delete_raw_artifact_api(tmp_path, monkeypatch) -> None:
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

    source = "\n".join(
        [
            "behavior_rules:",
            "- id: state_purpose_and_scope",
            "  severity: medium",
            "  description: Stay inside a revised review scope.",
            "  target_id: contract-review-agent-target-v1",
            "  status: review",
            "",
        ]
    )
    updated = client.put(
        "/api/drafts/contract-review-agent/artifacts/behavior_rules",
        json={"source": source},
    )
    assert updated.status_code == 200
    assert updated.json()["artifacts"]["behavior_rules"]["behavior_rules"][0]["status"] == (
        "review"
    )

    deleted = client.delete("/api/drafts/contract-review-agent/artifacts/behavior_rules")
    assert deleted.status_code == 200
    assert "behavior_rules" not in deleted.json()["artifacts"]
    assert (
        deleted.json()["artifact_cards"][1]["id"],
        deleted.json()["artifact_cards"][1]["status"],
    ) == ("behavior_rules", "pending")


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
    assert events[-1]["draft"]["artifacts"]["publish_result"]["publish_result"]["delivery"][
        "mode"
    ] == "local"
